"""Exercise the public DML executor with real commits, rollbacks and lost replies."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
import time


def verify_bounded(lab):
    def update_range(first, last, label):
        ids = ",".join(map(str, range(first, last+1)))
        return f"UPDATE dbo.BulkFixtureRow SET Label=N'{label}' WHERE Id IN ({ids});"

    first = lab.bounded("DEV2-CUMULATIVE", update_range(1, 60, "budget"))
    lab.record("task budget: first 60 rows committed", first.get("rows") == 60 and first.get("remaining_rows") == 40, result=first)
    over = lab.bounded("DEV2-CUMULATIVE", update_range(61, 110, "overflow"))
    lab.record("task budget: subsequent 50 rows rolled back", over["status"] == "rolled_back" and
               51001 in over.get("sql_error_codes", []), result=over)
    lab.check_sql("task budget: overflow left no changes", "lab_dev", "DevFixture",
                  "SELECT COUNT(*) FROM dbo.BulkFixtureRow WHERE Label=N'overflow';", expected=0)
    exact = lab.bounded("DEV2-CUMULATIVE", update_range(61, 100, "budget"))
    lab.record("task budget: exactly 100 cumulative rows", exact.get("rows") == 40 and exact.get("remaining_rows") == 0, result=exact)
    exhausted = lab.bounded("DEV2-CUMULATIVE", update_range(101, 101, "forbidden"))
    lab.record("task budget: further execution blocked", exhausted["status"] == "blocked", result=exhausted)
    lab.check_sql("task budget: exactly 100 rows persisted", "lab_dev", "DevFixture",
                  "SELECT COUNT(*) FROM dbo.BulkFixtureRow WHERE Label=N'budget';", expected=100)

    def slow_transport(batch, timeout):
        # Inject server delay after DML and before COMMIT to emulate a slow
        # statement while preserving the executor's transaction/receipt protocol.
        batch = batch.replace("DECLARE @affected int=@@ROWCOUNT;",
                              "DECLARE @affected int=@@ROWCOUNT; WAITFOR DELAY '00:00:20';")
        completed = lab.query("lab_dev", "DevFixture", batch, timeout)
        lab.report.setdefault("bounded_timeout_diagnostics", []).append({
            "exit_code": completed.returncode, "output": lab.clean(completed.stdout + completed.stderr)})
        return completed

    timed = lab.bounded("DEV2-TIMEOUT", "UPDATE dbo.FixtureRow SET Label=N'should-rollback' WHERE Id=1;", slow_transport)
    lab.record("executor treats timeout as failure", not timed["ok"] and timed["error"] == "timeout" and
               timed["status"] == "unknown", result=timed)
    lab.record("executor confirms timed-out session lock released", timed.get("session_cleanup_confirmed") is True)
    lab.check_sql("timed-out DML rolled back", "lab_dev", "DevFixture",
                  "SELECT Label FROM dbo.FixtureRow WHERE Id=1;", expected="baseline")
    replay = lab.bounded("DEV2-TIMEOUT", "UPDATE dbo.FixtureRow SET Label=N'retry' WHERE Id=1;")
    lab.record("uncertain timeout blocks replay", replay["status"] == "blocked", result=replay)

    def lost_reply(batch, timeout):
        completed = lab.query("lab_dev", "DevFixture", batch, timeout)
        lab.require(completed, "commit before dropped reply")
        return subprocess.CompletedProcess([], 0, "", "")

    lost = lab.bounded("DEV2-LOST-REPLY", "UPDATE dbo.FixtureRow SET Label=N'committed-no-reply' WHERE Id=2;", lost_reply)
    lab.record("lost commit receipt is not success", not lost["ok"] and lost["status"] == "unknown", result=lost)
    lab.check_sql("lost reply fixture actually committed", "lab_dev", "DevFixture",
                  "SELECT Label FROM dbo.FixtureRow WHERE Id=2;", expected="committed-no-reply")
    replay = lab.bounded("DEV2-LOST-REPLY", "DELETE FROM dbo.FixtureRow WHERE Id=2;")
    lab.record("lost commit receipt blocks replay", replay["status"] == "blocked", result=replay)

    def postcommit_error(batch, timeout):
        batch = batch.replace("COMMIT TRANSACTION;", "COMMIT TRANSACTION; THROW 51010, 'Postcommit fault', 1;")
        return lab.query("lab_dev", "DevFixture", batch, timeout)
    postcommit = lab.bounded("DEV2-POSTCOMMIT", "UPDATE dbo.FixtureRow SET Label=N'postcommit-error' WHERE Id=2;", postcommit_error)
    lab.record("postcommit error is uncertain, not rolled back", postcommit["status"] == "unknown", result=postcommit)
    lab.check_sql("postcommit fault actually committed", "lab_dev", "DevFixture",
                  "SELECT Label FROM dbo.FixtureRow WHERE Id=2;", expected="postcommit-error")
    replay = lab.bounded("DEV2-POSTCOMMIT", "DELETE FROM dbo.FixtureRow WHERE Id=2;")
    lab.record("postcommit error blocks replay", replay["status"] == "blocked", result=replay)

    lab.require(lab.query("sa", "DevFixture", """
CREATE TABLE dbo.TriggerFixture (Id int PRIMARY KEY, Label nvarchar(60));
INSERT INTO dbo.TriggerFixture VALUES (1,N'baseline');
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.TriggerFixture TO lab_dev;
GO
CREATE TRIGGER dbo.TriggerSideEffect ON dbo.TriggerFixture AFTER UPDATE AS
UPDATE dbo.FixtureRow SET Label=N'trigger-side-effect' WHERE Id=1;
"""), "trigger fixture")
    triggered = lab.bounded("DEV2-TRIGGER", "UPDATE dbo.TriggerFixture SET Label=N'changed' WHERE Id=1;")
    lab.record("enabled trigger rejected before DML", triggered["status"] == "rolled_back" and
               51007 in triggered.get("sql_error_codes", []), result=triggered)
    lab.check_sql("trigger side effect did not execute", "lab_dev", "DevFixture",
                  "SELECT Label FROM dbo.FixtureRow WHERE Id=1;", expected="baseline")
    lab.require(lab.query("sa", "DevFixture", """
CREATE TABLE dbo.RaceFixture (Id int PRIMARY KEY, Label nvarchar(60));
INSERT INTO dbo.RaceFixture VALUES (1,N'baseline');
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.RaceFixture TO lab_dev;
"""), "metadata race fixture")
    def paused_transport(batch, timeout):
        batch = batch.replace("SET @object_id=OBJECT_ID", "WAITFOR DELAY '00:00:04'; SET @object_id=OBJECT_ID")
        return lab.query("lab_dev", "DevFixture", batch, timeout)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(lab.bounded, "DEV2-DDL-RACE",
                              "UPDATE dbo.RaceFixture SET Label=N'safe' WHERE Id=1;", paused_transport)
        deadline = time.monotonic() + 3
        locked = False
        while time.monotonic() < deadline:
            locked = int(lab.scalar("""SELECT COUNT(*) FROM sys.dm_tran_locks l
JOIN sys.dm_exec_sessions s ON l.request_session_id=s.session_id
WHERE s.login_name=N'lab_dev' AND l.resource_database_id=DB_ID(N'DevFixture')
AND l.resource_type='OBJECT' AND l.request_mode='X' AND l.request_status='GRANT'
AND l.resource_associated_entity_id=OBJECT_ID(N'DevFixture.dbo.RaceFixture');""")) > 0
            if locked:
                break
            time.sleep(0.05)
        lab.record("executor holds table lock before metadata check", locked,
                   execution_result=pending.result(timeout=10) if not locked else None)
        lab.check_sql("concurrent trigger DDL blocked before DML", "sa", "DevFixture", """
SET LOCK_TIMEOUT 1000;
GO
CREATE TRIGGER dbo.RaceSideEffect ON dbo.RaceFixture AFTER UPDATE AS
UPDATE dbo.FixtureRow SET Label=N'race-side-effect' WHERE Id=1;
""", errors=[1222], query_timeout=3)
        raced = pending.result(timeout=10)
        lab.record("DML commits after concurrent DDL was rejected", raced.get("ok") is True, result=raced)
    lab.check_sql("concurrent DDL caused no side effect", "lab_dev", "DevFixture",
                  "SELECT Label FROM dbo.FixtureRow WHERE Id=1;", expected="baseline")
    lab.observations.append("The DML executor rolled back excess rows, enforced a cumulative 100-row local task budget, and blocked replay after timeout or a lost commit acknowledgement. Local state is not a tamper-proof production approval service.")
