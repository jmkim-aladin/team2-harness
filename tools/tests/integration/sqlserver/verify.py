#!/usr/bin/env python3
"""Disposable SQL Server permission tests. Never connects to an existing DB.

Requires Docker and a SQL Server 2022 image. Generates synthetic data/passwords,
publishes no ports, mounts no files, and removes only its own container on exit.
"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("guard", ROOT / "tools/db_sqlcmd_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
sys.path.insert(0, str(ROOT / "tools"))
from db_execute import execute
from isolation import verify_isolation
from emergency_stop import verify_emergency_stop
from coordination import verify_coordination
from production_transport import verify_production_transport
DEFAULT_IMAGE = "mcr.microsoft.com/mssql/server:2022-CU24-GDR1-ubuntu-22.04"
SQLCMD = "/opt/mssql-tools18/bin/sqlcmd"


class Lab:
    def __init__(self, image):
        self.name = "team2-db-policy-test-" + uuid.uuid4().hex[:12]
        self.image = image
        self.passwords = {user: "Aa1!" + secrets.token_hex(20)
                          for user in ("sa", "lab_dev", "lab_prod", "lab_staging", "lab_cancel")}
        self.checks = []
        self.observations = []
        self.lock_process = None
        self.cancel_process = None
        self.owner = uuid.uuid4().hex
        self.budget_directory = tempfile.TemporaryDirectory(prefix="team2-db-budget-")
        self.budget_path = Path(self.budget_directory.name) / "budget.sqlite3"
        self.report = {"started_at": datetime.now(timezone.utc).isoformat(),
                       "host_arch": platform.machine(), "requested_image": image,
                       "checks": self.checks, "observations": self.observations,
                       "production_ready": False,
                       "scope": "isolated SQL Server permissions + local guard; not production gateway"}

    def run(self, args, *, env=None, sql=None, timeout=30):
        return subprocess.run(args, env=env, input=sql, text=True, capture_output=True, timeout=timeout)

    def clean(self, text):
        for password in self.passwords.values():
            text = text.replace(password, "<redacted>")
        return text

    def require(self, result, context):
        if result.returncode:
            raise RuntimeError(context + ": " + self.clean(result.stdout + result.stderr)[-2000:])
        return result.stdout.strip()

    def sql_args(self, user, database, query_timeout=10):
        return ["docker", "exec", "-i", "--env", "SQLCMDPASSWORD", self.name, SQLCMD,
                "-S", "tcp:127.0.0.1,1433", "-U", user, "-d", database, "-C", "-b", "-V", "11",
                "-l", "3", "-t", str(query_timeout), "-h", "-1", "-W"]

    def sql_env(self, user):
        return {**os.environ, "SQLCMDPASSWORD": self.passwords[user]}

    def query(self, user, database, sql, query_timeout=10):
        return self.run(self.sql_args(user, database, query_timeout), env=self.sql_env(user),
                        sql="SET NOCOUNT ON;\n" + sql + "\nGO\n", timeout=query_timeout + 15)

    def scalar(self, sql, database="master"):
        return self.require(self.query("sa", database, sql), "observer query").strip()

    def record(self, name, passed, **evidence):
        self.checks.append({"name": name, "passed": passed, **evidence})
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
        if not passed:
            raise RuntimeError(f"Check failed: {name}")

    def check_sql(self, name, user, db, sql, *, errors=None, expected=None, query_timeout=10):
        start = time.monotonic()
        result = self.query(user, db, sql, query_timeout)
        output = self.clean(result.stdout + result.stderr)
        codes = sorted(set(int(code) for code in re.findall(r"Msg\s+(\d+)", output)))
        passed = (result.returncode == 0 if errors is None else
                  result.returncode != 0 and bool(set(codes) & set(errors)))
        if expected is not None:
            passed = passed and result.stdout.strip() == str(expected)
        self.record(name, passed, sql_error_codes=codes, exit_code=result.returncode,
                    duration_seconds=round(time.monotonic() - start, 3),
                    **({"failure_diagnostic": output[-2000:]} if not passed else {}))
        return result

    def guard_dml(self, name, sql, expected_count):
        # Only the guard receives the registered dev hostname. Execution is bound
        # to this disposable container's localhost; no real hostname is resolved.
        candidate = f"sqlcmd -S {guard.DEV_HOST} -d WebCatalog -Q {shlex.quote(sql)}"
        self.record(name + ": raw sqlcmd blocked", "db_execute.py" in (guard.command_reason(candidate) or ""))
        result = self.bounded("DEV2-SMOKE", sql)
        self.record(name + ": bounded DB commit", result["ok"] and result.get("rows") == expected_count,
                    result=result)

    def bounded(self, task, sql, transport=None):
        return execute(task=task, database="WebCatalog", sql=sql,
                       transport=transport or (lambda batch, timeout: self.query("lab_dev", "DevFixture", batch, timeout)),
                       ledger=self.budget_path)

    def start(self):
        # Pin the locally resolved image ID so tags cannot change between checks.
        image = self.run(["docker", "image", "inspect", self.image, "--format", "{{json .}}"])
        if image.returncode:
            print("Pulling SQL Server image...", flush=True)
            self.require(self.run(["docker", "pull", "--platform", "linux/amd64", self.image],
                                  timeout=600), "image pull")
            image = self.run(["docker", "image", "inspect", self.image, "--format", "{{json .}}"])
        metadata = json.loads(self.require(image, "image inspect"))
        self.report.update(image_id=metadata["Id"], image_digests=metadata.get("RepoDigests", []),
                           image_arch=metadata["Architecture"])
        if metadata["Architecture"] != "amd64":
            raise RuntimeError("This fixture expects the SQL Server linux/amd64 image")
        env = {**os.environ, "MSSQL_SA_PASSWORD": self.passwords["sa"]}
        self.require(self.run(["docker", "run", "-d", "--name", self.name,
                               "--label", "team2.fixture=db-access", "--label", "team2.fixture.owner=" + self.owner,
                               "--platform", "linux/amd64",
                               "--network", "none", "--memory", "2560m", "--cpus", "2",
                               "--env", "ACCEPT_EULA=Y", "--env", "MSSQL_PID=Developer",
                               "--env", "MSSQL_MEMORY_LIMIT_MB=2048",
                               "--env", "MSSQL_SA_PASSWORD", metadata["Id"]], env=env), "container start")
        self.require(self.run(["docker", "exec", self.name, "test", "-x", SQLCMD]), "sqlcmd binary availability")
        deadline = time.monotonic() + 180
        attempts = 0
        while time.monotonic() < deadline:
            ready = self.query("sa", "master", "SELECT 1;", query_timeout=3)
            if ready.returncode == 0 and ready.stdout.strip() == "1":
                self.report["server_version"] = self.scalar("SELECT @@VERSION;")
                print("SQL Server ready", flush=True)
                return
            state = self.run(["docker", "inspect", self.name, "--format", "{{.State.Running}}"])
            if state.stdout.strip() != "true":
                raise RuntimeError("SQL Server exited during startup: " + self.clean(self.run(
                    ["docker", "logs", "--tail", "30", self.name]).stdout)[-2000:])
            attempts += 1
            if attempts == 1 or attempts % 10 == 0:
                print("Waiting for SQL Server: " + self.clean(ready.stdout + ready.stderr)[-600:].strip(), flush=True)
            time.sleep(2)
        raise RuntimeError("SQL Server startup deadline exceeded: " + self.clean(ready.stdout + ready.stderr)[-1000:])

    def setup(self):
        statements = ["CREATE DATABASE DevFixture;", "CREATE DATABASE ProdFixture;",
                      "CREATE DATABASE StagingFixture;"]
        statements += [f"CREATE LOGIN {user} WITH PASSWORD = '{password}', CHECK_POLICY=OFF;"
                       for user, password in self.passwords.items() if user != "sa"]
        self.require(self.query("sa", "master", "\nGO\n".join(statements)), "database/logins fixture")
        self.require(self.query("sa", "DevFixture", """
CREATE TABLE dbo.FixtureRow (Id int NOT NULL PRIMARY KEY, Label nvarchar(60) NOT NULL, IsTest bit NOT NULL);
INSERT INTO dbo.FixtureRow VALUES (1, N'baseline', 1), (2, N'baseline', 1);
CREATE TABLE dbo.BulkFixtureRow (Id int NOT NULL PRIMARY KEY, Label nvarchar(60) NOT NULL, IsTest bit NOT NULL);
INSERT INTO dbo.BulkFixtureRow SELECT TOP (150) ROW_NUMBER() OVER (ORDER BY object_id), N'baseline', 1 FROM sys.all_objects;
CREATE USER lab_dev FOR LOGIN lab_dev;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.FixtureRow TO lab_dev;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.BulkFixtureRow TO lab_dev;
GRANT VIEW DEFINITION TO lab_dev;
GO
CREATE PROCEDURE dbo.ForbiddenWrite AS UPDATE dbo.FixtureRow SET Label=N'procedure' WHERE Id=1;
"""), "dev fixture")
        self.require(self.query("sa", "ProdFixture", """
CREATE TABLE dbo.RawCustomer (Id int NOT NULL PRIMARY KEY, Status nvarchar(20) NOT NULL, Email nvarchar(80) NOT NULL);
INSERT INTO dbo.RawCustomer VALUES (1, N'active', N'synthetic@example.invalid');
GO
CREATE VIEW dbo.SafeStatus AS SELECT Id, Status FROM dbo.RawCustomer;
GO
CREATE PROCEDURE dbo.ForbiddenWrite AS UPDATE dbo.RawCustomer SET Status=N'changed' WHERE Id=1;
GO
CREATE USER lab_prod FOR LOGIN lab_prod;
CREATE USER lab_cancel FOR LOGIN lab_cancel;
GRANT SELECT ON dbo.SafeStatus TO lab_prod;
GRANT SELECT ON dbo.SafeStatus TO lab_cancel;
"""), "prod fixture")
        self.require(self.query("sa", "StagingFixture", """
CREATE TABLE dbo.FixtureRow (Id int NOT NULL PRIMARY KEY, Label nvarchar(60) NOT NULL);
INSERT INTO dbo.FixtureRow VALUES (1, N'baseline');
CREATE USER lab_staging FOR LOGIN lab_staging;
GRANT SELECT ON dbo.FixtureRow TO lab_staging;
"""), "staging fixture")

    def permissions(self):
        self.check_sql("dev SELECT", "lab_dev", "DevFixture", "SELECT COUNT(*) FROM dbo.FixtureRow;", expected=2)
        self.guard_dml("dev INSERT", "INSERT INTO dbo.FixtureRow (Id, Label, IsTest) VALUES (3, N'insert', 1);", 1)
        self.guard_dml("dev UPDATE", "UPDATE dbo.FixtureRow SET Label=N'updated' WHERE Id=3;", 1)
        self.check_sql("dev UPDATE persisted", "lab_dev", "DevFixture", "SELECT Label FROM dbo.FixtureRow WHERE Id=3;", expected="updated")
        self.guard_dml("dev DELETE", "DELETE FROM dbo.FixtureRow WHERE Id=3;", 1)
        self.check_sql("dev DELETE persisted", "lab_dev", "DevFixture", "SELECT COUNT(*) FROM dbo.FixtureRow WHERE Id=3;", expected=0)
        for name, sql, codes in [
            ("CREATE denied", "CREATE TABLE dbo.Forbidden (Id int);", [262]),
            ("ALTER denied", "ALTER TABLE dbo.FixtureRow ADD Extra int;", [229, 1088, 15151]),
            ("DROP denied", "DROP TABLE dbo.FixtureRow;", [229, 3701]),
            ("TRUNCATE denied", "TRUNCATE TABLE dbo.FixtureRow;", [229, 1088]),
            ("EXEC denied", "EXEC dbo.ForbiddenWrite;", [229]),
        ]:
            self.check_sql("dev " + name, "lab_dev", "DevFixture", sql, errors=codes)
        # GRANT may report only a warning when nothing was granted. Verify the
        # effective permission and subsequent ALTER, not merely CLI exit status.
        attempted = self.query("lab_dev", "DevFixture", "GRANT ALTER ON dbo.FixtureRow TO lab_dev;")
        self.report["self_grant_attempt"] = {"exit_code": attempted.returncode,
                                             "diagnostic": self.clean(attempted.stdout + attempted.stderr).strip()}
        self.check_sql("dev self-grant did not gain ALTER", "lab_dev", "DevFixture",
                       "SELECT HAS_PERMS_BY_NAME('dbo.FixtureRow', 'OBJECT', 'ALTER');", expected=0)
        self.check_sql("dev ALTER still denied after self-grant", "lab_dev", "DevFixture",
                       "ALTER TABLE dbo.FixtureRow ADD Extra int;", errors=[229, 1088, 15151])
        self.check_sql("dev cross-DB access denied", "lab_dev", "DevFixture",
                       "SELECT * FROM ProdFixture.dbo.RawCustomer;", errors=[916, 229])
        self.check_sql("dev metadata grant exposes procedure definition", "lab_dev", "DevFixture",
                       "SELECT CASE WHEN OBJECT_DEFINITION(OBJECT_ID('dbo.ForbiddenWrite')) IS NOT NULL THEN 1 ELSE 0 END;", expected=1)
        self.check_sql("staging SELECT", "lab_staging", "StagingFixture", "SELECT COUNT(*) FROM dbo.FixtureRow;", expected=1)
        for sql in ["INSERT INTO dbo.FixtureRow VALUES (2,N'no');",
                    "UPDATE dbo.FixtureRow SET Label=N'no' WHERE Id=1;",
                    "DELETE FROM dbo.FixtureRow WHERE Id=1;"]:
            self.check_sql("staging " + sql.split()[0] + " denied", "lab_staging", "StagingFixture", sql, errors=[229])
        self.check_sql("prod safe view SELECT", "lab_prod", "ProdFixture", "SELECT Status FROM dbo.SafeStatus WHERE Id=1;", expected="active")
        self.check_sql("prod raw table denied", "lab_prod", "ProdFixture", "SELECT Email FROM dbo.RawCustomer;", errors=[229])
        self.check_sql("prod sensitive column absent from view", "lab_prod", "ProdFixture", "SELECT Email FROM dbo.SafeStatus;", errors=[207])
        for sql in ["INSERT INTO dbo.SafeStatus (Id,Status) VALUES (2,N'no');",
                    "UPDATE dbo.SafeStatus SET Status=N'no' WHERE Id=1;",
                    "DELETE FROM dbo.SafeStatus WHERE Id=1;", "EXEC dbo.ForbiddenWrite;"]:
            self.check_sql("prod " + sql.split()[0] + " denied", "lab_prod", "ProdFixture", sql, errors=[229])
        self.check_sql("prod CREATE denied", "lab_prod", "ProdFixture", "CREATE TABLE dbo.Forbidden (Id int);", errors=[262])
        for name, sql, codes in [
            ("CREATE PROCEDURE", "CREATE PROCEDURE dbo.ForbiddenNew AS SELECT 1;", [262]),
            ("ALTER PROCEDURE", "ALTER PROCEDURE dbo.ForbiddenWrite AS SELECT 1;", [229, 15151, 3701]),
            ("CREATE OR ALTER PROCEDURE", "CREATE OR ALTER PROCEDURE dbo.ForbiddenWrite AS SELECT 1;", [229, 15151, 3701, 262]),
            ("DROP PROCEDURE", "DROP PROCEDURE dbo.ForbiddenWrite;", [229, 3701]),
        ]:
            self.check_sql("prod " + name + " denied", "lab_prod", "ProdFixture", "GO\n" + sql, errors=codes)
        self.check_sql("prod procedure definition unchanged", "sa", "ProdFixture",
                       "SELECT CASE WHEN OBJECT_DEFINITION(OBJECT_ID('dbo.ForbiddenWrite')) LIKE '%UPDATE dbo.RawCustomer%' THEN 1 ELSE 0 END;", expected=1)
        self.check_sql("prod procedure definition not visible", "lab_prod", "ProdFixture",
                       "SELECT CASE WHEN OBJECT_DEFINITION(OBJECT_ID('dbo.ForbiddenWrite')) IS NULL THEN 1 ELSE 0 END;", expected=1)
        self.check_sql("prod source unchanged", "sa", "ProdFixture", "SELECT Status FROM dbo.RawCustomer WHERE Id=1;", expected="active")

    def limits(self):
        sql = "UPDATE dbo.BulkFixtureRow SET Label=N'changed' WHERE IsTest=1;"
        result = self.bounded("DEV2-OVER-LIMIT", sql)
        self.record("executor rolls back 150-row UPDATE", result["status"] == "rolled_back" and
                    51001 in result.get("sql_error_codes", []), result=result)
        self.check_sql("over-limit UPDATE leaves zero changed rows", "lab_dev", "DevFixture",
                       "SELECT COUNT(*) FROM dbo.BulkFixtureRow WHERE Label=N'changed';", expected=0)
        from bounded import verify_bounded
        verify_bounded(self)
        self.lock_process = subprocess.Popen(self.sql_args("lab_dev", "DevFixture", 25),
                                             env=self.sql_env("lab_dev"), stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.lock_process.stdin.write("BEGIN TRAN; UPDATE dbo.FixtureRow SET Label=N'locked' WHERE Id=1; WAITFOR DELAY '00:00:08'; ROLLBACK;\nGO\n")
        self.lock_process.stdin.close()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.scalar("SELECT COUNT(*) FROM sys.dm_exec_requests r JOIN sys.dm_exec_sessions s ON r.session_id=s.session_id WHERE s.login_name='lab_dev' AND r.wait_type='WAITFOR';") == "1":
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Lock holder did not reach WAITFOR")
        self.check_sql("lock wait cancelled by LOCK_TIMEOUT", "lab_dev", "DevFixture",
                       "SET LOCK_TIMEOUT 1000; SELECT Label FROM dbo.FixtureRow WHERE Id=1;", errors=[1222])
        self.lock_process.wait(timeout=12)
        self.record("lock holder completed", self.lock_process.returncode == 0)
        self.check_sql("lock released and transaction rolled back", "lab_dev", "DevFixture",
                       "SELECT Label FROM dbo.FixtureRow WHERE Id=1;", expected="baseline")
        self.check_sql("cancel account can connect", "lab_cancel", "ProdFixture", "SELECT Status FROM dbo.SafeStatus WHERE Id=1;", expected="active")
        cancel_started = time.monotonic()
        self.cancel_process = subprocess.Popen(self.sql_args("lab_cancel", "ProdFixture", 5),
                                               env=self.sql_env("lab_cancel"), stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.cancel_process.stdin.write("WAITFOR DELAY '00:00:20';\nGO\n")
        self.cancel_process.stdin.close()
        deadline = time.monotonic() + 4
        session_id = ""
        while time.monotonic() < deadline:
            session_id = self.scalar("SELECT r.session_id FROM sys.dm_exec_requests r JOIN sys.dm_exec_sessions s ON r.session_id=s.session_id WHERE s.login_name='lab_cancel' AND r.wait_type='WAITFOR';")
            if session_id.isdigit():
                break
            time.sleep(0.1)
        self.record("timeout query observed running on server", session_id.isdigit())
        self.cancel_process.wait(timeout=10)
        output = self.cancel_process.stdout.read() + self.cancel_process.stderr.read()
        elapsed = time.monotonic() - cancel_started
        self.report["timeout_client"] = {"exit_code": self.cancel_process.returncode,
                                          "duration_seconds": round(elapsed, 3),
                                          "diagnostic": self.clean(output).strip()}
        # This ODBC sqlcmd prints exactly 'Timeout expired' yet exits 0 with
        # these flags. Observe the running request, exact diagnostic, early
        # completion (<20s WAITFOR) and session removal independently of exit code.
        timeout_diagnostic = output.strip().lower() in {"timeout expired", "query timeout expired"}
        self.record("sqlcmd query timeout", timeout_diagnostic and 4 <= elapsed < 15,
                    exit_code=self.cancel_process.returncode)
        deadline = time.monotonic() + 5
        active = "unknown"
        while time.monotonic() < deadline:
            active = self.scalar(f"SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE session_id={int(session_id)} AND login_name='lab_cancel';")
            if active == "0":
                break
            time.sleep(0.2)
        self.record("timed-out server session ended", active == "0")
        if self.cancel_process.returncode == 0:
            self.observations.append("This ODBC sqlcmd returned exit code 0 with 'Timeout expired'; automation must inspect timeout diagnostics and server-side completion, not exit status alone.")
        self.observations.append("sqlcmd timeout/session cleanup passed for WAITFOR; production gateway cancellation, resource limits, concurrent budgets and audits remain untested.")

    def cleanup(self):
        # Unique name and no external volumes; never prune or stop other workloads.
        inspected = self.run(["docker", "container", "inspect", self.name, "--format", "{{json .Config.Labels}}"])
        if inspected.returncode == 0:
            labels = json.loads(inspected.stdout)
            if labels.get("team2.fixture.owner") != self.owner or labels.get("team2.fixture") != "db-access":
                raise RuntimeError("Container ownership mismatch; refusing cleanup: " + self.name)
            removed = self.run(["docker", "rm", "-f", "-v", self.name])
            self.report["container_removed"] = removed.returncode == 0
            if removed.returncode:
                self.report["cleanup_error"] = self.clean(removed.stderr)
                raise RuntimeError("Test container cleanup failed: " + self.name)
            print("Test container removed", flush=True)
        elif "no such" in inspected.stderr.lower():
            self.report["container_removed"] = True
        else:
            raise RuntimeError("Could not verify test container cleanup: " + self.name)
        for process in (self.lock_process, self.cancel_process):
            if process is not None:
                process.wait(timeout=10)
                process.stdout.close()
                process.stderr.close()
        self.budget_directory.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--transport-only", action="store_true", help="새 운영 transport만 격리 fixture에서 검사")
    args = parser.parse_args()
    def interrupted(*_):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    lab = Lab(args.image)
    exit_code = 1
    try:
        lab.start()
        lab.setup()
        if not args.transport_only:
            lab.permissions()
            lab.limits()
            verify_isolation(lab)
            verify_coordination(lab)
        verify_production_transport(lab)
        if not args.transport_only:
            verify_emergency_stop(lab)
        lab.report["passed"] = True
        exit_code = 0
    except (Exception, KeyboardInterrupt) as error:
        lab.report.update(passed=False, error=lab.clean(str(error)))
        print("FAIL " + lab.clean(str(error)), flush=True)
    finally:
        try:
            lab.cleanup()
        except Exception as error:
            lab.report.update(passed=False, cleanup_error=lab.clean(str(error)))
            exit_code = 1
        lab.report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(lab.report, ensure_ascii=False, indent=2) + "\n")
        print(f"Report: {args.report}", flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
