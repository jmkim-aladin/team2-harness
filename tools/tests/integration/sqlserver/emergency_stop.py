"""DB emergency-stop primitives in the disposable lab, not a production controller.

The independent operator is simulated by lab sa. Never grant these permissions
to the reader. Fixed logins belong only to verify.py's isolated container.
"""
import subprocess
import time


def _start(lab, user):
    process = subprocess.Popen(lab.sql_args(user, "ProdFixture", 45),
                               env=lab.sql_env(user), stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    process.stdin.write("SET NOCOUNT ON; WAITFOR DELAY '00:00:40'; SELECT 1;\nGO\n")
    process.stdin.close()
    process.stdin = None
    return process


def _sessions(lab, user):
    # The login is a fixture constant, not an operator-supplied filter.
    if user not in {"lab_cancel", "lab_prod"}:
        raise ValueError("Not a fixture login")
    output = lab.scalar(f"""SELECT CONCAT(s.session_id, '|', CONVERT(varchar(36), c.connection_id))
FROM sys.dm_exec_sessions s JOIN sys.dm_exec_connections c ON s.session_id=c.session_id
JOIN sys.dm_exec_requests r ON r.session_id=s.session_id
WHERE s.login_name=N'{user}' AND r.database_id=DB_ID(N'ProdFixture')
AND r.command=N'WAITFOR' AND r.wait_type=N'WAITFOR';""")
    return [line.split("|") for line in output.splitlines() if line.strip()]


def _expect_disabled(lab, name):
    result = lab.query("lab_cancel", "ProdFixture", "SELECT 1;")
    diagnostic = lab.clean(result.stdout + result.stderr)
    # Login errors are ODBC diagnostics, not T-SQL "Msg 18470" output.
    lab.record(name, result.returncode != 0 and
               "Login failed for user 'lab_cancel'. Reason: The account is disabled." in diagnostic,
               exit_code=result.returncode, diagnostic=diagnostic.strip())


def verify_emergency_stop(lab):
    processes = []
    try:
        # Successful access first distinguishes stop rejection from a bad password.
        lab.check_sql("emergency reader can connect before stop", "lab_cancel", "ProdFixture",
                      "SELECT Status FROM dbo.SafeStatus WHERE Id=1;", expected="active")
        processes.extend([_start(lab, "lab_cancel"), _start(lab, "lab_cancel"), _start(lab, "lab_prod")])
        deadline = time.monotonic() + 8
        targets, unrelated = [], []
        while time.monotonic() < deadline:
            targets, unrelated = _sessions(lab, "lab_cancel"), _sessions(lab, "lab_prod")
            if len(targets) == 2 and len(unrelated) == 1:
                break
            time.sleep(0.1)
        lab.record("emergency stop observes two active target sessions", len(targets) == 2,
                   sessions=[int(sid) for sid, _ in targets])
        lab.record("emergency stop observes unrelated active session", len(unrelated) == 1)

        started = time.monotonic()
        lab.require(lab.query("sa", "master", "ALTER LOGIN lab_cancel DISABLE;"), "disable fixture login")
        _expect_disabled(lab, "emergency stop blocks new login")
        lab.record("disabling login alone leaves active sessions", len(_sessions(lab, "lab_cancel")) == 2)
        # Reader cannot re-enable the login through the same instance.
        lab.check_sql("reader cannot undo emergency stop", "lab_prod", "master",
                      "ALTER LOGIN lab_cancel ENABLE;", errors=[15151, 15247])

        for sid, connection in targets:
            sid = int(sid)
            # Recheck connection identity immediately before the operator KILL.
            # This lab holds WAITFOR sessions open; it is NOT a production-safe
            # SPID-reuse algorithm. Production uses owned connection handles and
            # a separately reviewed DBA escalation, as required by the runbook.
            current = lab.scalar(f"""SELECT COUNT(*) FROM sys.dm_exec_sessions s
JOIN sys.dm_exec_connections c ON c.session_id=s.session_id
WHERE s.session_id={sid} AND s.login_name=N'lab_cancel'
AND c.connection_id=CONVERT(uniqueidentifier,N'{connection}');""")
            lab.record("emergency stop identifies target connection " + str(sid), current == "1")
            lab.require(lab.query("sa", "master", f"KILL {sid};"), "kill fixture session")

        deadline = time.monotonic() + 5
        active = "unknown"
        while time.monotonic() < deadline:
            active = lab.scalar("SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE login_name=N'lab_cancel';")
            if active == "0":
                break
            time.sleep(0.1)
        lab.record("emergency stop confirms all target sessions gone", active == "0",
                   duration_seconds=round(time.monotonic()-started, 3))
        for process in processes[:2]:
            process.communicate(timeout=5)
        lab.record("emergency stop leaves unrelated query running", _sessions(lab, "lab_prod") == unrelated)
        lab.check_sql("emergency stop leaves unrelated login usable", "lab_prod", "ProdFixture",
                      "SELECT Status FROM dbo.SafeStatus WHERE Id=1;", expected="active")
        # State is persisted by SQL Server, not held in a runner variable.
        lab.record("emergency stop remains disabled on fresh control connection", lab.scalar(
            "SELECT is_disabled FROM sys.server_principals WHERE name=N'lab_cancel';") == "1")
        _expect_disabled(lab, "emergency stop still rejects subsequent login")
        lab.observations.append("Emergency-stop DB primitives passed: disable a dedicated login, terminate two active sessions, preserve an unrelated session, and keep new logins blocked. The operator was simulated by lab sa. No production stop UI/API, distributed admission fence, least-privilege control service, or restart/failure-path guarantee was implemented by this fixture.")
    finally:
        # Remove only client processes started here; verify.py then removes the
        # owned container, including any server sessions after an early failure.
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=3)
