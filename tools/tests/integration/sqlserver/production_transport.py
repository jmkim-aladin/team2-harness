"""Exercise the production-shaped sqlcmd transport against the disposable lab.

The lab command factory deliberately uses the container's ODBC ``sqlcmd`` and
``docker exec`` because the host binary is not part of this fixture.  This
module never reads a production profile or Keychain entry: all credentials are
the synthetic accounts created by :class:`verify.Lab`.  The observer uses the
fixture ``sa`` account only to exercise the DMV permission/zero-session gate;
the gateway's deployment configuration is responsible for supplying its
least-privilege observer profile.
"""

import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import time

# The helper is launched as a standalone child by the transport.  Its
# inherited PYTHONPATH is not guaranteed to include the repository's tools
# directory, so make the fixture import explicit without touching production
# installation paths.
_TOOLS = Path(__file__).resolve().parents[3]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from db_prod_transport import Credentials, SqlcmdBackend


_CONTAINER_SQLCMD_WRAPPER = r'''pid_file="$1"
shift
rm -f "$pid_file"
# POSIX shells may give an asynchronous command /dev/null as stdin.  Duplicate
# the Docker exec stream before starting the child so startup and the approved
# batch reach the same SQLCMD process.
exec 3<&0
"$@" <&3 &
child="$!"
printf '%s' "$child" > "$pid_file"
trap 'kill -INT "$child" 2>/dev/null || true' INT TERM
wait "$child"
status="$?"
rm -f "$pid_file"
exit "$status"
'''


def _docker_forwarder(payload):
    """Run one Docker exec and forward cancellation to its in-container PID.

    Docker CLI does not reliably deliver a host process-group SIGINT to an
    already-running ``docker exec`` child.  The disposable fixture therefore
    starts a shell wrapper *inside the same container*; the host-side helper
    uses the wrapper's unique PID file to send SIGINT to that exact sqlcmd OS
    process.  This helper is selected only by the Docker integration command
    factory and is never imported by the production gateway.
    """

    docker_argv = payload["docker_argv"]
    kill_argv = payload["kill_argv"]
    cancelled = False
    killers = []

    child = subprocess.Popen(
        docker_argv,
        stdin=sys.stdin.buffer,
        stdout=sys.stdout.buffer,
        stderr=sys.stderr.buffer,
    )

    def forward(signum, _frame):
        nonlocal cancelled
        cancelled = True
        try:
            # A separate session lets this short control command finish even
            # when the transport subsequently SIGKILLs this forwarding group.
            killer = subprocess.Popen(
                kill_argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            killers.append(killer)
        except OSError:
            pass
        try:
            child.send_signal(signum)
        except (ProcessLookupError, OSError):
            pass

    signal.signal(signal.SIGINT, forward)
    signal.signal(signal.SIGTERM, forward)
    status = child.wait()
    for killer in killers:
        try:
            killer.wait(timeout=2)
        except subprocess.TimeoutExpired:
            killer.kill()
            killer.wait(timeout=1)
    # A transport cancellation is a failed query even if sqlcmd happened to
    # exit 0 while handling EOF.  Preserve ordinary status for normal runs.
    return (128 + signal.SIGINT) if cancelled else status


def _forwarding_command(lab, current, database, tag, timeout):
    """Build the Docker-only host wrapper command for one SQLCMD process."""

    base = lab.sql_args(current.account, database, int(math.ceil(timeout)))
    # Lab.sql_args is deliberately the single source for its ODBC flags.  Its
    # first six arguments are docker exec's transport prefix; the remaining
    # arguments are the in-container sqlcmd invocation.
    if len(base) < 7 or base[0:2] != ["docker", "exec"]:
        raise RuntimeError("unexpected_docker_sqlcmd_argv")
    prefix, sqlcmd_argv = base[:6], base[6:]
    pid_file = "/tmp/team2-sqlcmd-" + tag + ".pid"
    sqlcmd_argv = sqlcmd_argv + ["-H", tag]
    docker_argv = prefix + [
        "/bin/sh",
        "-c",
        _CONTAINER_SQLCMD_WRAPPER,
        "team2-sqlcmd-wrapper",
        pid_file,
        *sqlcmd_argv,
    ]
    kill_script = (
        "if test -r "
        + pid_file
        + "; then kill -INT \"$(cat "
        + pid_file
        + ")\" 2>/dev/null || true; fi"
    )
    kill_argv = ["docker", "exec", lab.name, "/bin/sh", "-c", kill_script]
    payload = json.dumps(
        {"docker_argv": docker_argv, "kill_argv": kill_argv},
        separators=(",", ":"),
    )
    return [sys.executable, str(Path(__file__).resolve()), "--docker-forward", payload]


def _backend(lab, account, observer_account, host_tag):
    """Build one backend with only the Docker lab transport overridden."""

    credentials = Credentials(
        host="127.0.0.1",
        port=1433,
        account=account,
        password=lab.passwords[account],
    )
    observer = Credentials(
        host="127.0.0.1",
        port=1433,
        account=observer_account,
        password=lab.passwords[observer_account],
    )

    def command_factory(current, database, tag, timeout):
        # The Docker lab's SQLCMD is the legacy ODBC client.  It accepts the
        # reviewed host tag and receives the password through SQLCMDPASSWORD.
        return _forwarding_command(lab, current, database, tag, timeout)

    def env_factory(current):
        return lab.sql_env(current.account)

    return SqlcmdBackend(
        credentials,
        "ProdFixture",
        observer_credentials=observer,
        command_factory=command_factory,
        env_factory=env_factory,
        popen_factory=subprocess.Popen,
        host_tag=host_tag,
        stop_latch=None,
        startup_timeout=10,
        cancel_grace=0.5,
        observer_timeout=3,
        query_timeout=30,
    )


def _poll(backend, timeout=15):
    deadline = time.monotonic() + timeout
    result = None
    while time.monotonic() < deadline:
        result = backend.poll()
        if result is not None:
            return result
        time.sleep(0.05)
    backend.cancel()
    raise RuntimeError("production transport poll deadline exceeded")


def _close(backend, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if backend.closed():
            return True
        time.sleep(0.1)
    return False


def verify_production_transport(lab):
    """Run transport handshake, gating, caps, cancel, and observer checks."""

    backends = []

    def make(account="lab_prod", observer="sa", tag=None):
        backend = _backend(
            lab,
            account,
            observer,
            tag or ("t2q-lab-" + account + "-" + str(len(backends))),
        )
        backends.append(backend)
        return backend

    try:
        reviewed_tag = "t2q-lab-reviewed"
        reviewed = SqlcmdBackend.review_sql(reviewed_tag)
        lab.record(
            "production transport exposes reviewed observer SQL",
            "VIEW SERVER STATE" in reviewed["observer_sql"]
            and "s.session_id <> @@SPID" in reviewed["observer_sql"]
            and reviewed_tag in reviewed["observer_sql"],
        )

        read = make(tag=reviewed_tag)
        identity = read.start("lab-read")
        read.dispatch(
            "SELECT Status FROM dbo.SafeStatus WHERE Id=1;",
            {"timeout": 10, "max_rows": 1, "max_bytes": 4096},
        )
        completed = _poll(read)
        closed = _close(read)
        output = read.output_bytes() if completed and closed else b""
        lab.record(
            "production transport reads only the approved result",
            completed and closed and b"active" in output and identity["host_tag"] == reviewed_tag,
            output_bytes=len(output),
            host_tag=identity["host_tag"],
        )

        capped = make(tag="t2q-lab-row-cap")
        capped.start("lab-row-cap")
        capped.dispatch(
            "SELECT Status FROM dbo.SafeStatus WHERE Id=1 UNION ALL "
            "SELECT Status FROM dbo.SafeStatus WHERE Id=1;",
            {"timeout": 10, "max_rows": 1, "max_bytes": 4096},
        )
        cap_result = _poll(capped)
        lab.record(
            "production transport enforces physical output row cap",
            cap_result is False and capped.failure_reason == "output_rows_exceeded",
            failure_reason=capped.failure_reason,
        )
        _close(capped)

        cancelled = make(account="lab_cancel", tag="t2q-lab-cancel")
        cancelled.start("lab-cancel")
        cancelled.dispatch(
            "WAITFOR DELAY '00:00:20'; SELECT Status FROM dbo.SafeStatus WHERE Id=1;",
            {"timeout": 5, "max_rows": 1, "max_bytes": 4096},
        )
        # Confirm that the query reached SQL Server before fencing its owned
        # process group.  This keeps the cancellation check meaningful.
        running = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            running = (
                lab.scalar(
                    "SELECT COUNT(*) FROM sys.dm_exec_requests AS r "
                    "JOIN sys.dm_exec_sessions AS s ON s.session_id=r.session_id "
                    f"WHERE s.host_name=N'{cancelled.host_tag}' AND r.command=N'WAITFOR';"
                )
                == "1"
            )
            if running:
                break
            time.sleep(0.1)
        cancelled.cancel()
        cancel_result = _poll(cancelled, timeout=5)
        cancel_closed = _close(cancelled)
        observer_probe = None
        try:
            observer_probe = cancelled._execute_observer_process()
        except Exception as error:
            observer_probe = {"error": type(error).__name__}
        lab.record(
            "production transport cancels the owned group and confirms closure",
            running and cancel_result is False and cancelled.cancelled and cancel_closed,
            running=running,
            cancel_result=cancel_result,
            cancelled=cancelled.cancelled,
            closed=cancel_closed,
            process_returncode=getattr(cancelled.process, "returncode", None),
            failure_reason=cancelled.failure_reason,
            observer_permission=getattr(observer_probe, "permission_ok", None),
            observer_sessions=getattr(observer_probe, "sessions", None),
            observer_probe_error=(observer_probe.get("error") if isinstance(observer_probe, dict) else None),
        )

        no_permission = make(
            account="lab_prod", observer="lab_prod", tag="t2q-lab-no-observer-permission"
        )
        no_permission.start("lab-no-observer-permission")
        no_permission.dispatch(
            "SELECT Status FROM dbo.SafeStatus WHERE Id=1;",
            {"timeout": 10, "max_rows": 1, "max_bytes": 4096},
        )
        no_permission_result = _poll(no_permission)
        lab.record("normal exit does not require DMV permission",
                   no_permission_result is True and _close(no_permission)
                   and no_permission.completion_basis == "normal_exit")
        no_permission.cancel()
        no_permission_closed = _close(no_permission)
        lab.record(
            "observer without DMV permission never confirms closure",
            no_permission_result is True and not no_permission_closed,
        )

        lab.observations.append(
            "Production-shaped transport passed against the disposable SQL Server: "
            "reviewed host tags, approved stdin batches, physical output caps, "
            "owned-process cancellation, and fail-closed DMV observer permission."
        )
    finally:
        for backend in backends:
            try:
                if backend.process is not None and backend.process.poll() is None:
                    backend.cancel()
            except Exception:
                # verify.py owns fixture cleanup; do not leak a client process
                # when an earlier assertion aborts this check.
                pass


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--docker-forward":
    raise SystemExit(_docker_forwarder(json.loads(sys.argv[2])))
