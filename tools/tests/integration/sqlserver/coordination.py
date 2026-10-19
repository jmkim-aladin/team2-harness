"""Exercise the central coordinator with isolated sqlcmd sessions.

The fixture-only cancellation adapter uses sa/KILL for known held sessions.
It is not a deployable production adapter (SPID reuse/privilege isolation).
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

from db_query_control import Store, Supervisor


class Query:
    def __init__(self, lab, *, hide_confirmation=False):
        self.lab = lab
        self.hide_confirmation = hide_confirmation
        self.process = None
        self.identity = None
        self.host = None
        self.dispatched = threading.Event()
        self.cancelled = False
        self.output = None

    def sessions(self):
        if self.host is None:
            return []
        output = self.lab.scalar(f"""SELECT CONCAT(s.session_id,'|',CONVERT(varchar(36),c.connection_id))
FROM sys.dm_exec_sessions s JOIN sys.dm_exec_connections c ON c.session_id=s.session_id
WHERE s.login_name=N'lab_prod' AND s.host_name=N'{self.host}';""")
        return [line.split("|") for line in output.splitlines() if line.strip()]

    def start(self, run):
        self.host = "t2-" + run
        self.process = subprocess.Popen(self.lab.sql_args("lab_prod", "ProdFixture", 35)+["-H", self.host],
                                        env=self.lab.sql_env("lab_prod"), stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Connection handshake only; user SQL is sent later, behind the gate.
        self.process.stdin.write("SET NOCOUNT ON; SELECT 1;\nGO\n")
        self.process.stdin.flush()
        deadline = time.monotonic()+3
        while time.monotonic() < deadline:
            sessions = self.sessions()
            if len(sessions) == 1:
                sid, connection = sessions[0]
                self.identity = dict(session=int(sid), connection=connection)
                return self.identity
            time.sleep(0.05)
        raise RuntimeError("Fixture connection handshake not observed")

    def dispatch(self, sql, limits):
        # Test SQL/result sizes are synthetic and fixed. Production streaming
        # output caps belong in the real transport, not this fixture adapter.
        self.process.stdin.write(sql + "\nPRINT 'TEAM2_QUERY_COMPLETE';\nGO\n")
        self.process.stdin.close()
        self.process.stdin = None
        self.dispatched.set()

    def poll(self):
        if self.process.poll() is None:
            return None
        if self.output is None:
            self.output = self.process.communicate(timeout=2)
        stdout, stderr = self.output
        return self.process.returncode == 0 and not stderr and stdout.strip().endswith("TEAM2_QUERY_COMPLETE")

    def cancel(self):
        self.cancelled = True
        if self.process is None:
            return
        # Fixed fixture identity rechecked before KILL. This is NOT a production
        # SPID-reuse solution; only the owned Docker lab can use this adapter.
        for sid, connection in self.sessions():
            if self.identity is not None and (int(sid) != self.identity["session"] or connection != self.identity["connection"]):
                raise RuntimeError("Fixture connection identity changed")
            self.lab.require(self.lab.query("sa", "master", f"KILL {int(sid)};"), "fixture cancellation")
        if self.process.stdin is not None:
            self.process.stdin.close()
            self.process.stdin = None
        self.output = self.process.communicate(timeout=3)

    def really_closed(self):
        return self.identity is not None and self.process.poll() is not None and not self.sessions()

    def closed(self):
        return False if self.hide_confirmation else self.really_closed()


def verify_coordination(lab):
    path = Path(lab.budget_directory.name)/"query-control.sqlite3"
    Store.initialize(path)
    store = Store(path)
    control = Supervisor(store, cleanup_timeout=0.5)
    backends = []

    def all_closed():
        return lab.scalar("SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE login_name=N'lab_prod';") == "0"

    def request(owner, sql, timeout=30, target="ProdFixture"):
        item = store.prepare(owner=owner, target=target, sql=sql, timeout=timeout)
        store.approve(item["id"], item["digest"], operator="fixture-human")
        return dict(owner=owner, target=target, sql=sql, timeout=timeout, approval_id=item["id"])

    def backend(**kwargs):
        instance = Query(lab, **kwargs)
        backends.append(instance)
        return instance

    slow = "WAITFOR DELAY '00:00:20'; SELECT Status FROM dbo.SafeStatus WHERE Id=1;"
    fast = "SELECT Status FROM dbo.SafeStatus WHERE Id=1;"
    try:
        lab.record("coordinator starts halted", bool(store.status()["halted"]))
        lab.record("operator explicitly arms coordinator after server check", control.resume(all_closed))
        pending = store.prepare(owner="agent-a", target="ProdFixture", sql=fast)
        unopened = backend()
        denied = control.execute(owner="agent-a", target="ProdFixture", sql=fast,
                                 approval_id=pending["id"], backend=unopened)
        lab.record("unapproved SQL never opens DB connection", denied["status"] == "approval_required" and unopened.process is None)

        first, second = request("agent-a", slow), request("agent-b", fast, target="other-prod")
        active = backend()
        with ThreadPoolExecutor(max_workers=1) as pool:
            running = pool.submit(control.execute, **first, backend=active)
            lab.record("approved first agent dispatches", active.dispatched.wait(5))
            other_backend = backend()
            busy = Supervisor(Store(path)).execute(**second, backend=other_backend)
            lab.record("other agent and DB share the global slot", busy["status"] == "busy" and other_backend.process is None)
            # Actual separate OS process: human stop CLI, no agent cooperation.
            stopped = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[3]/"db_query_control.py"),
                                      "--state", str(path), "stop"], text=True, capture_output=True, timeout=3)
            lab.record("independent stop CLI persists halt", stopped.returncode == 0 and json.loads(stopped.stdout)["halted"] == 1)
            result = running.result(timeout=10)
        lab.record("manual stop cancels and confirms SQL Server session gone",
                   result["status"] == "stopped" and result["session_closed"] and active.cancelled and active.really_closed(), result=result)
        reopened = Supervisor(Store(path))
        lab.record("new supervisor preserves halt", reopened.execute(**second, backend=backend())["status"] == "halted")
        lab.record("operator resumes only after confirmed close", reopened.resume(all_closed))
        lab.record("old approval invalid after stop and resume", reopened.execute(**second, backend=backend())["status"] == "approval_required")

        normal = reopened.execute(**request("agent-b", fast), backend=backend())
        lab.record("fresh approval completes with confirmed close", normal["ok"] and normal["session_closed"], result=normal)
        failed_backend = backend()
        failed = reopened.execute(**request("agent-b", "SELECT 1/0;"), backend=failed_backend)
        lab.record("SQL error cancels and latches global stop", failed["status"] == "stopped" and
                   failed_backend.cancelled and store.status()["halted"] == 1, result=failed)
        lab.record("error cleanup confirmed before slot release", failed["session_closed"] and store.status()["active"] is None)
        lab.record("operator resumes after SQL error", reopened.resume(all_closed))

        timed_backend = backend()
        timed = reopened.execute(**request("agent-c", slow, timeout=1), backend=timed_backend)
        lab.record("approved timeout cancels and confirms server close", timed["status"] == "stopped" and
                   timed["reason"] == "timeout" and timed["session_closed"] and timed_backend.cancelled, result=timed)
        lab.record("operator resumes after timeout", reopened.resume(all_closed))
        hidden = backend(hide_confirmation=True)
        uncertain = reopened.execute(**request("agent-d", "SELECT 1/0;"), backend=hidden)
        lab.record("missing close evidence retains active slot", uncertain["status"] == "unconfirmed" and
                   Store(path).status()["active"] == uncertain["run_id"], result=uncertain)
        lab.record("resume refused while cleanup unconfirmed", not reopened.resume(all_closed))
        lab.record("fresh server evidence reconciles but remains halted", reopened.reconcile(all_closed) and store.status()["halted"] == 1)
        lab.record("reconciled state still requires explicit resume", reopened.execute(**second, backend=backend())["status"] == "halted")
        lab.observations.append("Central coordinator core passed real sqlcmd/SQL Server tests for per-execution approval, cross-agent admission, independent CLI stop, error/timeout cancellation, server close confirmation, persisted halt and explicit operator recovery. This is one trusted shared SQLite store, not deployed multi-host authentication, a production cancellation adapter, or a complete production gateway.")
    finally:
        for instance in backends:
            if instance.process is not None and instance.process.poll() is None:
                try:
                    instance.cancel()
                except Exception:
                    instance.process.kill()
                    instance.process.communicate(timeout=3)
