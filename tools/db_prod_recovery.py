#!/usr/bin/env python3
"""Fail-closed recovery for a current-user production gateway.

The gateway publishes a small recovery journal before it starts a transport.
The journal contains process identities and approval-binding metadata only; it
never contains SQL text, an address, an account, or a secret.  Recovery is a
separate, explicitly reviewed operation.  The caller supplies the reviewed
SQL plan and the already-authenticated session observer, while this module
only fences process identities and reconciles the durable coordinator state.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sqlite3
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Optional

from db_query_control import Store, Supervisor
from db_prod_watchdog import process_fingerprint


RUN_ID_RE = re.compile(r"^[0-9a-f]{16,128}$")
HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
HOST_TAG_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
RECOVERABLE_PHASES = frozenset(("starting", "dispatching", "running", "finishing", "unconfirmed"))
# Kept as a compatibility alias for callers that imported the original name.
ALLOWED_PHASES = RECOVERABLE_PHASES
MIN_WATCHDOG_GRACE = 5.0
MAX_METADATA_BYTES = 16 * 1024
RECOVERY_SCHEMA = 1
RECOVERY_APPROVAL_SCHEMA = 1
RECOVERY_APPROVAL_TTL = 1800.0
RECOVERY_APPROVAL_TABLE = "recovery_approvals"
# The observer is a single bounded control batch.  These values are shown in
# the recovery review and are part of its digest so an operator approves the
# same limits that the transport enforces.
RECOVERY_OBSERVER_TIMEOUT = 5.0
RECOVERY_OBSERVER_MAX_ROWS = 1
RECOVERY_OBSERVER_MAX_BYTES = 256


class RecoveryDenied(RuntimeError):
    """A recovery precondition was not proven."""


def _safe_text(value: Any, name: str, *, max_bytes: int = 512) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise RecoveryDenied(f"{name}_invalid")
    if len(value.encode("utf-8")) > max_bytes or any(ord(char) < 32 for char in value):
        raise RecoveryDenied(f"{name}_invalid")
    return value


def validate_run_id(run_id: Any) -> str:
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise RecoveryDenied("run_id_invalid")
    return run_id


def _validate_pid(value: Any, name: str) -> int:
    if type(value) is not int or value <= 1:
        raise RecoveryDenied(f"{name}_invalid")
    return value


def _validate_birth(value: Any, name: str) -> str:
    return _safe_text(value, name, max_bytes=256)


def _validate_digest(value: Any, name: str = "profile_digest") -> str:
    if not isinstance(value, str) or not HEX_DIGEST_RE.fullmatch(value):
        raise RecoveryDenied(f"{name}_invalid")
    return value


def _secure_directory(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or "\x00" in str(path):
        raise RecoveryDenied("state_dir_invalid")
    try:
        info = path.lstat()
    except OSError:
        raise RecoveryDenied("state_dir_unavailable") from None
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink() or info.st_uid != os.geteuid():
        raise RecoveryDenied("state_dir_untrusted")
    if info.st_mode & 0o077:
        raise RecoveryDenied("state_dir_permissions")
    return path


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_METADATA_BYTES:
        raise RecoveryDenied("journal_too_large")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            descriptor = -1
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _load_json(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise RecoveryDenied("journal_untrusted")
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise RecoveryDenied("journal_permissions")
        if info.st_size > MAX_METADATA_BYTES:
            raise RecoveryDenied("journal_too_large")
        value = json.loads(path.read_text(encoding="utf-8"))
    except RecoveryDenied:
        raise
    except (OSError, UnicodeError, ValueError):
        raise RecoveryDenied("journal_invalid") from None
    if not isinstance(value, dict):
        raise RecoveryDenied("journal_invalid")
    return value


def _validate_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise RecoveryDenied("journal_metadata_invalid")
    allowed = {
        "target",
        "database",
        "host_tag",
        "profile_digest",
        "gateway_pid",
        "gateway_birth",
    }
    if set(metadata) != allowed:
        raise RecoveryDenied("journal_metadata_fields")
    target = _safe_text(metadata["target"], "target")
    database = _safe_text(metadata["database"], "database")
    host_tag = metadata["host_tag"]
    if not isinstance(host_tag, str) or not HOST_TAG_RE.fullmatch(host_tag):
        raise RecoveryDenied("host_tag_invalid")
    profile_digest = _validate_digest(metadata["profile_digest"])
    gateway_pid = _validate_pid(metadata["gateway_pid"], "gateway_pid")
    gateway_birth = _validate_birth(metadata["gateway_birth"], "gateway_birth")
    normalized = {
        "target": target,
        "database": database,
        "host_tag": host_tag,
        "profile_digest": profile_digest,
        "gateway_pid": gateway_pid,
        "gateway_birth": gateway_birth,
    }
    encoded = json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_METADATA_BYTES:
        raise RecoveryDenied("journal_too_large")
    return normalized


@dataclass(frozen=True)
class JournalRecord:
    run_id: str
    metadata: dict[str, Any]
    worker_pid: Optional[int]
    worker_birth: Optional[str]
    schema: int = RECOVERY_SCHEMA

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "metadata": self.metadata,
            "worker": (
                None
                if self.worker_pid is None
                else {"pid": self.worker_pid, "birth": self.worker_birth}
            ),
        }


class RecoveryJournal:
    """Durable process identity journal for one current-user state directory."""

    def __init__(self, state_dir: Path):
        self.state_dir = _secure_directory(Path(state_dir))

    def path_for(self, run_id: str) -> Path:
        run_id = validate_run_id(run_id)
        return self.state_dir / f"{run_id}.json"

    def _record_from_dict(self, value: Mapping[str, Any], run_id: str) -> JournalRecord:
        if set(value) != {"schema", "run_id", "metadata", "worker"}:
            raise RecoveryDenied("journal_fields")
        if value.get("schema") != RECOVERY_SCHEMA or value.get("run_id") != run_id:
            raise RecoveryDenied("journal_identity_mismatch")
        metadata = _validate_metadata(value.get("metadata"))
        worker = value.get("worker")
        if worker is None:
            worker_pid = worker_birth = None
        else:
            if not isinstance(worker, Mapping):
                raise RecoveryDenied("worker_identity_invalid")
            if set(worker) != {"pid", "birth"}:
                raise RecoveryDenied("worker_identity_fields")
            worker_pid = _validate_pid(worker.get("pid"), "worker_pid")
            worker_birth = _validate_birth(worker.get("birth"), "worker_birth")
        return JournalRecord(run_id, metadata, worker_pid, worker_birth)

    def write_before_start(self, run_id: str, metadata: Mapping[str, Any]) -> JournalRecord:
        run_id = validate_run_id(run_id)
        normalized = _validate_metadata(metadata)
        path = self.path_for(run_id)
        if path.exists() or path.is_symlink():
            raise RecoveryDenied("journal_already_exists")
        record = JournalRecord(run_id, normalized, None, None)
        payload = (json.dumps(record.as_dict(), sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        _atomic_write(path, payload)
        return record

    def read(self, run_id: str) -> JournalRecord:
        run_id = validate_run_id(run_id)
        path = self.path_for(run_id)
        return self._record_from_dict(_load_json(path), run_id)

    def update_worker(self, run_id: str, pid: int, birth: str) -> JournalRecord:
        current = self.read(run_id)
        pid = _validate_pid(pid, "worker_pid")
        birth = _validate_birth(birth, "worker_birth")
        record = JournalRecord(current.run_id, current.metadata, pid, birth)
        payload = (json.dumps(record.as_dict(), sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        _atomic_write(self.path_for(run_id), payload)
        return record


def _observer_zero(observer: Callable[[Mapping[str, Any]], Any], plan: Mapping[str, Any]) -> bool:
    try:
        value = observer(plan)
    except Exception:
        raise RecoveryDenied("session_observer_failed") from None
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, Mapping):
        permission = value.get("permission_ok", value.get("permission"))
        if permission is not None and permission is not True:
            return False
        for key in ("sessions", "active_sessions", "count"):
            if key in value:
                value = value[key]
                if isinstance(value, (list, tuple, set)):
                    value = len(value)
                break
    if type(value) is int:
        return value == 0
    return False


def _pid_presence(pid: int) -> bool:
    """Distinguish a missing PID from an unobservable live PID.

    ``process_fingerprint`` intentionally returns ``None`` for both an absent
    process and platform/permission failures.  Recovery must only interpret
    that value as death after an independent ``kill(pid, 0)`` check proves
    that the PID no longer exists.
    """

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        raise RecoveryDenied("process_presence_denied") from None
    except OSError:
        raise RecoveryDenied("process_presence_failed") from None
    return True


def _probe(
    process_probe: Callable[[int], Optional[str]],
    pid: int,
    presence_probe: Callable[[int], bool],
) -> Optional[str]:
    try:
        value = process_probe(pid)
    except Exception:
        raise RecoveryDenied("process_probe_failed") from None
    if value is not None and (not isinstance(value, str) or not value):
        raise RecoveryDenied("process_identity_invalid")
    if value is None:
        try:
            present = presence_probe(pid)
        except RecoveryDenied:
            raise
        except Exception:
            raise RecoveryDenied("process_presence_failed") from None
        if present is not False:
            raise RecoveryDenied("process_identity_unavailable")
    return value


def current_user_sqlcmd_absent() -> bool:
    """Prove absence of the fixed macOS sqlcmd transport, without reading argv.

Only used after the original gateway is dead and its watchdog grace elapsed.
Any sqlcmd for this UID blocks recovery, even one unrelated to the run. This
is a cooperative same-UID boundary, not protection against renamed binaries.
"""
    if sys.platform != "darwin":
        raise RecoveryDenied("worker_inventory_unsupported")
    try:
        result = subprocess.run(
            ["/bin/ps", "-ww", "-axo", "pid=,uid=,comm="],
            capture_output=True, text=True, timeout=3, check=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        if result.stderr or len(result.stdout.encode("utf-8")) > 1024 * 1024:
            raise ValueError("inventory warning")
        seen_self = False
        seen_pids = set()
        sqlcmd_seen = False
        for line in result.stdout.splitlines():
            fields = line.strip().split(None, 2)
            if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
                raise ValueError("invalid inventory")
            pid, uid = int(fields[0]), int(fields[1])
            if pid <= 0 or pid in seen_pids or any(ord(c) < 32 for c in fields[2]):
                raise ValueError("invalid inventory identity")
            seen_pids.add(pid)
            if pid == os.getpid() and uid == os.getuid():
                seen_self = True
            if uid == os.getuid() and Path(fields[2]).name == "sqlcmd":
                sqlcmd_seen = True
        if not seen_self:
            raise ValueError("incomplete inventory")
        return not sqlcmd_seen
    except Exception:
        raise RecoveryDenied("worker_inventory_unavailable") from None


def _prove_fenced(
    record: JournalRecord,
    process_probe: Callable[[int], Optional[str]],
    *,
    presence_probe: Callable[[int], bool],
    watchdog_grace: float,
    sleep: Callable[[float], None],
    allow_unknown_worker: bool,
    unknown_worker_absence_probe: Optional[Callable[[], bool]],
) -> None:
    if (
        isinstance(watchdog_grace, bool)
        or not isinstance(watchdog_grace, (int, float))
        or not math.isfinite(float(watchdog_grace))
        or watchdog_grace < MIN_WATCHDOG_GRACE
    ):
        raise RecoveryDenied("watchdog_grace_too_short")

    metadata = record.metadata
    gateway_pid = metadata["gateway_pid"]
    gateway_birth = metadata["gateway_birth"]
    if record.worker_pid is not None and record.worker_birth is not None:
        observed = _probe(process_probe, record.worker_pid, presence_probe)
        if observed == record.worker_birth:
            raise RecoveryDenied("worker_alive")
        return

    if not allow_unknown_worker:
        raise RecoveryDenied("worker_identity_missing")

    # Without a worker identity, the gateway identity is the last fence.  A
    # grace period is mandatory even when the first probe already says dead:
    # the independent watchdog may still be completing its kill sequence.
    observed = _probe(process_probe, gateway_pid, presence_probe)
    if observed == gateway_birth:
        raise RecoveryDenied("gateway_alive")
    try:
        sleep(float(watchdog_grace))
    except Exception:
        raise RecoveryDenied("watchdog_grace_failed") from None
    observed = _probe(process_probe, gateway_pid, presence_probe)
    if observed == gateway_birth:
        raise RecoveryDenied("gateway_alive_after_grace")
    if unknown_worker_absence_probe is None:
        raise RecoveryDenied("worker_absence_proof_required")
    if unknown_worker_absence_probe() is not True:
        raise RecoveryDenied("worker_processes_remaining")


def _validate_request_id(value: Any, name: str = "request_id") -> str:
    try:
        return validate_run_id(value)
    except RecoveryDenied:
        raise RecoveryDenied(f"{name}_invalid") from None


def observer_recovery_digest(
    *,
    run_id: str,
    epoch: Any,
    target: str,
    database: str,
    host_tag: str,
    profile_digest: str,
    observer_sql: str,
    timeout: float = RECOVERY_OBSERVER_TIMEOUT,
    max_rows: int = RECOVERY_OBSERVER_MAX_ROWS,
    max_bytes: int = RECOVERY_OBSERVER_MAX_BYTES,
) -> str:
    """Hash the exact observer-only recovery batch and its state binding."""

    run_id = validate_run_id(run_id)
    if type(epoch) is not int or epoch < 0:
        raise RecoveryDenied("recovery_epoch_invalid")
    target = _safe_text(target, "target")
    database = _safe_text(database, "database")
    if not isinstance(host_tag, str) or not HOST_TAG_RE.fullmatch(host_tag):
        raise RecoveryDenied("host_tag_invalid")
    profile_digest = _validate_digest(profile_digest)
    # SQL is a multiline batch, unlike the single-line metadata fields. Keep
    # the exact bytes in the approval digest, including ordinary whitespace.
    if (not isinstance(observer_sql, str) or not observer_sql.strip()
            or len(observer_sql.encode("utf-8")) > MAX_METADATA_BYTES
            or any(ord(c) < 32 and c not in "\n\r\t" for c in observer_sql)):
        raise RecoveryDenied("observer_sql_invalid")
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(float(timeout)) or float(timeout) != RECOVERY_OBSERVER_TIMEOUT):
        raise RecoveryDenied("recovery_timeout_invalid")
    if type(max_rows) is not int or max_rows != RECOVERY_OBSERVER_MAX_ROWS:
        raise RecoveryDenied("recovery_max_rows_invalid")
    if type(max_bytes) is not int or max_bytes != RECOVERY_OBSERVER_MAX_BYTES:
        raise RecoveryDenied("recovery_max_bytes_invalid")
    payload = {
        "kind": "team2-observer-recovery-v1",
        "run_id": run_id,
        "epoch": epoch,
        "target": target,
        "database": database,
        "host_tag": host_tag,
        "profile_digest": profile_digest,
        "observer_sql": observer_sql,
        "timeout": float(timeout),
        "max_rows": max_rows,
        "max_bytes": max_bytes,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def ensure_recovery_approval_table(store: Store) -> None:
    """Provision the durable observer-only approval ledger if absent."""

    with store.transaction() as connection:
        connection.execute(
            f"""CREATE TABLE IF NOT EXISTS {RECOVERY_APPROVAL_TABLE} (
                id TEXT PRIMARY KEY,
                schema INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                target TEXT NOT NULL,
                database_name TEXT NOT NULL,
                host_tag TEXT NOT NULL,
                profile_digest TEXT NOT NULL,
                digest TEXT NOT NULL,
                expires REAL NOT NULL,
                status TEXT NOT NULL,
                operator TEXT
            )"""
        )


def create_recovery_approval(
    store: Store,
    *,
    request_id: str,
    run_id: str,
    epoch: int,
    target: str,
    database: str,
    host_tag: str,
    profile_digest: str,
    digest: str,
    expires: Optional[float] = None,
) -> None:
    """Create one pending observer approval bound to the current halted run."""

    request_id = _validate_request_id(request_id)
    run_id = validate_run_id(run_id)
    if type(epoch) is not int or epoch < 0:
        raise RecoveryDenied("recovery_epoch_invalid")
    target = _safe_text(target, "target")
    database = _safe_text(database, "database")
    if not isinstance(host_tag, str) or not HOST_TAG_RE.fullmatch(host_tag):
        raise RecoveryDenied("host_tag_invalid")
    profile_digest = _validate_digest(profile_digest)
    digest = _validate_digest(digest, "recovery_digest")
    expiry = time.time() + RECOVERY_APPROVAL_TTL if expires is None else float(expires)
    if not math.isfinite(expiry) or expiry <= time.time():
        raise RecoveryDenied("recovery_expiry_invalid")
    ensure_recovery_approval_table(store)
    try:
        with store.transaction() as connection:
            state = Store._state(connection)
            if (
                not state["halted"]
                or state["active"] != run_id
                or state["epoch"] != epoch
                or state["phase"] not in RECOVERABLE_PHASES
            ):
                raise RecoveryDenied("recovery_state_changed")
            existing = connection.execute(
                f"""SELECT id FROM {RECOVERY_APPROVAL_TABLE}
                    WHERE run_id=? AND epoch=? AND status IN ('pending','approved')
                    LIMIT 1""",
                (run_id, epoch),
            ).fetchone()
            if existing is not None:
                # A gateway restart or a stale in-memory review must never
                # make an old approval the only recovery path.  Supersede it
                # inside the same transaction and issue a fresh request.
                connection.execute(
                    f"UPDATE {RECOVERY_APPROVAL_TABLE} SET status='superseded' WHERE id=?",
                    (existing["id"],),
                )
            connection.execute(
                f"""INSERT INTO {RECOVERY_APPROVAL_TABLE}
                    (id,schema,run_id,epoch,target,database_name,host_tag,profile_digest,
                     digest,expires,status,operator)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                (
                    request_id,
                    RECOVERY_APPROVAL_SCHEMA,
                    run_id,
                    epoch,
                    target,
                    database,
                    host_tag,
                    profile_digest,
                    digest,
                    expiry,
                    "pending",
                ),
            )
    except sqlite3.IntegrityError:
        raise RecoveryDenied("recovery_request_exists") from None


def approve_recovery_approval(store: Store, request_id: str, digest: str, *, operator: str) -> None:
    """Approve exactly the observer SQL shown in the recovery review."""

    request_id = _validate_request_id(request_id)
    digest = _validate_digest(digest, "recovery_digest")
    operator = _safe_text(operator, "operator", max_bytes=128)
    ensure_recovery_approval_table(store)
    with store.transaction() as connection:
        state = Store._state(connection)
        changed = connection.execute(
            f"""UPDATE {RECOVERY_APPROVAL_TABLE}
                SET status='approved', operator=?
                WHERE id=? AND schema=? AND digest=? AND status='pending'
                  AND expires>? AND epoch=? AND run_id=?""",
            (
                operator,
                request_id,
                RECOVERY_APPROVAL_SCHEMA,
                digest,
                time.time(),
                state["epoch"],
                state["active"],
            ),
        ).rowcount
        if not state["halted"] or not state["active"] or state["phase"] not in RECOVERABLE_PHASES or changed != 1:
            raise RecoveryDenied("recovery_approval_invalid")


def _consume_recovery_approval_and_mark(
    store: Store,
    snapshot: Mapping[str, Any],
    *,
    request_id: str,
    digest: str,
    run_id: str,
) -> None:
    """Consume approval and fence the same state snapshot in one transaction."""

    request_id = _validate_request_id(request_id)
    digest = _validate_digest(digest, "recovery_digest")
    with store.transaction() as connection:
        current = Store._state(connection)
        for field in ("active", "owner", "target", "identity", "epoch", "halted"):
            if current.get(field) != snapshot.get(field):
                raise RecoveryDenied("store_changed")
        if current["active"] != run_id or not current["halted"] or current["phase"] not in RECOVERABLE_PHASES:
            raise RecoveryDenied("phase_not_recoverable")
        row = connection.execute(
            f"""SELECT run_id,epoch,digest,status,expires FROM {RECOVERY_APPROVAL_TABLE}
                WHERE id=? AND schema=?""",
            (request_id, RECOVERY_APPROVAL_SCHEMA),
        ).fetchone()
        if row is None or (
            row["run_id"] != run_id
            or row["epoch"] != current["epoch"]
            or row["digest"] != digest
            or row["status"] != "approved"
            or row["expires"] <= time.time()
        ):
            raise RecoveryDenied("recovery_approval_invalid")
        changed = connection.execute(
            f"""UPDATE {RECOVERY_APPROVAL_TABLE} SET status='consumed'
                WHERE id=? AND schema=? AND status='approved' AND digest=? AND epoch=?""",
            (request_id, RECOVERY_APPROVAL_SCHEMA, digest, current["epoch"]),
        ).rowcount
        if changed != 1:
            raise RecoveryDenied("recovery_approval_replay")
        connection.execute(
            "UPDATE control SET halted=1,reason=?,phase='unconfirmed' WHERE id=1",
            ("recovery_fenced",),
        )


def _verify_recovery_plan(
    plan: Mapping[str, Any], state: Mapping[str, Any], record: JournalRecord
) -> tuple[str, str]:
    """Validate a reviewed observer-only plan and return request ID/digest."""

    if not isinstance(plan, Mapping) or plan.get("approved") is not True:
        raise RecoveryDenied("explicit_review_required")
    if not state.get("halted"):
        raise RecoveryDenied("recovery_requires_halted")
    if state.get("phase") not in RECOVERABLE_PHASES or state.get("active") != record.run_id:
        raise RecoveryDenied("phase_not_recoverable")
    run_id = validate_run_id(plan.get("run_id"))
    if run_id != record.run_id:
        raise RecoveryDenied("run_identity_mismatch")
    if type(plan.get("epoch")) is not int or plan.get("epoch") != state.get("epoch"):
        raise RecoveryDenied("recovery_epoch_changed")
    request_id = _validate_request_id(plan.get("recovery_request_id", plan.get("request_id")), "recovery_request_id")
    if plan.get("target") != record.metadata["target"]:
        raise RecoveryDenied("target_changed")
    if plan.get("database") != record.metadata["database"]:
        raise RecoveryDenied("database_changed")
    if plan.get("host_tag") != record.metadata["host_tag"]:
        raise RecoveryDenied("host_tag_changed")
    if plan.get("profile_digest") != record.metadata["profile_digest"]:
        raise RecoveryDenied("profile_changed")
    if plan.get("owner") is not None and plan.get("owner") != state.get("owner"):
        raise RecoveryDenied("owner_changed")
    if "sql" in plan:
        raise RecoveryDenied("observer_only_required")
    observer_sql = plan.get("observer_sql")
    digest = _validate_digest(plan.get("digest"), "recovery_digest")
    if (plan.get("timeout") != RECOVERY_OBSERVER_TIMEOUT
            or plan.get("max_rows") != RECOVERY_OBSERVER_MAX_ROWS
            or plan.get("max_bytes") != RECOVERY_OBSERVER_MAX_BYTES):
        raise RecoveryDenied("recovery_limits_changed")
    try:
        expected = observer_recovery_digest(
            run_id=run_id,
            epoch=state["epoch"],
            target=record.metadata["target"],
            database=record.metadata["database"],
            host_tag=record.metadata["host_tag"],
            profile_digest=record.metadata["profile_digest"],
            observer_sql=observer_sql,
            timeout=plan["timeout"],
            max_rows=plan["max_rows"],
            max_bytes=plan["max_bytes"],
        )
    except RecoveryDenied:
        raise
    except Exception:
        raise RecoveryDenied("recovery_plan_invalid") from None
    if digest != expected:
        raise RecoveryDenied("recovery_digest_mismatch")
    return request_id, digest


def _verify_recovery_approval(
    store: Store, *, request_id: str, run_id: str, epoch: int, digest: str
) -> None:
    ensure_recovery_approval_table(store)
    with store.transaction() as connection:
        row = connection.execute(
            f"""SELECT run_id,epoch,digest,status,expires FROM {RECOVERY_APPROVAL_TABLE}
                WHERE id=? AND schema=?""",
            (request_id, RECOVERY_APPROVAL_SCHEMA),
        ).fetchone()
    if row is None or (
        row["run_id"] != run_id
        or row["epoch"] != epoch
        or row["digest"] != digest
        or row["status"] != "approved"
        or row["expires"] <= time.time()
    ):
        raise RecoveryDenied("recovery_approval_invalid")


def recover(
    reviewed_plan: Mapping[str, Any],
    store: Store,
    session_observer: Callable[[Mapping[str, Any]], Any],
    process_probe: Callable[[int], Optional[str]] = process_fingerprint,
    *,
    journal: Optional[RecoveryJournal] = None,
    watchdog_grace: float = MIN_WATCHDOG_GRACE,
    sleep: Callable[[float], None] = time.sleep,
    pid_presence_probe: Callable[[int], bool] = _pid_presence,
    allow_unknown_worker: bool = False,
    unknown_worker_absence_probe: Optional[Callable[[], bool]] = None,
) -> dict[str, Any]:
    """Recover one fenced active run while keeping the coordinator halted.

    The plan is always observer-only and comes from the gateway's separate
    recovery approval flow.  The approval is consumed and the phase is made
    ``unconfirmed`` before any observer connection is opened.  A failed
    observer therefore leaves the slot halted and active, while a later
    recovery requires a fresh observer approval.
    """

    if not isinstance(reviewed_plan, Mapping):
        raise RecoveryDenied("reviewed_plan_invalid")
    run_id = validate_run_id(reviewed_plan.get("run_id"))
    if journal is None:
        state_dir = reviewed_plan.get("state_dir")
        if not isinstance(state_dir, str):
            raise RecoveryDenied("journal_required")
        journal = RecoveryJournal(Path(state_dir))
    record = journal.read(run_id)
    snapshot = store.status()
    request_id, digest = _verify_recovery_plan(reviewed_plan, snapshot, record)
    _verify_recovery_approval(
        store,
        request_id=request_id,
        run_id=run_id,
        epoch=snapshot["epoch"],
        digest=digest,
    )

    # This compare-and-write is the approval's one-use boundary.  It happens
    # before fencing probes and before either observer connection.
    _consume_recovery_approval_and_mark(
        store,
        snapshot,
        request_id=request_id,
        digest=digest,
        run_id=run_id,
    )

    _prove_fenced(
        record,
        process_probe,
        presence_probe=pid_presence_probe,
        watchdog_grace=watchdog_grace,
        sleep=sleep,
        allow_unknown_worker=allow_unknown_worker,
        unknown_worker_absence_probe=unknown_worker_absence_probe,
    )

    # Never reconcile a state whose active identity changed while the observer
    # was running.  Supervisor.reconcile performs the final compare-and-clear;
    # this callback adds the original run fence around its bounded observer.
    def fenced_zero() -> bool:
        try:
            with store.transaction() as connection:
                current = Store._state(connection)
        except Exception:
            return False
        if any(current.get(field) != snapshot.get(field)
               for field in ("active", "owner", "target", "identity", "epoch", "halted")):
            return False
        if current.get("phase") != "unconfirmed":
            return False
        if not _observer_zero(session_observer, reviewed_plan):
            return False
        if record.worker_pid is None and unknown_worker_absence_probe() is not True:
            return False
        try:
            with store.transaction() as connection:
                current = Store._state(connection)
                if any(current.get(field) != snapshot.get(field)
                       for field in ("active", "owner", "target", "identity", "epoch", "halted")):
                    return False
                return current.get("phase") == "unconfirmed"
        except Exception:
            return False

    supervisor = Supervisor(store)
    if not supervisor.reconcile(fenced_zero):
        raise RecoveryDenied("reconcile_failed")
    state = store.status()
    return {
        "ok": True,
        "status": "recovered",
        "run_id": run_id,
        "digest": digest,
        "halted": bool(state["halted"]),
        "active": state["active"],
        "phase": state["phase"],
    }

