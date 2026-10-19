#!/usr/bin/env python3
"""Bounded ``sqlcmd`` transport for the production query supervisor.

This module is deliberately only a transport.  It does not load Keychain
credentials, issue approvals, or decide whether a statement is allowed.  A
trusted gateway supplies the credentials *after* admission and connects this
backend to :class:`db_query_control.Supervisor`.

The worker is an owned ``sqlcmd`` process group.  User SQL is written exactly
once, after the supervisor's dispatch gate, and is followed by EOF so that no
transport-generated SQL changes the approved batch. Normal completion uses a
successful poll with fully drained streams and process exit. Cancellation or
uncertain completion uses a separate observer query to establish zero sessions.

The default command relies on sqlcmd's documented SQLCMDSERVER/SQLCMDUSER
environment variables.  Its child environment is an explicit, small allowlist:
the inherited process environment is not copied, and HOME points at an empty
service directory so a user's sqlcmd configuration cannot select a target or
change output.  The password is never part of argv.

The command intentionally does not use ``-X1``.  Go sqlcmd v1.10 treats that
flag as disabling environment variables, including SQLCMDSERVER, SQLCMDUSER,
and SQLCMDPASSWORD.  The validator and fixed stdin path reject sqlcmd control
lines before they reach the client; ``-x`` additionally disables variable
substitution in the client.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Mapping, Optional

from db_prod_watchdog import DEFAULT_STOP_LATCH, OwnedProcessWatchdog
from db_prod_diagnostics import Diagnostics


# The current-user daemon uses the reviewed Homebrew sqlcmd installation. The
# gateway still validates the executable/configuration at admission; tests and
# the SQL Server Docker lab inject their own command factory.
SQLCMD_PATH = "/opt/homebrew/bin/sqlcmd"
# The production child has no reason to inherit the daemon's executable search
# path or home directory.  In particular, modern sqlcmd may inspect a config
# below HOME, while SQLCMDINI and other SQLCMD* settings are process controls.
# The service provisioner must keep this directory present and unwritable by
# the daemon; it is intentionally outside the user's home directory.
DEFAULT_CHILD_PATH = "/usr/bin:/bin:/opt/homebrew/bin"
DEFAULT_CHILD_HOME = "/var/empty"
DEFAULT_CHILD_LOCALE = "C.UTF-8"
READY_MARKER = b"SQLCMD_READY"
DEFAULT_STARTUP_TIMEOUT = 5.0
DEFAULT_CANCEL_GRACE = 1.0
OBSERVER_MAX_TIMEOUT = 5.0
OBSERVER_MAX_ROWS = 1
OBSERVER_MAX_BYTES = 256
DEFAULT_OBSERVER_TIMEOUT = OBSERVER_MAX_TIMEOUT
DEFAULT_QUERY_TIMEOUT = 60.0

# These are reviewable control batches.  They contain no user data and are
# the only SQL the transport adds to the worker or observer process.
STARTUP_SQL = (
    "SET NOCOUNT ON;\n"
    "PRINT 'SQLCMD_READY';\n"
    # This is transport-generated control syntax.  It terminates only the
    # handshake batch; user supplied GO remains rejected by _reject_sqlcmd_controls.
    "GO\n"
)


class TransportError(RuntimeError):
    """A generic transport failure safe to expose to the caller."""


@dataclass(frozen=True)
class Credentials(Mapping[str, Any]):
    """Immutable credential snapshot used for one backend instance.

    Mapping methods are provided so injected command/env factories can use
    either ``credentials.host`` or ``credentials[\"host\"]``.  ``repr`` does
    not include the password, and the object cannot be mutated after the
    gateway hands it to the transport.
    """

    host: str
    port: int
    account: str
    password: str

    @classmethod
    def from_value(cls, value: "Credentials | Mapping[str, Any]") -> "Credentials":
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise ValueError("credentials_required")
        try:
            host, port, account, password = (
                value["host"], value["port"], value["account"], value["password"]
            )
        except (KeyError, TypeError):
            raise ValueError("credentials_incomplete") from None
        if (
            not isinstance(host, str)
            or not host.strip()
            or "\x00" in host
            or isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
            or not isinstance(account, str)
            or not account.strip()
            or "\x00" in account
            or not isinstance(password, str)
            or not password
        ):
            raise ValueError("credentials_invalid")
        return cls(host=host, port=port, account=account, password=password)

    def __getitem__(self, key: str) -> Any:
        if key == "host":
            return self.host
        if key == "port":
            return self.port
        if key == "account":
            return self.account
        if key == "password":
            return self.password
        raise KeyError(key)

    def __iter__(self):
        return iter(("host", "port", "account", "password"))

    def __len__(self) -> int:
        return 4

    def __repr__(self) -> str:
        return (
            "Credentials(host={!r}, port={!r}, account={!r}, password='***')"
        ).format(self.host, self.port, self.account)


def _timeout_seconds(value: Any, name: str = "timeout") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_invalid")
    value = float(value)
    if not math.isfinite(value) or value <= 0 or value > 60:
        raise ValueError(f"{name}_invalid")
    return value


def _positive_limit(value: Any, name: str) -> Optional[int]:
    if value is None:
        return None
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}_invalid")
    return value


def _safe_host_tag(host_tag: str) -> str:
    if (
        not isinstance(host_tag, str)
        or not host_tag
        or "\x00" in host_tag
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", host_tag)
    ):
        raise ValueError("host_tag_invalid")
    return host_tag


def _sqlcmd_timeout_arg(timeout: float) -> str:
    # sqlcmd's -l/-t options take integer seconds.  Rounding up preserves the
    # supervisor's hard deadline; the supervisor remains the authoritative cap.
    return str(max(1, int(math.ceil(timeout))))


def default_command_factory(
    credentials: Credentials, database: str, host_tag: str, timeout: float
) -> list[str]:
    """Build argv without putting host, account, or password in the command."""

    del credentials  # Connection values are passed by default_env_factory.
    if not isinstance(database, str) or not database or "\x00" in database:
        raise ValueError("database_invalid")
    host_tag = _safe_host_tag(host_tag)
    timeout_arg = _sqlcmd_timeout_arg(_timeout_seconds(timeout))
    return [
        SQLCMD_PATH,
        "-d",
        database,
        "-H",
        host_tag,
        "-N",
        "true",
        "-C",
        "-x",
        # The console reader drops an unterminated final line at EOF. File
        # input consumes the same stdin bytes without adding SQL or a GO.
        "-i",
        "/dev/stdin",
        "-b",
        "-V",
        "11",
        "-h",
        "-1",
        "-w",
        "65535",
        "-l",
        timeout_arg,
        "-t",
        timeout_arg,
    ]


def default_env_factory(credentials: Credentials) -> dict[str, str]:
    """Return the reviewed child environment.

    Authentication values are the only SQLCMD variables supplied.  The
    process environment is otherwise constructed from fixed values so
    ``SQLCMDINI``, sqlcmd scripting/output settings, proxy settings, and
    unrelated inherited secrets cannot affect an approved batch.  ``HOME`` is
    an isolated service directory rather than the daemon user's home because
    Go sqlcmd can use a per-user configuration below it.

    Go sqlcmd's ``-X1`` compatibility mode disables environment variables,
    including these connection variables, so the default argv omits that flag.
    This function deliberately does not put a password in argv as a fallback.
    """

    return {
        "PATH": DEFAULT_CHILD_PATH,
        "HOME": DEFAULT_CHILD_HOME,
        "LANG": DEFAULT_CHILD_LOCALE,
        "LC_ALL": DEFAULT_CHILD_LOCALE,
        "LC_CTYPE": DEFAULT_CHILD_LOCALE,
        "SQLCMDSERVER": f"{credentials.host},{credentials.port}",
        "SQLCMDUSER": credentials.account,
        "SQLCMDPASSWORD": credentials.password,
    }


def _reject_sqlcmd_controls(sql: str) -> None:
    """Reject sqlcmd meta syntax while leaving ordinary SQL unrestricted."""

    if not isinstance(sql, str) or not sql.strip() or "\x00" in sql:
        raise ValueError("sql_invalid")
    # Variable expansion happens before SQL Server sees the batch, including
    # inside quoted literals.  Reject it everywhere.
    if re.search(r"\$\([^\r\n)]*\)", sql):
        raise ValueError("sqlcmd_variable_rejected")
    for line in sql.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(":") or stripped.startswith("!!"):
            raise ValueError("sqlcmd_command_rejected")
        # The Go sqlcmd parser accepts these legacy commands without a colon
        # (including EXIT(query)).  Only inspect the first token, so an
        # identifier or string containing a command word remains ordinary SQL.
        if re.match(r"(?:EXIT|QUIT|RESET|ED)(?=$|[\s(])", stripped, re.IGNORECASE):
            raise ValueError("sqlcmd_command_rejected")
        if re.match(r"ON[ \t]+ERROR(?=$|[ \t])", stripped, re.IGNORECASE):
            raise ValueError("sqlcmd_command_rejected")
        # GO is a sqlcmd batch separator, not a T-SQL statement.  Reject every
        # first-token form (GO, GO 2, GO;, GO -- comment).  A word such as
        # ``going`` or ``go`` inside a quoted value remains ordinary SQL.
        if re.match(r"GO(?=$|[\s;])", stripped, re.IGNORECASE):
            raise ValueError("sqlcmd_batch_rejected")


def validate_sql(sql: str) -> bool:
    """Public gateway validator for transport-level sqlcmd controls."""

    _reject_sqlcmd_controls(sql)
    return True


def control_sql(host_tag: str) -> str:
    """Return the exact server-session observer batch for review/audit."""

    host_tag = _safe_host_tag(host_tag)
    # host tags are generated from a restricted alphabet; keep the escaping
    # explicit so this method remains safe if its input contract is widened.
    literal = host_tag.replace("'", "''")
    return (
        "SET NOCOUNT ON;\n"
        "DECLARE @has_session_visibility int = CASE WHEN "
        "HAS_PERMS_BY_NAME(NULL, NULL, N'VIEW SERVER STATE') = 1 OR "
        "HAS_PERMS_BY_NAME(NULL, NULL, N'VIEW SERVER PERFORMANCE STATE') = 1 "
        "THEN 1 ELSE 0 END;\n"
        "DECLARE @session_count int = 0, @checks int = 0;\n"
        # Keep the bounded grace INSIDE the single reviewed observer batch.
        # A disconnected client can precede server-side session removal.
        # Never reconnect/retry SQL after this batch's approval is consumed.
        "WHILE @has_session_visibility = 1 AND @checks < 16\n"
        "BEGIN\n"
        "    SELECT @session_count = COUNT(*) FROM sys.dm_exec_sessions AS s\n"
        f"    WHERE s.host_name = N'{literal}' AND s.session_id <> @@SPID;\n"
        "    IF @session_count = 0 BREAK;\n"
        "    SET @checks += 1;\n"
        "    IF @checks < 16 WAITFOR DELAY '00:00:00.200';\n"
        "END;\n"
        "SELECT @has_session_visibility AS has_session_visibility, @session_count AS session_count;\n"
    )


def startup_sql() -> str:
    """Return the exact worker handshake batch for review/audit."""

    return STARTUP_SQL


def review_sql(host_tag: str) -> dict[str, str]:
    """Return every transport-generated SQL batch for approval review."""

    return {
        "setup_sql": startup_sql(),
        "observer_sql": control_sql(host_tag),
        "observer_when": "cancellation_or_uncertain_completion_only",
    }


def _parse_observer_output(stdout: Any) -> "ObserverResult":
    """Parse one bounded observer row without exposing client diagnostics."""

    if isinstance(stdout, str):
        stdout = stdout.encode("utf-8", "replace")
    if not isinstance(stdout, (bytes, bytearray)):
        raise TransportError("observer_failed")
    stdout = bytes(stdout)
    if len(stdout) > OBSERVER_MAX_BYTES:
        raise TransportError("observer_output_bytes_exceeded")
    lines = stdout.splitlines()
    # Go sqlcmd terminates a result set with an extra blank line. Ignore only
    # trailing whitespace framing, after enforcing the raw byte ceiling.
    while lines and not lines[-1].strip():
        lines.pop()
    if len(lines) != OBSERVER_MAX_ROWS:
        raise TransportError("observer_output_rows_exceeded")
    fields = lines[0].strip().split()
    if len(fields) != 2 or any(not re.fullmatch(rb"[0-9]+", field) for field in fields):
        raise TransportError("observer_output_invalid")
    permission, sessions = (int(field) for field in fields)
    if permission not in (0, 1) or sessions < 0:
        raise TransportError("observer_output_invalid")
    return ObserverResult(permission_ok=permission == 1, sessions=sessions)


@dataclass(frozen=True)
class ObserverResult:
    permission_ok: bool
    sessions: int


class SqlcmdBackend:
    """``db_query_control.Supervisor`` backend backed by one sqlcmd worker."""

    def __init__(
        self,
        credentials: Credentials | Mapping[str, Any],
        database: str,
        *,
        observer_credentials: Credentials | Mapping[str, Any] | None = None,
        command_factory: Callable[[Credentials, str, str, float], list[str]] = default_command_factory,
        env_factory: Callable[[Credentials], Mapping[str, str]] = default_env_factory,
        popen_factory: Callable[..., Any] = subprocess.Popen,
        observer_runner: Optional[Callable[..., Any]] = None,
        host_tag: Optional[str] = None,
        watchdog_factory: Callable[..., Any] = OwnedProcessWatchdog,
        stop_latch: Optional[Path] = DEFAULT_STOP_LATCH,
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
        cancel_grace: float = DEFAULT_CANCEL_GRACE,
        observer_timeout: float = DEFAULT_OBSERVER_TIMEOUT,
        query_timeout: float = DEFAULT_QUERY_TIMEOUT,
    ):
        if not isinstance(database, str) or not database or "\x00" in database:
            raise ValueError("database_invalid")
        self._credentials = Credentials.from_value(credentials)
        self._observer_credentials = (
            Credentials.from_value(observer_credentials) if observer_credentials is not None else None
        )
        # A caller may explicitly pass the query snapshot for observation when
        # the deployment has one account with the required DMV permission.
        # Omitting observer_credentials still fails closed in closed(), while
        # the gateway can impose a separate profile when its policy requires
        # one.
        self.database = database
        self.command_factory = command_factory
        # Go sqlcmd emits one empty line after each result set. Only its
        # final terminator is excluded from the physical-row budget; keep
        # every data byte and count empty data rows normally. Injected ODBC
        # transports keep their original physical-line semantics.
        self._go_result_framing = command_factory is default_command_factory
        self.env_factory = env_factory
        self.popen_factory = popen_factory
        self.observer_runner = observer_runner
        self._configured_host_tag = _safe_host_tag(host_tag) if host_tag is not None else None
        self.watchdog_factory = watchdog_factory
        self.stop_latch = Path(stop_latch) if stop_latch is not None else None
        self.startup_timeout = min(_timeout_seconds(startup_timeout, "startup_timeout"), 60.0)
        self.cancel_grace = min(_timeout_seconds(cancel_grace, "cancel_grace"), 60.0)
        self.observer_timeout = min(
            _timeout_seconds(observer_timeout, "observer_timeout"), OBSERVER_MAX_TIMEOUT
        )
        # The worker is created before the per-request timeout is known to the
        # transport.  Keep sqlcmd's own query ceiling at the protocol maximum;
        # Supervisor's monotonic deadline and cancel path enforce the approved
        # per-request timeout.
        self.query_timeout = min(_timeout_seconds(query_timeout, "query_timeout"), 60.0)

        self.parent_pid = os.getpid()
        self.process: Any = None
        self.process_pid: Optional[int] = None
        self.run_id: Optional[str] = None
        self.host_tag: Optional[str] = None
        self.observer_host_tag: Optional[str] = None
        self.identity: Optional[dict[str, Any]] = None
        self._watchdog: Any = None

        self._state_lock = threading.RLock()
        self._diagnostics = Diagnostics()
        self._cancel_lock = threading.Lock()
        self._cancelled = False
        self._dispatch_started = False
        self._query_collecting = False
        self._ready = threading.Event()
        self._ready_probe = bytearray()
        self._writer_error = False
        self._failure_reason: Optional[str] = None
        self._stderr_seen = False
        self._result = bytearray()
        self._output_bytes_seen = 0
        self._newline_count = 0
        self._line_has_bytes = False
        self._max_rows: Optional[int] = None
        self._max_bytes: Optional[int] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._closed_confirmation = False
        self.completion_basis: Optional[str] = None
        self._successful = False
        self._observer_error = False
        # One backend represents one approved execution (or one separately
        # approved recovery observation).  The close proof is therefore a
        # one-use observer operation.  In particular, a failed/nonzero
        # observer result is cached as False so repeated Supervisor.cleanup
        # calls cannot keep opening DMV connections.
        self._observer_attempted = False
        self._observer_attempted_host_tag: Optional[str] = None
        self._observer_cached_result: Optional[ObserverResult] = None
        self._observer_cached_success = False

    @property
    def credentials(self) -> Credentials:
        return self._credentials

    @property
    def observer_credentials(self) -> Optional[Credentials]:
        return self._observer_credentials

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def failure_reason(self) -> Optional[str]:
        return self._failure_reason

    @staticmethod
    def control_sql(host_tag: str) -> str:
        return control_sql(host_tag)

    @staticmethod
    def startup_sql() -> str:
        return startup_sql()

    @staticmethod
    def review_sql(host_tag: str) -> dict[str, str]:
        return review_sql(host_tag)

    @staticmethod
    def validate_sql(sql: str) -> bool:
        """Validate only sqlcmd transport controls; policy lives in gateway."""

        return validate_sql(sql)

    def _child_env(self, credentials: Optional[Credentials] = None) -> dict[str, str]:
        credentials = credentials or self._credentials
        try:
            value = self.env_factory(credentials)
            env = dict(value)
        except Exception:
            raise TransportError("environment_failed") from None
        # Do not trust an injected factory to accidentally omit the password
        # or to replace it with a mutable source.  The secret is still never
        # copied into argv or error strings.
        env["SQLCMDSERVER"] = f"{credentials.host},{credentials.port}"
        env["SQLCMDUSER"] = credentials.account
        env["SQLCMDPASSWORD"] = credentials.password
        return env

    def _read_stream(self, stream: Any, *, stdout: bool) -> None:
        if stream is None:
            return
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8", "replace")
                if not isinstance(chunk, (bytes, bytearray)):
                    self._mark_failure("worker_output_invalid")
                    break
                chunk = bytes(chunk)
                if stdout:
                    self._record_stdout(chunk)
                else:
                    self._record_stderr(chunk)
        except Exception:
            self._mark_failure("worker_output_failed")

    def _record_stdout(self, chunk: bytes) -> None:
        with self._state_lock:
            if not self._ready.is_set():
                self._diagnostics.capture("startup", "stdout", chunk)
                self._ready_probe.extend(chunk)
                if len(self._ready_probe) > 65536:
                    del self._ready_probe[:-65536]
                if READY_MARKER in self._ready_probe:
                    self._ready.set()
                return
            if not self._query_collecting:
                return
            self._record_output_bytes(len(chunk))
            if self._failure_reason is not None:
                return
            self._result.extend(chunk)
            self._newline_count += chunk.count(b"\n")
            if chunk:
                self._line_has_bytes = not chunk.endswith(b"\n")
            self._check_row_limit(final=False)

    def _check_row_limit(self, *, final: bool) -> None:
        physical_lines = self._newline_count + (1 if self._line_has_bytes else 0)
        if self._go_result_framing:
            if self._result.endswith((b"\n\n", b"\r\n\r\n")):
                physical_lines -= 1
            elif not final and self._result.endswith(b"\n\r"):
                # A CRLF result terminator may be split between pipe reads.
                # Defer this single pending CR; EOF rechecks it as data.
                physical_lines -= 1
        if self._max_rows is not None and physical_lines > self._max_rows:
            self._mark_failure("output_rows_exceeded")

    def _record_stderr(self, chunk: bytes) -> None:
        with self._state_lock:
            self._diagnostics.capture("query" if self._query_collecting else "startup", "stderr", chunk)
            if not self._query_collecting:
                return
            self._record_output_bytes(len(chunk))
            self._stderr_seen = True
            if self._failure_reason is None:
                self._failure_reason = "worker_error_output"

    def _record_output_bytes(self, count: int) -> None:
        self._output_bytes_seen += count
        if self._max_bytes is not None and self._output_bytes_seen > self._max_bytes:
            self._failure_reason = "output_bytes_exceeded"

    def _mark_failure(self, reason: str) -> None:
        with self._state_lock:
            if self._failure_reason is None:
                self._failure_reason = reason

    def _spawn(
        self, host_tag: str, timeout: float, credentials: Optional[Credentials] = None,
        *, stage: str = "startup",
    ) -> Any:
        credentials = credentials or self._credentials
        try:
            argv = list(self.command_factory(credentials, self.database, host_tag, timeout))
            env = self._child_env(credentials)
            return self.popen_factory(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=(os.name == "posix"),
                bufsize=0,
            )
        except TransportError as error:
            self._diagnostics.failure(stage, error)
            raise
        except Exception as error:
            self._diagnostics.failure(stage, error, code="process_start_failed")
            raise TransportError("process_start_failed") from None

    @staticmethod
    def _write_all(stream: Any, payload: bytes, *, failure_reason: str) -> None:
        """Write every byte, rejecting short/empty writes fail-closed.

        ``bufsize=0`` gives the transport a raw pipe.  Raw ``write`` calls
        are allowed to return fewer bytes than requested; treating one such
        call as a complete SQL batch could execute a prefix of an approved
        statement.  ``None`` and zero are also failures, because neither
        proves progress toward EOF.
        """

        view = memoryview(payload)
        offset = 0
        try:
            while offset < len(view):
                try:
                    written = stream.write(view[offset:])
                except Exception:
                    raise TransportError(failure_reason) from None
                if (
                    written is None
                    or isinstance(written, bool)
                    or not isinstance(written, int)
                    or written <= 0
                    or written > len(view) - offset
                ):
                    raise TransportError(failure_reason)
                offset += written
        finally:
            view.release()

    def start(self, run: str) -> dict[str, Any]:
        """Spawn and handshake; this method never sends user SQL."""

        try:
            return self._start(run)
        except Exception as error:
            self._diagnostics.failure("startup", error)
            raise

    def diagnostics(self) -> list[dict[str, Any]]:
        """Local snapshot only: never connects, observes, or retries SQL."""
        if self._process_exited():
            # EOF readers may lag process exit, especially during startup.
            for thread in (self._stdout_thread, self._stderr_thread):
                if thread is not None and thread is not threading.current_thread():
                    thread.join(timeout=0.1)
        stage = "query" if self._dispatch_started else "startup"
        self._diagnostics.exit_code(stage, getattr(self.process, "returncode", None))
        if self._failure_reason:
            self._diagnostics.failure(stage, code=self._failure_reason)
        return self._diagnostics.snapshot()

    def _start(self, run: str) -> dict[str, Any]:

        with self._state_lock:
            if self.process is not None:
                raise TransportError("already_started")
        if not isinstance(run, str) or not run:
            raise ValueError("run_invalid")
        # A gateway can allocate the tag before presenting the approval.  In
        # that case the same tag is used here; it is never regenerated from a
        # later run id and therefore remains part of the reviewed target.
        host_tag = self._configured_host_tag or _safe_host_tag(f"q-{run}")
        observer_host_tag = _safe_host_tag(f"{host_tag}-observer")
        self.run_id, self.host_tag, self.observer_host_tag = run, host_tag, observer_host_tag
        process = self._spawn(host_tag, self.query_timeout)
        self.process = process
        self.process_pid = getattr(process, "pid", None)
        if isinstance(self.process_pid, int) and self.process_pid > 1:
            try:
                self._watchdog = self.watchdog_factory(
                    self.process_pid,
                    parent_pid=self.parent_pid,
                    stop_latch=self.stop_latch,
                ).start()
            except Exception:
                self.cancel()
                raise TransportError("watchdog_start_failed") from None
        self._stdout_thread = threading.Thread(
            target=self._read_stream, args=(getattr(process, "stdout", None),),
            kwargs={"stdout": True}, daemon=True, name="team2-sqlcmd-stdout"
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stream, args=(getattr(process, "stderr", None),),
            kwargs={"stdout": False}, daemon=True, name="team2-sqlcmd-stderr"
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        try:
            stdin = getattr(process, "stdin", None)
            if stdin is None:
                raise TransportError("worker_stdin_unavailable")
            self._write_all(
                stdin,
                STARTUP_SQL.encode("utf-8"),
                failure_reason="startup_write_failed",
            )
            stdin.flush()
        except TransportError:
            self.cancel()
            raise
        except Exception:
            self.cancel()
            raise TransportError("startup_write_failed") from None

        deadline = time.monotonic() + min(self.startup_timeout, self.observer_timeout)
        while not self._ready.is_set():
            if self._process_exited():
                self.cancel()
                raise TransportError("startup_failed")
            if time.monotonic() >= deadline:
                self.cancel()
                raise TransportError("startup_timeout")
            time.sleep(0.01)
        self.identity = {"host_tag": host_tag, "pid": self.process_pid, "parent_pid": self.parent_pid}
        return dict(self.identity)

    def dispatch(self, sql: str, limits: Mapping[str, Any] | None) -> None:
        """Enqueue the approved SQL and return without waiting for execution."""

        self.validate_sql(sql)
        limits = dict(limits or {})
        max_rows = _positive_limit(limits.get("max_rows"), "max_rows")
        max_bytes = _positive_limit(limits.get("max_bytes"), "max_bytes")
        timeout = limits.get("timeout", 60)
        _timeout_seconds(timeout)
        with self._state_lock:
            if self.process is None or not self._ready.is_set():
                raise TransportError("not_started")
            if self._dispatch_started:
                raise TransportError("dispatch_already_attempted")
            self._dispatch_started = True
            self._query_collecting = True
            self._max_rows = max_rows
            self._max_bytes = max_bytes
            self._result.clear()
            self._output_bytes_seen = 0
            self._newline_count = 0
            self._line_has_bytes = False
        self._writer_thread = threading.Thread(
            target=self._write_query, args=(sql,), daemon=True, name="team2-sqlcmd-writer"
        )
        self._writer_thread.start()

    def _write_query(self, sql: str) -> None:
        stdin = getattr(self.process, "stdin", None)
        if stdin is None:
            self._writer_error = True
            self._mark_failure("worker_stdin_unavailable")
            return
        try:
            # No newline, PRINT marker, GO, or other transport text is added:
            # the approved SQL is the complete stdin batch.
            self._write_all(
                stdin,
                sql.encode("utf-8"),
                failure_reason="query_write_failed",
            )
            stdin.flush()
        except Exception:
            self._writer_error = True
            self._mark_failure("query_write_failed")
            # A partial/failed write must not leave a prefix of the approved
            # SQL running.  Cancellation is idempotent and poll() will keep
            # the result unreleasable.
            self.cancel()
        finally:
            try:
                stdin.close()
            except Exception:
                pass

    def _process_exited(self) -> bool:
        process = self.process
        if process is None:
            return True
        try:
            return process.poll() is not None
        except Exception:
            return False

    def poll(self) -> Optional[bool]:
        """Return None while running, then a success boolean."""

        if not self._dispatch_started:
            return None
        if self._failure_reason is not None and not self._process_exited():
            self.cancel()
        if not self._process_exited():
            return None
        self._stop_watchdog()
        for thread in (self._writer_thread, self._stdout_thread, self._stderr_thread):
            if thread is not None:
                thread.join(timeout=0.5)
                if thread.is_alive():
                    self._mark_failure("worker_output_unconfirmed")
        with self._state_lock:
            self._check_row_limit(final=True)
            if (self._cancelled or self._failure_reason is not None
                    or self._writer_error or self._stderr_seen):
                self._successful = False
                return False
            try:
                returncode = self.process.returncode
            except Exception:
                returncode = None
            self._successful = returncode == 0
            return self._successful

    def _signal_group(self, sig: int) -> None:
        process = self.process
        if process is None:
            return
        pid = getattr(process, "pid", None)
        try:
            if os.name == "posix" and pid is not None:
                os.killpg(os.getpgid(pid), sig)
            elif hasattr(process, "send_signal"):
                process.send_signal(sig)
            elif sig == getattr(signal, "SIGKILL", signal.SIGTERM) and hasattr(process, "kill"):
                process.kill()
            elif hasattr(process, "terminate"):
                process.terminate()
        except (ProcessLookupError, OSError):
            pass
        except Exception:
            # Cancellation is best effort here; closed() remains the release
            # gate and will keep the central slot held if proof is unavailable.
            pass

    def _stop_watchdog(self) -> None:
        watchdog, self._watchdog = self._watchdog, None
        if watchdog is None:
            return
        try:
            watchdog.close()
        except Exception:
            # Worker/session confirmation remains the release gate.  A
            # missing watchdog acknowledgement is not a success signal.
            self._mark_failure("watchdog_close_failed")

    def cancel(self) -> None:
        """Idempotently interrupt the owned process group, then kill it."""

        with self._cancel_lock:
            if self._cancelled:
                return
            self._cancelled = True
        process = self.process
        if process is None:
            self._stop_watchdog()
            return
        try:
            stdin = getattr(process, "stdin", None)
            if stdin is not None:
                stdin.close()
        except Exception:
            pass
        if self._process_exited():
            self._stop_watchdog()
            return
        self._signal_group(getattr(signal, "SIGINT", signal.SIGTERM))
        deadline = time.monotonic() + self.cancel_grace
        while not self._process_exited() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not self._process_exited():
            self._signal_group(getattr(signal, "SIGKILL", signal.SIGTERM))
            try:
                process.wait(timeout=self.cancel_grace)
            except Exception:
                pass
        self._stop_watchdog()

    def _execute_observer_process(
        self,
        *,
        host_tag: Optional[str] = None,
        observer_host_tag: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ObserverResult:
        target_host_tag = host_tag if host_tag is not None else self.host_tag
        observer_tag = (
            observer_host_tag if observer_host_tag is not None else self.observer_host_tag
        )
        observer_timeout = self.observer_timeout if timeout is None else timeout
        if target_host_tag is None or observer_tag is None or self._observer_credentials is None:
            raise TransportError("observer_not_ready")
        try:
            target_host_tag = _safe_host_tag(target_host_tag)
            observer_tag = _safe_host_tag(observer_tag)
            observer_timeout = _timeout_seconds(observer_timeout, "observer_timeout")
        except (TypeError, ValueError):
            raise TransportError("observer_failed") from None
        if observer_timeout > OBSERVER_MAX_TIMEOUT:
            raise TransportError("observer_timeout_invalid")
        process = self._spawn(observer_tag, observer_timeout, self._observer_credentials, stage="observer")
        stdin = getattr(process, "stdin", None)
        if stdin is None:
            raise TransportError("observer_stdin_unavailable")
        try:
            # communicate(input=...) owns the write/flush/close sequence.  A
            # manual close followed by communicate makes subprocess flush a
            # closed stdin and turns every observer into a false failure.
            stdout, stderr = process.communicate(
                input=control_sql(target_host_tag).encode("utf-8"),
                timeout=observer_timeout,
            )
        except Exception as error:
            if isinstance(error, subprocess.TimeoutExpired):
                self._diagnostics.capture("observer", "stderr", error.stderr)
                self._diagnostics.capture("observer", "stdout", error.output)
            self._diagnostics.failure("observer", error, code="observer_failed")
            self._terminate_observer(process)
            raise TransportError("observer_failed") from None
        self._diagnostics.capture("observer", "stderr", stderr)
        self._diagnostics.exit_code("observer", getattr(process, "returncode", None))
        if stderr:
            self._diagnostics.capture("observer", "stdout", stdout)
            raise TransportError("observer_failed")
        if getattr(process, "returncode", None) != 0:
            self._diagnostics.capture("observer", "stdout", stdout)
            raise TransportError("observer_failed")
        try:
            return _parse_observer_output(stdout)
        except Exception:
            self._diagnostics.capture("observer", "stdout", stdout)
            self._diagnostics.failure("observer", code="observer_result_invalid")
            raise

    @staticmethod
    def _terminate_observer(process: Any) -> None:
        try:
            if getattr(process, "poll", lambda: 0)() is None:
                if hasattr(process, "kill"):
                    process.kill()
                elif hasattr(process, "terminate"):
                    process.terminate()
                if hasattr(process, "wait"):
                    process.wait(timeout=1)
        except Exception:
            pass

    def _claim_observer(self, target_host_tag: str) -> tuple[bool, bool]:
        """Claim the one observer attempt, or return its cached result."""

        with self._state_lock:
            if self._observer_attempted:
                return (
                    False,
                    self._observer_attempted_host_tag == target_host_tag
                    and self._observer_cached_success,
                )
            self._observer_attempted = True
            self._observer_attempted_host_tag = target_host_tag
            # Set the fail-closed value before releasing the lock.  A
            # concurrent cleanup caller cannot start a second observer while
            # the first one is still in flight.
            self._observer_cached_result = None
            self._observer_cached_success = False
            return True, False

    def _cache_observer(
        self,
        target_host_tag: str,
        result: Optional[ObserverResult],
        success: bool,
    ) -> bool:
        if not success:
            code = ("observer_failed" if result is None else
                    "observer_permission_denied" if not result.permission_ok else
                    "observer_sessions_remaining")
            self._diagnostics.failure("observer", code=code)
        with self._state_lock:
            if self._observer_attempted_host_tag == target_host_tag:
                self._observer_cached_result = result
                self._observer_cached_success = bool(success)
            return self._observer_cached_success

    @staticmethod
    def _observer_outcome(result: Any) -> tuple[bool, Optional[ObserverResult]]:
        """Normalize injected observer results without exposing diagnostics."""

        if result is True:
            return True, ObserverResult(permission_ok=True, sessions=0)
        if result is False or result is None:
            return False, None
        if isinstance(result, ObserverResult):
            return result.permission_ok and result.sessions == 0, result
        if isinstance(result, Mapping):
            permission = result.get("permission_ok", result.get("permission"))
            sessions = result.get("sessions")
            if isinstance(sessions, (list, tuple, set)):
                sessions = len(sessions)
            if permission in (True, False) and isinstance(sessions, int):
                normalized = ObserverResult(permission_ok=permission, sessions=sessions)
                return permission is True and sessions == 0, normalized
            return False, None
        if isinstance(result, tuple) and len(result) == 2:
            permission, sessions = result
            if permission in (True, False) and isinstance(sessions, int):
                normalized = ObserverResult(permission_ok=permission, sessions=sessions)
                return permission is True and sessions == 0, normalized
        return False, None

    def _observe(self) -> bool:
        target_host_tag = self.host_tag
        if target_host_tag is None:
            self._observer_error = True
            return False
        try:
            target_host_tag = _safe_host_tag(target_host_tag)
        except (TypeError, ValueError):
            self._observer_error = True
            return False
        claimed, cached = self._claim_observer(target_host_tag)
        if not claimed:
            return cached
        if self._observer_credentials is None:
            self._observer_error = True
            return self._cache_observer(target_host_tag, None, False)
        try:
            if self.observer_runner is None:
                result: Any = self._execute_observer_process()
            else:
                result = self.observer_runner(
                    self._observer_credentials,
                    self.database,
                    self.observer_host_tag,
                    control_sql(target_host_tag),
                    self.observer_timeout,
                )
            success, normalized = self._observer_outcome(result)
            return self._cache_observer(target_host_tag, normalized, success)
        except Exception as error:
            self._diagnostics.failure("observer", error)
            self._observer_error = True
            return self._cache_observer(target_host_tag, None, False)

    def observe_closed(self, host_tag: str, timeout: float = DEFAULT_OBSERVER_TIMEOUT) -> bool:
        """Run only the fixed observer query for a recovery host tag.

        Recovery deliberately uses this path without calling ``start``: no
        worker, startup batch, or user SQL is created.  A configured tag (or
        an already-started worker tag) must match the requested tag before an
        observer process can be spawned.  Every malformed, oversized,
        diagnostic, permission-failed, or timed-out observation returns
        ``False``.
        """

        try:
            requested_tag = _safe_host_tag(host_tag)
            requested_timeout = _timeout_seconds(timeout, "observer_timeout")
        except (TypeError, ValueError):
            return False
        if requested_timeout > OBSERVER_MAX_TIMEOUT:
            return False
        with self._state_lock:
            if (
                self._configured_host_tag is not None
                and requested_tag != self._configured_host_tag
            ):
                return False
            if self.host_tag is not None and requested_tag != self.host_tag:
                return False
            if self._observer_attempted:
                if self._observer_attempted_host_tag != requested_tag:
                    return False
                return self._observer_cached_success
            observer_tag = _safe_host_tag(f"{requested_tag}-observer")
            self.host_tag = requested_tag
            self.observer_host_tag = observer_tag
            self.observer_timeout = requested_timeout
            self._observer_error = False
            self._observer_attempted = True
            self._observer_attempted_host_tag = requested_tag
            self._observer_cached_result = None
            self._observer_cached_success = False
        try:
            result = self._execute_observer_process(
                host_tag=requested_tag,
                observer_host_tag=observer_tag,
                timeout=requested_timeout,
            )
        except Exception as error:
            self._diagnostics.failure("observer", error)
            self._observer_error = True
            self._cache_observer(requested_tag, None, False)
            return False
        return self._cache_observer(
            requested_tag,
            result,
            result.permission_ok and result.sessions == 0,
        )

    def closed(self) -> bool:
        """Accept clean completion; observe server sessions on uncertain exit.

        normal_exit is evidence of completed work and client connection teardown,
        not a DMV assertion that SQL Server has already removed the session row.
        """

        if self._closed_confirmation and (
                self.completion_basis == "observer" or not self._cancelled):
            return True
        if not self._process_exited():
            return False
        with self._state_lock:
            if (self._successful and self._dispatch_started and not self._cancelled
                    and self._failure_reason is None and not self._writer_error
                    and not self._stderr_seen and self.process.returncode == 0
                    and all(thread is not None and not thread.is_alive() for thread in
                            (self._writer_thread, self._stdout_thread, self._stderr_thread))):
                self.completion_basis = "normal_exit"
                self._closed_confirmation = True
                return True
        if self._observe():
            self.completion_basis = "observer"
            self._closed_confirmation = True
            return True
        return False

    def output_bytes(self) -> bytes:
        """Return raw stdout only after successful completion and close proof."""

        with self._state_lock:
            if (not self._successful or not self._closed_confirmation or self._cancelled
                    or self._failure_reason is not None
                    or any(thread is not None and thread.is_alive() for thread in
                           (self._writer_thread, self._stdout_thread, self._stderr_thread))):
                raise TransportError("result_not_releasable")
            return bytes(self._result)

    # Names used by gateways that prefer an explicit result accessor.
    result_bytes = output_bytes


__all__ = [
    "Credentials",
    "ObserverResult",
    "SqlcmdBackend",
    "TransportError",
    "STARTUP_SQL",
    "SQLCMD_PATH",
    "OBSERVER_MAX_TIMEOUT",
    "OBSERVER_MAX_ROWS",
    "OBSERVER_MAX_BYTES",
    "control_sql",
    "startup_sql",
    "review_sql",
    "default_command_factory",
    "default_env_factory",
    "validate_sql",
]

