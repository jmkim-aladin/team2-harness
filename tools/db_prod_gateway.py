#!/usr/bin/env python3
"""One current-user production SQL gateway. No implicit DB connections.

This is a cooperative agent boundary, not isolation from malicious same-UID
code. The human reviews every request; CLI or chat approval is relayed here.
"""
import sys
from pathlib import Path

# -I excludes the current directory. Installed modules live beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import base64
import ctypes
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import pwd
import re
import secrets
import select
import signal
import socket
import socketserver
import sqlite3
import stat
import struct
import threading
import time

from db_query_control import Store, Supervisor, Denied
from db_prod_diagnostics import Diagnostics
from db_prod_transport import DEFAULT_OBSERVER_TIMEOUT
from db_prod_profiles import TARGETS, ProfileError, LocalKeychain, profile_digest
from db_prod_recovery import (
    RECOVERY_APPROVAL_TTL,
    RECOVERY_OBSERVER_MAX_BYTES,
    RECOVERY_OBSERVER_MAX_ROWS,
    RECOVERY_OBSERVER_TIMEOUT,
    RECOVERABLE_PHASES,
    RecoveryDenied,
    RecoveryJournal,
    approve_recovery_approval,
    create_recovery_approval,
    current_user_sqlcmd_absent,
    ensure_recovery_approval_table,
    observer_recovery_digest,
    recover,
)
from db_prod_watchdog import (
    DEFAULT_STOP_MARKERS,
    StopMarkerError,
    create_stop_marker,
    cancel_markers_only,
    list_stop_markers,
    process_fingerprint,
    remove_stop_markers,
    stop_latched,
)

INSTALL = Path(__file__).resolve().parent


def current_source_fingerprint():
    """Identify installed code without reading config, credentials or results."""
    digest = hashlib.sha256()
    paths = sorted(INSTALL.glob("db_prod_*.py")) + [INSTALL / "db_query_control.py"]
    for path in paths:
        digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


# Capture once: later disk edits must not masquerade as running code updates.
RUNTIME_FINGERPRINT = current_source_fingerprint()

STATE = Path.home() / "Library/Application Support/team2-db"
# Darwin Unix socket paths are short; the directory is owner-only.
SOCKET = Path("/tmp") / ("team2-db-" + str(os.getuid())) / "query.sock"
LATCH = DEFAULT_STOP_MARKERS
MAX_MESSAGE = 1024 * 1024
RESOURCE_MAX_BYTES = None  # User-authorized time-only result limits.
# macOS AF_UNIX commonly has an 8 KiB send buffer. Base64 + JSON must fit a
# single nonblocking send while the stop/finish transaction is held.
RESULT_CHUNK_BYTES = 2048
PROBE_SQL = "SELECT 1 AS connection_ok;"
SESSION_VISIBILITY_PROBE_SQL = (
    "WAITFOR DELAY '00:00:10';\n"
    "SELECT @@SPID AS session_id, APP_NAME() AS program_name;"
)
SESSION_STOP_PROBE_SQL = (
    "WAITFOR DELAY '00:00:30';\n"
    "SELECT @@SPID AS session_id, APP_NAME() AS program_name;"
)


def validate_read_sql(sql):
    """Defense in depth; actual SELECT-only DB permissions remain mandatory."""
    # Remove literals, quoted identifiers and nested comments before examining
    # reserved operation words. Unterminated constructs fail closed.
    words, i = [], 0
    while i < len(sql):
        if sql.startswith("--", i):
            end = sql.find("\n", i)
            i = len(sql) if end < 0 else end + 1
        elif sql.startswith("/*", i):
            depth, i = 1, i + 2
            while i < len(sql) and depth:
                if sql.startswith("/*", i): depth, i = depth + 1, i + 2
                elif sql.startswith("*/", i): depth, i = depth - 1, i + 2
                else: i += 1
            if depth: raise Denied("unterminated_sql_comment")
        elif sql[i] in "'\"[":
            close = "]" if sql[i] == "[" else sql[i]
            i += 1
            while i < len(sql):
                if sql[i] == close:
                    if i + 1 < len(sql) and sql[i+1] == close: i += 2
                    else: i += 1; break
                else: i += 1
            else: raise Denied("unterminated_sql_literal")
        elif sql[i].isalpha() or sql[i] in "_@#":
            start = i
            while i < len(sql) and (sql[i].isalnum() or sql[i] in "_@$#"): i += 1
            words.append(sql[start:i].upper())
        else:
            if ord(sql[i]) < 32 and sql[i] not in "\r\n\t":
                raise Denied("sql_control_character")
            i += 1
    forbidden = {"INSERT", "UPDATE", "DELETE", "MERGE", "INTO", "TRUNCATE", "CREATE", "ALTER", "DROP",
                 "EXEC", "EXECUTE", "GRANT", "DENY", "REVOKE", "BACKUP", "RESTORE", "DBCC", "KILL",
                 "RECONFIGURE", "SHUTDOWN", "USE", "OPENROWSET", "OPENQUERY", "OPENDATASOURCE"}
    if forbidden.intersection(words):
        raise Denied("production_read_only_sql_required")
    if any(words[i:i + 3] == ["NEXT", "VALUE", "FOR"] for i in range(len(words) - 2)):
        raise Denied("sequence_value_consumption_forbidden")
    # SQL Server permits omitting EXEC only for a module call at batch start.
    # Accept statement introducers, never a bare/quoted procedure identifier.
    if not words or words[0] not in {"SELECT", "WITH", "DECLARE", "SET", "IF", "WHILE", "BEGIN", "WAITFOR", "RETURN", "PRINT"}:
        raise Denied("implicit_procedure_execution_forbidden")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_local_references(sql):
    """Reject explicit 3/4-part references for operator-opened, unverified logins.

    This is not a permission proof: a local view/synonym may have dependencies
    elsewhere. The review separately exposes that verification is incomplete.
    """
    import re
    normalized, i = [], 0
    while i < len(sql):
        if sql.startswith("--", i):
            end = sql.find("\n", i)
            i = len(sql) if end < 0 else end + 1
            normalized.append(" ")
        elif sql.startswith("/*", i):
            depth, i = 1, i + 2
            while i < len(sql) and depth:
                if sql.startswith("/*", i): depth, i = depth + 1, i + 2
                elif sql.startswith("*/", i): depth, i = depth - 1, i + 2
                else: i += 1
            if depth: raise Denied("unterminated_sql_comment")
            normalized.append(" ")
        elif sql[i] in "'\"[":
            opening = sql[i]
            closing = "]" if opening == "[" else opening
            i += 1
            while i < len(sql):
                if sql[i] == closing:
                    if i + 1 < len(sql) and sql[i + 1] == closing: i += 2
                    else: i += 1; break
                else: i += 1
            else: raise Denied("unterminated_sql_literal")
            normalized.append(" q " if opening != "'" else " ")
        else:
            normalized.append(sql[i])
            i += 1
    identifier = r"[A-Za-z_@#\u0080-\uffff][\w@$#]*"
    if re.search(identifier + r"\s*\.\s*(?:" + identifier + r")?\s*\.", "".join(normalized)):
        raise Denied("explicit_cross_database_reference_requires_verified_permissions")


def peer_uid(sock):
    if sys.platform == "darwin":
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.getpeereid(sock.fileno(), ctypes.byref(uid), ctypes.byref(gid)):
            raise Denied("peer_authentication_failed")
        return uid.value
    if hasattr(socket, "SO_PEERCRED"):
        return struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]
    raise Denied("unsupported_peer_authentication")


def receive(sock):
    data = bytearray()
    while b"\n" not in data:
        part = sock.recv(min(65536, MAX_MESSAGE + 1 - len(data)))
        if not part:
            raise Denied("incomplete_request")
        data.extend(part)
        if len(data) > MAX_MESSAGE:
            raise Denied("request_too_large")
    line, tail = data.split(b"\n", 1)
    if tail:
        raise Denied("one_request_per_connection")
    request = json.loads(line)
    if not isinstance(request, dict):
        raise Denied("invalid_request")
    return request


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"


class LatchStore(Store):
    """An independent operator can halt even a frozen gateway via a latch."""
    def __init__(self, path, latch=LATCH):
        super().__init__(path)
        self.latch = Path(latch)

    def _observe_latch(self):
        if stop_latched(self.latch):
            state = super().status()
            if not state["halted"]:
                if cancel_markers_only(self.latch):
                    super().cancel()
                else:
                    super().stop("independent_emergency_stop")

    def status(self):
        self._observe_latch()
        return super().status()

    def reserve(self, *args, **kwargs):
        self._observe_latch()
        return super().reserve(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        self._observe_latch()
        return super().dispatch(*args, **kwargs)

    def finish(self, *args, **kwargs):
        self._observe_latch()
        return super().finish(*args, **kwargs)


class Audit:
    """No SQL, host, account, credential or result contents in the audit log."""
    def __init__(self, path):
        self.path = Path(path)
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS events(time REAL, event TEXT, detail TEXT)")
        os.chmod(self.path, 0o600)

    def write(self, event, **detail):
        with sqlite3.connect(self.path, timeout=0.1) as conn:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("INSERT INTO events VALUES (?,?,?)", (time.time(), event, json.dumps(detail, sort_keys=True)))


class LazyBackend:
    """Passwords are resolved only after Store.reserve consumes an approval."""
    def __init__(self, factory, before_start=lambda run: None, after_start=lambda run, backend: None):
        self.factory, self.backend = factory, None
        self.started = False
        self.admitted = threading.Event()
        self.before_start = before_start
        self.after_start = after_start
        self._diagnostics = Diagnostics()

    def start(self, run):
        self.admitted.set()
        stage = "journal"
        try:
            self.before_start(run)
            stage = "credentials"
            self.backend = self.factory()
            self.started = True
            stage = "startup"
            identity = self.backend.start(run)
            stage = "journal"
            self.after_start(run, self.backend)
            return identity
        except Exception as error:
            self._diagnostics.failure(stage, error)
            raise

    def diagnostics(self):
        local = self._diagnostics.snapshot()
        reader = getattr(self.backend, "diagnostics", None)
        if reader is not None:
            try:
                transport = reader()
                stages = {item["stage"] for item in transport}
                return [item for item in local if item["stage"] not in stages] + transport
            except Exception:
                # Reporting must never replace the execution/cleanup outcome.
                pass
        return local

    def dispatch(self, *args):
        return self.backend.dispatch(*args)

    @property
    def completion_basis(self):
        return getattr(self.backend, "completion_basis", None)

    def poll(self):
        return self.backend.poll()

    def cancel(self):
        if self.backend is not None:
            self.backend.cancel()

    def closed(self):
        # Failure before backend creation cannot leave a DB connection.
        return True if not self.started else self.backend.closed()


class Gateway:
    def __init__(
        self,
        store,
        vault,
        audit,
        targets,
        *,
        allowed_uids,
        backend_type,
        recovery_journal=None,
        recovery_process_probe=process_fingerprint,
        recovery_pid_presence_probe=None,
        recovery_sleep=time.sleep,
        recovery_session_observer=None,
        supervisor_factory=Supervisor,
    ):
        self.store, self.vault, self.audit = store, vault, audit
        self.targets, self.allowed_uids = targets, set(allowed_uids)
        self.backend_type = backend_type
        self.pending = {}
        self.recovery_pending = {}
        self.results = {}
        self.lock = threading.RLock()
        self.recovery_journal = recovery_journal or RecoveryJournal(Path(store.path).parent)
        self.recovery_process_probe = recovery_process_probe
        self.recovery_pid_presence_probe = recovery_pid_presence_probe
        self.recovery_sleep = recovery_sleep
        self.recovery_session_observer = recovery_session_observer
        self.supervisor_factory = supervisor_factory
        self.stop_lock_path = Path(store.path).parent / "stop.lock"
        self.gateway_pid = os.getpid()
        self.gateway_birth = process_fingerprint(self.gateway_pid)
        ensure_recovery_approval_table(self.store)

    def _operator(self, uid):
        if uid != os.getuid():
            raise Denied("operator_authentication_required")

    def _record(self, event, **detail):
        try:
            self.audit.write(event, **detail)
        except Exception:
            try:
                create_stop_marker(self._latch_path(), reason="audit_unavailable")
            except StopMarkerError:
                pass
            self.store.stop("audit_unavailable")
            raise Denied("audit_unavailable") from None

    @contextmanager
    def _stop_lock(self):
        try:
            descriptor = os.open(
                self.stop_lock_path,
                os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.chmod(self.stop_lock_path, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError:
            raise Denied("stop_lock_unavailable") from None
        try:
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @staticmethod
    def _stop_generation(state):
        return state["epoch"] if state["halted"] else None

    def _latch_path(self):
        return (Path(self.store.latch) if isinstance(self.store, LatchStore)
                else Path(self.store.path).parent / "stop.d")

    def _stop_markers(self):
        try:
            return list_stop_markers(self._latch_path())
        except StopMarkerError as error:
            raise Denied(str(error)) from None

    def _state_with_stop_markers(self):
        markers = self._stop_markers()
        state = self.store.status()
        # A generic Store does not have LatchStore's read hook.  Synchronize
        # once here so an independent marker cannot leave an apparently live
        # coordinator until the next request.
        if markers and not state["halted"]:
            if cancel_markers_only(self._latch_path(), markers):
                self.store.cancel()
            else:
                self.store.stop("independent_emergency_stop")
            state = self.store.status()
            markers = self._stop_markers()
        return state, markers

    def _settle_cancel(self):
        """Allow fresh approvals only after a soft cancellation is safely idle.

        Store.finish clears active only with server closure proof. Startup,
        faults and unconfirmed slots remain halted and require explicit recovery.
        """
        with self._stop_lock():
            state, markers = self._state_with_stop_markers()
            if (not state["halted"] or state["active"] is not None or state["phase"] != "idle"
                    or state["reason"] != "operator_cancel"
                    or not cancel_markers_only(self._latch_path(), markers)):
                return False
            self._record("cancel_release_requested", epoch=state["epoch"], stop_markers=list(markers))
            try:
                # Remove only this snapshot while the DB admission gate is
                # still closed. A concurrent stop changes epoch or leaves a
                # new marker, and can never restore an old approval.
                remove_stop_markers(self._latch_path(), markers)
                if not self.store.clear(state, resume=True, reason="operator_cancel_completed"):
                    return False
                remaining = self._stop_markers()
                if remaining:
                    if cancel_markers_only(self._latch_path(), remaining):
                        self.store.cancel()
                    else:
                        self.store.stop("stop_marker_changed")
                    return False
            except (StopMarkerError, OSError):
                self.store.stop("cancel_release_failed")
                return False
            self._record("cancel_ready", epoch=self.store.status()["epoch"])
            return True

    def _owned(self, request_id, uid):
        entry = self.pending.get(request_id)
        if entry is None or entry["uid"] != uid:
            raise Denied("request_not_found")
        return entry

    def _recovery_owned(self, request_id, uid):
        entry = self.recovery_pending.get(request_id)
        if entry is None or entry["uid"] != uid:
            raise Denied("recovery_request_not_found")
        return entry

    def _recovery_context(self):
        state = self.store.status()
        if not state["halted"]:
            raise Denied("recovery_requires_halted")
        if not state["active"] or state["phase"] not in RECOVERABLE_PHASES:
            raise Denied("recovery_phase_not_recoverable")
        try:
            record = self.recovery_journal.read(state["active"])
        except RecoveryDenied:
            raise Denied("recovery_journal_unavailable") from None
        metadata = record.metadata
        target = metadata["target"]
        stored_target = state.get("target")
        if not isinstance(stored_target, str) or stored_target.split(":", 1)[0] != target:
            raise Denied("recovery_target_changed")
        try:
            profile = self.vault.profile(target)
            current_profile_digest = profile_digest(profile)
        except Exception:
            raise Denied("recovery_profile_unavailable") from None
        if current_profile_digest != metadata["profile_digest"]:
            raise Denied("recovery_profile_changed")
        try:
            protocol = self.backend_type.review_sql(metadata["host_tag"])
            observer_sql = protocol["observer_sql"]
        except Exception:
            raise Denied("recovery_observer_unavailable") from None
        if not isinstance(observer_sql, str) or not observer_sql.strip():
            raise Denied("recovery_observer_unavailable")
        try:
            digest = observer_recovery_digest(
                run_id=record.run_id,
                epoch=state["epoch"],
                target=target,
                database=metadata["database"],
                host_tag=metadata["host_tag"],
                profile_digest=metadata["profile_digest"],
                observer_sql=observer_sql,
            )
        except RecoveryDenied:
            raise Denied("recovery_observer_invalid") from None
        return state, record, protocol, observer_sql, digest

    def recovery_prepare(self, request, uid):
        self._operator(uid)
        with self.lock:
            if any(entry.get("executing") for entry in self.recovery_pending.values()):
                raise Denied("recovery_execution_in_progress")
        state, record, protocol, observer_sql, digest = self._recovery_context()
        for key, expected in (("target", record.metadata["target"]), ("database", record.metadata["database"])):
            if key in request and request[key] != expected:
                raise Denied("recovery_binding_changed")
        request_id = secrets.token_hex(16)
        try:
            create_recovery_approval(
                self.store,
                request_id=request_id,
                run_id=record.run_id,
                epoch=state["epoch"],
                target=record.metadata["target"],
                database=record.metadata["database"],
                host_tag=record.metadata["host_tag"],
                profile_digest=record.metadata["profile_digest"],
                digest=digest,
            )
        except RecoveryDenied as error:
            raise Denied(str(error)) from None
        review = {
            "kind": "observer-only-recovery",
            "approved": False,
            "recovery_request_id": request_id,
            "request_id": request_id,
            "run_id": record.run_id,
            "epoch": state["epoch"],
            "target": record.metadata["target"],
            "database": record.metadata["database"],
            "host_tag": record.metadata["host_tag"],
            "profile_digest": record.metadata["profile_digest"],
            "observer_sql": observer_sql,
            "timeout": RECOVERY_OBSERVER_TIMEOUT,
            "max_rows": RECOVERY_OBSERVER_MAX_ROWS,
            "max_bytes": RECOVERY_OBSERVER_MAX_BYTES,
            "digest": digest,
            "expires_in": int(RECOVERY_APPROVAL_TTL),
        }
        entry = {"uid": uid, "review": review, "plan": dict(review), "executing": False,
                 "created": time.monotonic()}
        with self.lock:
            now = time.monotonic()
            self.recovery_pending = {
                key: value for key, value in self.recovery_pending.items()
                if value["executing"] or now - value["created"] < RECOVERY_APPROVAL_TTL
            }
            if len(self.recovery_pending) >= 128:
                raise Denied("too_many_recovery_requests")
            self.recovery_pending[request_id] = entry
        self._record("recovery_prepared", request_id=request_id, run_id=record.run_id, digest=digest)
        return {"ok": True, "review": review}

    def recovery_review(self, request_id, uid):
        self._operator(uid)
        entry = self._recovery_owned(request_id, uid)
        return {"ok": True, "review": dict(entry["review"])}

    def recovery_approve(self, request, uid):
        self._operator(uid)
        request_id = request.get("recovery_request_id", request.get("request_id"))
        entry = self._recovery_owned(request_id, uid)
        source = request.get("approval_source")
        if source not in {"human-terminal", "explicit-user-chat"}:
            raise Denied("explicit_approval_source_required")
        try:
            approve_recovery_approval(self.store, request_id, request.get("digest"), operator=source)
        except RecoveryDenied as error:
            raise Denied(str(error)) from None
        with self.lock:
            entry["plan"]["approved"] = True
            entry["review"]["approved"] = True
        self._record("recovery_approved", request_id=request_id, uid=uid,
                     digest=request.get("digest"), source=source)
        return {"ok": True, "recovery_request_id": request_id}

    def _observe_recovery_sessions(self, plan, diagnostics=None):
        target = plan["target"]
        backend = None
        local = Diagnostics()
        try:
            profile = self.vault.profile(target)
            if profile_digest(profile) != plan["profile_digest"]:
                raise Denied("recovery_profile_changed")
            credentials = self.vault.credentials(target, profile)
            backend = self.backend_type(
                credentials,
                plan["database"],
                observer_credentials=credentials,
                host_tag=plan["host_tag"],
                startup_timeout=RECOVERY_OBSERVER_TIMEOUT,
                observer_timeout=RECOVERY_OBSERVER_TIMEOUT,
                query_timeout=RECOVERY_OBSERVER_TIMEOUT,
            )
            observer = getattr(backend, "observe_closed", None)
            if not callable(observer):
                return False
            result = observer(plan["host_tag"], timeout=RECOVERY_OBSERVER_TIMEOUT)
            if hasattr(result, "permission_ok") and hasattr(result, "sessions"):
                return {"permission_ok": result.permission_ok, "sessions": result.sessions}
            if isinstance(result, bool):
                return result
            return result
        except Denied:
            raise
        except Exception as error:
            local.failure("credentials" if backend is None else "observer", error)
            raise Denied("recovery_observer_failed") from None
        finally:
            if diagnostics is not None:
                diagnostics.extend(local.snapshot())
                reader = getattr(backend, "diagnostics", None)
                if callable(reader):
                    diagnostics.extend(reader())

    def recovery_execute(self, request_id, uid):
        self._operator(uid)
        with self.lock:
            entry = self._recovery_owned(request_id, uid)
            if entry["executing"]:
                raise Denied("recovery_execution_already_requested")
            if entry["plan"].get("approved") is not True:
                raise Denied("recovery_approval_required")
            entry["executing"] = True
            plan = dict(entry["plan"])
        completed = False
        diagnostics = []
        try:
            observer = self.recovery_session_observer or (
                lambda plan: self._observe_recovery_sessions(plan, diagnostics))
            kwargs = dict(
                journal=self.recovery_journal,
                watchdog_grace=5,
                sleep=self.recovery_sleep,
                allow_unknown_worker=True,
                unknown_worker_absence_probe=current_user_sqlcmd_absent,
            )
            if self.recovery_pid_presence_probe is not None:
                kwargs["pid_presence_probe"] = self.recovery_pid_presence_probe
            try:
                result = recover(
                    plan,
                    self.store,
                    observer,
                    process_probe=self.recovery_process_probe,
                    **kwargs,
                )
            except RecoveryDenied as error:
                self._record("recovery_failed", request_id=request_id, run_id=plan["run_id"],
                             status=str(error), diagnostics=diagnostics)
                return dict(ok=False, status=str(error), run_id=plan["run_id"],
                            diagnostics=diagnostics, session_closed=False)
            self._record("recovery_completed", request_id=request_id, run_id=result["run_id"], digest=result["digest"])
            completed = True
            return result
        finally:
            consumed = False
            try:
                with self.store.transaction() as connection:
                    row = connection.execute(
                        "SELECT status FROM recovery_approvals WHERE id=?", (request_id,)
                    ).fetchone()
                    consumed = row is not None and row["status"] == "consumed"
            except Exception:
                # Keep a pending, unconsumed review available for a retry;
                # an unavailable ledger never permits a new execution.
                consumed = False
            with self.lock:
                if completed or consumed:
                    self.recovery_pending.pop(request_id, None)
                elif request_id in self.recovery_pending:
                    self.recovery_pending[request_id]["executing"] = False

    def prepare(self, request, uid):
        self._settle_cancel()
        target, database, sql = (request.get(k) for k in ("target", "database", "sql"))
        settings = self.targets.get(target, {})
        if target not in TARGETS or not settings.get("enabled"):
            raise Denied("target_not_enabled")
        if not isinstance(database, str) or not database or len(database) > 128 or any(ord(c) < 32 for c in database):
            raise Denied("invalid_database")
        if not isinstance(sql, str) or not sql.strip():
            raise Denied("sql_required")
        self.backend_type.validate_sql(sql)
        validate_read_sql(sql)
        # Operator opening is an authorization decision, not evidence that the
        # database login's SELECT-only grants have been verified. Keep the two
        # states separate and bind the database allowlist into the review digest.
        authorized_databases = settings.get("operator_authorized_read_databases", [])
        operator_authorized = (
            isinstance(authorized_databases, list)
            and all(isinstance(name, str) and name for name in authorized_databases)
            and database in authorized_databases
        )
        if not (settings.get("read_only_verified") or operator_authorized) and sql.strip() not in (
                PROBE_SQL, SESSION_VISIBILITY_PROBE_SQL, SESSION_STOP_PROBE_SQL):
            raise Denied("connection_probe_only_until_read_only_verification")
        if operator_authorized and not settings.get("read_only_verified"):
            validate_local_references(sql)
        limits = {key: request.get(key) for key in ("timeout", "max_rows", "max_bytes")}
        if any(key not in request for key in limits):
            raise Denied("explicit_limits_required")
        query_profile = self.vault.profile(target)
        observer_profile = query_profile
        if (query_profile["host"], query_profile["port"]) != (observer_profile["host"], observer_profile["port"]):
            raise Denied("observer_endpoint_mismatch")
        host_tag = "q-" + secrets.token_hex(16)
        protocol = self.backend_type.review_sql(host_tag)
        binding = dict(target=target, database=database, host_tag=host_tag,
                       query_profile=profile_digest(query_profile), observer_profile=profile_digest(observer_profile),
                       protocol=fingerprint(protocol), settings=fingerprint(settings), resource_max_bytes=RESOURCE_MAX_BYTES)
        spec = dict(owner="uid:"+str(uid), target=target+":"+fingerprint(binding), sql=sql, **limits)
        prepared = self.store.prepare(**spec)
        review = dict(prepared["review"], target=target, database=database,
                      read_access_basis=("verified_database_permissions" if settings.get("read_only_verified")
                                         else "operator_authorized_database_permissions_unverified" if operator_authorized
                                         else "diagnostic_only"),
                      indirect_object_dependencies_verified=False,
                      profile_fingerprint=binding["query_profile"], observer_fingerprint=binding["observer_profile"],
                      control_sql=protocol, output_limit_unit="physical_output_lines",
                      resource_max_bytes=RESOURCE_MAX_BYTES,
                      host_tag=host_tag, request_id=prepared["id"], digest=prepared["digest"])
        entry = dict(uid=uid, spec=spec, review=review, prepared=prepared, target=target,
                     database=database, profiles=(query_profile, observer_profile), binding=binding,
                     created=time.monotonic(), executing=False)
        with self.lock:
            self.pending = {k:v for k,v in self.pending.items() if v["executing"] or time.monotonic()-v["created"] < 1800}
            if len(self.pending) >= 128:
                raise Denied("too_many_pending_requests")
            self.pending[prepared["id"]] = entry
        self._record("prepared", request_id=prepared["id"], owner=spec["owner"], target=target,
                     digest=prepared["digest"])
        return dict(ok=True, review=review)

    def handle(self, request, uid, *, publish=None, disconnected=None):
        if uid not in self.allowed_uids:
            raise Denied("caller_not_authorized")
        action = request.get("action")
        if action == "status":
            self._settle_cancel()
            state, markers = self._state_with_stop_markers()
            return dict(ok=True, halted=bool(state["halted"]), active=state["active"], phase=state["phase"],
                        runtime_fingerprint=RUNTIME_FINGERPRINT,
                        reason=state["reason"], epoch=state["epoch"],
                        stop_generation=self._stop_generation(state), stop_markers=list(markers))
        if action == "settle_cancel":
            self._operator(uid)
            self._settle_cancel()
            state, markers = self._state_with_stop_markers()
            return dict(ok=True, ready_for_new_request=not state["halted"] and state["active"] is None
                        and state["phase"] == "idle",
                        halted=bool(state["halted"]), active=state["active"], phase=state["phase"],
                        stop_markers=list(markers))
        if action == "stop":
            try:
                marker = create_stop_marker(self._latch_path(), reason="operator_cancel")
            except StopMarkerError as error:
                raise Denied(str(error)) from None
            with self._stop_lock():
                state = self.store.cancel()
                with self.lock:
                    self.results.clear()
            self._record("stop", uid=uid)
            self._settle_cancel()
            state, _ = self._state_with_stop_markers()
            return dict(ok=True, halted=bool(state["halted"]), active=state["active"], phase=state["phase"],
                        session_closed=state["active"] is None, epoch=state["epoch"],
                        stop_generation=self._stop_generation(state), stop_marker=marker,
                        stop_markers=list(self._stop_markers()))
        if action == "resume":
            self._operator(uid)
            expected_epoch = request.get("expected_epoch")
            expected_generation = request.get("expected_stop_generation")
            expected_markers = request.get("expected_stop_markers")
            if (type(expected_epoch) is not int or type(expected_generation) is not int
                    or not isinstance(expected_markers, list)
                    or len(expected_markers) > 256
                    or any(not isinstance(name, str) or not name or "/" in name or "\x00" in name
                           or any(ord(char) < 32 for char in name) for name in expected_markers)):
                raise Denied("resume_confirmation_required")
            with self._stop_lock():
                state, markers = self._state_with_stop_markers()
                if (state["epoch"] != expected_epoch
                        or self._stop_generation(state) != expected_generation
                        or list(markers) != expected_markers):
                    raise Denied("resume_confirmation_changed")
                if state["active"] or state["phase"] != "idle" or not state["halted"]:
                    raise Denied("active_session_requires_fencing_and_reconciliation")
                cleared = self.store.clear(state, resume=True)
                if not cleared:
                    raise Denied("resume_state_changed")
                try:
                    # Only the exact immutable nonce list shown to the user is
                    # eligible for deletion.  A marker created after this
                    # request remains and wins over the resume.
                    remove_stop_markers(self._latch_path(), expected_markers)
                    remaining = self._stop_markers()
                    if remaining:
                        raise StopMarkerError("stop_marker_changed")
                    result_state = self.store.status()
                except StopMarkerError as error:
                    try:
                        self.store.stop("resume_stop_marker_changed")
                    except Exception:
                        pass
                    raise Denied(str(error)) from None
            self._record("resume", uid=uid, epoch=expected_epoch,
                         stop_generation=expected_generation, stop_markers=expected_markers)
            return dict(ok=True, halted=bool(result_state["halted"]), active=result_state["active"],
                        phase=result_state["phase"], epoch=result_state["epoch"],
                        stop_generation=self._stop_generation(result_state), stop_markers=[])
        if action in {"recovery_prepare", "recovery-prepare"}:
            return self.recovery_prepare(request, uid)
        if action in {"recovery_review", "recovery-review"}:
            return self.recovery_review(request.get("recovery_request_id", request.get("request_id")), uid)
        if action in {"recovery_approve", "recovery-approve"}:
            return self.recovery_approve(request, uid)
        if action in {"recovery_execute", "recovery-execute"}:
            return self.recovery_execute(request.get("recovery_request_id", request.get("request_id")), uid)
        if action == "prepare":
            return self.prepare(request, uid)
        if action == "fetch":
            return self.fetch(request, uid, publish=publish)
        request_id = request.get("request_id")
        with self.lock:
            entry = self._owned(request_id, uid)
        if action == "review":
            self._operator(uid)
            return dict(ok=True, review=entry["review"])
        if action == "approve":
            self._operator(uid)
            source = request.get("approval_source")
            if source not in {"human-terminal", "explicit-user-chat"}:
                raise Denied("explicit_approval_source_required")
            self.store.approve(request_id, request.get("digest"), operator=source)
            self._record("approved", request_id=request_id, uid=uid, digest=request.get("digest"), source=source)
            return dict(ok=True, request_id=request_id)
        if action != "execute":
            raise Denied("unknown_action")
        with self.lock:
            if entry["executing"]:
                raise Denied("execution_already_requested")
            entry["executing"] = True
        try:
            return self.execute(entry, publish=publish, disconnected=disconnected)
        finally:
            with self.lock:
                self.pending.pop(request_id, None)

    def execute(self, entry, *, publish, disconnected):
        request_id = entry["prepared"]["id"]
        target = entry["target"]
        if fingerprint(self.targets.get(target)) != entry["binding"]["settings"]:
            raise Denied("configuration_changed_new_approval_required")

        deadline = time.monotonic() + entry["spec"]["timeout"]

        def check_start(run):
            if time.monotonic() >= deadline:
                raise Denied("timeout")
            if self.store.status()["halted"]:
                raise Denied("operator_stop")

        def publish_recovery_journal(run):
            check_start(run)
            if not isinstance(self.gateway_birth, str) or not self.gateway_birth:
                raise Denied("gateway_identity_unavailable")
            metadata = {
                "target": target,
                "database": entry["database"],
                "host_tag": entry["binding"]["host_tag"],
                "profile_digest": entry["binding"]["query_profile"],
                "gateway_pid": self.gateway_pid,
                "gateway_birth": self.gateway_birth,
            }
            try:
                self.recovery_journal.write_before_start(run, metadata)
            except RecoveryDenied:
                raise Denied("recovery_journal_publish_failed") from None

        def record_worker_identity(run, backend_instance):
            owns_process = hasattr(backend_instance, "process_pid") or hasattr(backend_instance, "process")
            pid = getattr(backend_instance, "process_pid", None)
            if pid is None:
                process = getattr(backend_instance, "process", None)
                pid = getattr(process, "pid", None)
            if type(pid) is not int or pid <= 1:
                # Synthetic backends without an owned process are used only in
                # tests; the real transport must publish its worker identity.
                if owns_process:
                    raise Denied("worker_identity_unavailable")
                return
            try:
                birth = self.recovery_process_probe(pid)
            except Exception:
                raise Denied("worker_identity_unavailable") from None
            if not isinstance(birth, str) or not birth:
                raise Denied("worker_identity_unavailable")
            try:
                self.recovery_journal.update_worker(run, pid, birth)
            except RecoveryDenied:
                raise Denied("worker_journal_update_failed") from None

        def factory():
            query = self.vault.credentials(target, entry["profiles"][0])
            observer = query
            return self.backend_type(query, entry["database"], observer_credentials=observer,
                                     host_tag=entry["binding"]["host_tag"], query_timeout=entry["spec"]["timeout"],
                                     startup_timeout=min(5, entry["spec"]["timeout"]),
                                     observer_timeout=DEFAULT_OBSERVER_TIMEOUT)

        backend = LazyBackend(
            factory,
            before_start=publish_recovery_journal,
            after_start=record_worker_identity,
        )
        self._record("execution_requested", request_id=request_id, target=target)
        done = threading.Event()

        def watch_client():
            while not done.wait(0.1):
                try:
                    if backend.admitted.is_set() and time.monotonic() >= deadline:
                        try:
                            create_stop_marker(self._latch_path(), reason="timeout")
                        except StopMarkerError:
                            self.store.stop("stop_marker_unavailable")
                        else:
                            self.store.stop("timeout")
                        if backend.backend is not None:
                            backend.cancel()
                        return
                    if disconnected and disconnected():
                        try:
                            create_stop_marker(self._latch_path(), reason="client_disconnected")
                        except StopMarkerError:
                            pass
                        self.store.stop("client_disconnected")
                        return
                except Exception:
                    self.store.stop("client_observer_failed")
                    return

        watcher = threading.Thread(target=watch_client, daemon=True)
        watcher.start()

        committed = threading.Event()
        delivered_run = None

        def deliver(receipt):
            nonlocal delivered_run
            output = backend.backend.output_bytes()
            completion_basis = getattr(backend.backend, "completion_basis", "unknown")
            self._record("completed", request_id=request_id, run_id=receipt["run_id"],
                         result_bytes=len(output), session_closed=True,
                         completion_basis=completion_basis)
            if publish is None:
                raise Denied("result_sink_required")
            with self.lock:
                # Only one unread result retained; no plaintext result files.
                self.results.clear()
                self.results[receipt["run_id"]] = dict(uid=entry["uid"], epoch=receipt["epoch"],
                    data=output, offset=0, expires=time.monotonic()+60,
                    commit_ready=committed, committed=False)
                delivered_run = receipt["run_id"]
            publish(dict(ok=True, status="completed", session_closed=True,
                         runtime_fingerprint=RUNTIME_FINGERPRINT,
                         completion_basis=completion_basis,
                         output_bytes=len(output), output_sha256=hashlib.sha256(output).hexdigest(), **receipt))

        result = None
        try:
            result = self.supervisor_factory(self.store).execute(**entry["spec"], backend=backend,
                                                                 approval_id=request_id, publish=deliver)
        finally:
            # Store.finish publishes a small receipt while holding its transaction.
            # Plaintext stays gated until execute returns after a successful commit.
            with self.lock:
                item = self.results.get(delivered_run)
                if item is not None:
                    if result is not None and result.get("ok"):
                        item["committed"] = True
                    else:
                        self.results.pop(delivered_run, None)
                committed.set()
            done.set()
        if not result["ok"]:
            result["diagnostics"] = backend.diagnostics()
            try:
                failure_state = self.store.status()
                if failure_state["halted"] and failure_state["reason"] != "operator_cancel":
                    create_stop_marker(self._latch_path(), reason=result["status"])
            except StopMarkerError:
                pass
            self._record("execution_failed", request_id=request_id, status=result["status"],
                         run_id=result.get("run_id"), diagnostics=result["diagnostics"],
                         session_closed=result.get("session_closed", False))
            if result.get("session_closed"):
                self._settle_cancel()
        return result

    def fetch(self, request, uid, *, publish):
        # Each small, nonblocking delivery is serialized against stop. A client
        # renders results only after all chunks and the final digest match.
        with self.lock:
            pending = self.results.get(request.get("run_id"))
            ready = pending.get("commit_ready") if pending and pending["uid"] == uid else None
        # Never wait while holding the coordinator transaction or gateway lock.
        if ready is not None and not ready.wait(timeout=1):
            raise Denied("result_commit_pending")
        with self.store.transaction() as connection:
            state = self.store._state(connection)
            with self.lock:
                item = self.results.get(request.get("run_id"))
                if (item is None or not item.get("committed")
                        or item["uid"] != uid or item["epoch"] != state["epoch"]
                        or state["halted"] or stop_latched(self._latch_path())
                        or item["expires"] < time.monotonic()):
                    self.results.pop(request.get("run_id"), None)
                    raise Denied("result_unavailable_or_stopped")
                if request.get("offset") != item["offset"] or publish is None:
                    raise Denied("result_offset_mismatch")
                offset = item["offset"]
                data = item["data"][offset:offset+RESULT_CHUNK_BYTES]
                end = offset + len(data)
                final = end == len(item["data"])
                # Persist intent in memory before non-idempotent send. A lost
                # response cannot cause the same chunk to be emitted twice.
                item["offset"] = end
                if final:
                    self.results.pop(request["run_id"])
                try:
                    publish(dict(ok=True, data_base64=base64.b64encode(data).decode("ascii"),
                                 offset=offset, next_offset=end, final=final))
                except Exception:
                    self.results.pop(request.get("run_id"), None)
                    raise
                return dict(ok=True)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        sent = False
        try:
            self.request.settimeout(5)
            uid = peer_uid(self.request)
            request = receive(self.request)
            self.request.settimeout(75)

            def disconnected():
                readable, _, _ = select.select([self.request], [], [], 0)
                if not readable:
                    return False
                # A protocol violation during execution is also a cancellation.
                self.request.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
                return True

            def publish(value):
                nonlocal sent
                data = encoded(value)
                # Never block the coordinator's stop/finish transaction on output.
                count = self.request.send(data, socket.MSG_DONTWAIT)
                if count != len(data):
                    sent = True  # close partial frame; client never prints it
                    raise Denied("result_delivery_unconfirmed")
                sent = True

            result = self.server.gateway.handle(request, uid, publish=publish, disconnected=disconnected)
            if not sent:
                self.request.sendall(encoded(result))
        except (Denied, ProfileError) as error:
            if not sent:
                self.request.sendall(encoded(dict(ok=False, status=str(error))))
        except Exception:
            if not sent:
                try:
                    self.request.sendall(encoded(dict(ok=False, status="gateway_error")))
                except OSError:
                    pass


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 16


def serve():
    from db_prod_transport import SqlcmdBackend
    if os.geteuid() == 0:
        raise Denied("run_as_current_user_not_root")
    config = json.loads((STATE / "config.json").read_text())
    if STATE.is_symlink() or STATE.stat().st_uid != os.getuid() or STATE.stat().st_mode & 0o077:
        raise Denied("untrusted_state_directory")
    lock = open(STATE / "gateway.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    store = LatchStore(STATE / "control.sqlite3")
    if not store.path.exists():
        # State creation belongs exclusively to the installer.
        raise Denied("control_not_provisioned")
    store.stop("service_started_requires_operator_resume")
    audit = Audit(STATE / "audit.sqlite3")
    vault = LocalKeychain(STATE, STATE / "db-prod-keychain")
    gateway = Gateway(store, vault, audit, config["targets"], allowed_uids=config["allowed_uids"], backend_type=SqlcmdBackend)
    if SOCKET.exists():
        if not stat.S_ISSOCK(SOCKET.lstat().st_mode):
            raise Denied("unexpected_socket_path")
        SOCKET.unlink()
    with Server(str(SOCKET), Handler) as server:
        os.chmod(SOCKET, 0o600)
        server.gateway = gateway
        def halt(*_):
            store.stop("service_shutdown")
            # Worker watchdogs fence connections after the service exits.
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, halt)
        signal.signal(signal.SIGINT, halt)
        server.serve_forever(poll_interval=0.1)


if __name__ == "__main__":
    try:
        if sys.argv[1:] != ["serve"]:
            raise Denied("use_installed_service")
        serve()
    except Exception:
        print("Production gateway unavailable; no credentials or SQL logged.", file=sys.stderr)
        raise SystemExit(1)
