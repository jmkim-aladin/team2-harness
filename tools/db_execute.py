#!/usr/bin/env python3
"""Bounded development DML, never an operational DB gateway.

The local ledger prevents accidental concurrent/repeated task overspend. It is
not tamper resistant. DB permissions and a trusted production gateway remain
separate controls. SQL and credentials are never written to the ledger/output.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sqlite3
import subprocess
import sys

from db_sqlcmd_guard import DEV_DATABASES, DEV_HOST, sql_reason

MAX_ROWS = 100
QUERY_TIMEOUT = 5
IDENTIFIER = r'(?:\[[^\]]+\]|"[^"]+"|[A-Za-z_][\w]*)'


def validate(sql):
    if len(sql) > 65536:
        raise ValueError("SQL exceeds 64 KiB")
    reason = sql_reason(sql)
    if reason:
        raise ValueError(reason)
    match = re.match(r"\s*(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+(" + IDENTIFIER +
                     r"(?:\s*\.\s*" + IDENTIFIER + r")?)", sql, re.I)
    if not match:
        raise ValueError("This executor accepts development INSERT/UPDATE/DELETE only")
    return match.group(1)


class Budget:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            raise ValueError("Ledger symlinks are not supported")
        # touch before sqlite opens it, so a newly created ledger is private.
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.connection = sqlite3.connect(path, timeout=5)
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
CREATE TABLE IF NOT EXISTS tasks (task TEXT PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0,
  pending TEXT, blocked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, task TEXT NOT NULL, database_name TEXT NOT NULL,
  sql_hash TEXT NOT NULL, status TEXT NOT NULL, rows INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
""")

    def reserve(self, task, database, sql, run):
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("INSERT OR IGNORE INTO tasks(task) VALUES (?)", (task,))
            used, pending, blocked = self.connection.execute(
                "SELECT used,pending,blocked FROM tasks WHERE task=?", (task,)).fetchone()
            if pending or blocked:
                raise ValueError("Task has an unresolved or concurrent execution; reconcile before continuing")
            if used >= MAX_ROWS:
                raise ValueError("Task row budget exhausted")
            self.connection.execute("UPDATE tasks SET pending=? WHERE task=?", (run, task))
            self.connection.execute("INSERT INTO runs(id,task,database_name,sql_hash,status) VALUES (?,?,?,?,?)",
                                    (run, task, database, hashlib.sha256(sql.encode()).hexdigest(), "pending"))
        return MAX_ROWS - used

    def finish(self, task, run, status, rows=0):
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            current = self.connection.execute("SELECT pending FROM tasks WHERE task=?", (task,)).fetchone()
            if current != (run,):
                raise ValueError("Ledger execution mismatch")
            self.connection.execute("UPDATE runs SET status=?,rows=? WHERE id=?", (status, rows, run))
            if status == "unknown":
                self.connection.execute("UPDATE tasks SET blocked=1 WHERE task=?", (task,))
            else:
                self.connection.execute("UPDATE tasks SET used=used+?,pending=NULL WHERE task=?", (rows, task))

    def close(self):
        self.connection.close()


def batch(sql, target, run, remaining):
    escaped_target = target.replace("'", "''")
    return f"""SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;
SET LOCK_TIMEOUT 1000;
DECLARE @lock_result int;
EXEC @lock_result=sys.sp_getapplock @Resource=N'team2:{run}', @LockMode='Exclusive', @LockOwner='Session', @LockTimeout=1000;
IF @lock_result < 0 THROW 51004, 'Execution lock unavailable', 1;
RAISERROR(N'TEAM2_{run}_SESSION', 0, 1) WITH NOWAIT;
DECLARE @commit_started bit=0;
BEGIN TRY
  IF ISNULL(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION'),0) <> 1
    THROW 51005, 'VIEW DEFINITION required for side-effect checks', 1;
  DECLARE @object_id int=OBJECT_ID(N'{escaped_target}', N'U');
  IF @object_id IS NULL THROW 51006, 'Only local base tables are supported', 1;
  BEGIN TRANSACTION;
  DECLARE @lock_probe bit;
  SELECT TOP (1) @lock_probe=1 FROM {target} WITH (TABLOCKX,HOLDLOCK);
  SET @object_id=OBJECT_ID(N'{escaped_target}', N'U');
  IF @object_id IS NULL THROW 51006, 'Only local base tables are supported', 1;
  IF EXISTS(SELECT 1 FROM sys.triggers WHERE parent_id=@object_id AND is_disabled=0)
    THROW 51007, 'Enabled triggers require a separate reviewed path', 1;
  IF EXISTS(SELECT 1 FROM sys.foreign_keys WHERE referenced_object_id=@object_id
            AND (delete_referential_action<>0 OR update_referential_action<>0))
    THROW 51008, 'Cascading changes require a separate reviewed path', 1;
  IF EXISTS(SELECT 1 FROM sys.tables WHERE object_id=@object_id AND temporal_type<>0)
    THROW 51009, 'Temporal tables require a separate reviewed path', 1;
  {sql.rstrip().removesuffix(';')};
  DECLARE @affected int=@@ROWCOUNT;
  IF @affected > {remaining} THROW 51001, 'Task row budget exceeded; rolled back', 1;
  SET @commit_started=1;
  COMMIT TRANSACTION;
  PRINT 'TEAM2_{run}_COMMITTED:' + CONVERT(varchar(20),@affected);
END TRY
BEGIN CATCH
  IF XACT_STATE()<>0
  BEGIN
    ROLLBACK TRANSACTION;
    PRINT 'TEAM2_{run}_ROLLED_BACK';
  END
  ELSE IF @commit_started=0 PRINT 'TEAM2_{run}_ROLLED_BACK';
  THROW;
END CATCH;
"""


def execute(*, task, database, sql, transport, ledger):
    """Execute one bounded DML; transport is a callable(batch, timeout)->CompletedProcess."""
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,79}", task):
            raise ValueError("Use a stable ticket/work ID (3-80 ASCII letters, digits, - or _)")
        if database.lower() not in DEV_DATABASES:
            raise ValueError("Database is not in the development allowlist")
        target = validate(sql)
    except ValueError as error:
        return {"ok": False, "status": "rejected", "error": str(error)}
    run = secrets.token_hex(16)
    budget = None
    try:
        budget = Budget(ledger)
        remaining = budget.reserve(task, database, sql, run)
    except (ValueError, OSError, sqlite3.Error) as error:
        if budget:
            budget.close()
        return {"ok": False, "status": "blocked", "error": str(error)}
    result = {"ok": False, "status": "unknown", "run_id": run}
    try:
        try:
            completed = transport(batch(sql, target, run, remaining), QUERY_TIMEOUT)
            stdout, stderr = completed.stdout or "", completed.stderr or ""
            code = completed.returncode
        except (Exception, KeyboardInterrupt):
            stdout, stderr, code = "", "", -1
        lines = [line.strip() for line in (stdout + "\n" + stderr).splitlines() if line.strip()]
        session = f"TEAM2_{run}_SESSION"
        receipt = re.fullmatch(f"TEAM2_{run}_COMMITTED:([0-9]+)", lines[1]) if len(lines) == 2 else None
        timed_out = bool(re.search(r"\btimeout\s+expired\b", stdout + stderr, re.I))
        if code == 0 and not timed_out and lines[:1] == [session] and receipt:
            affected = int(receipt.group(1))
            if affected <= remaining:
                result.update(ok=True, status="committed", rows=affected, remaining_rows=remaining-affected)
        elif f"TEAM2_{run}_ROLLED_BACK" in lines and session in lines:
            result.update(status="rolled_back", error="database_rejected", sql_error_codes=
                          sorted(set(map(int, re.findall(r"Msg\s+(\d+)", stdout + stderr)))))
        if result["status"] == "unknown":
            result["error"] = "timeout" if timed_out else "missing_or_invalid_commit_receipt"
            # The marker proves the original request acquired this session lock.
            # Reacquiring it proves release; absence of a marker stays unconfirmed.
            result["session_cleanup_confirmed"] = False
            if session in lines:
                probe = f"""SET NOCOUNT ON;
DECLARE @r int;
EXEC @r=sys.sp_getapplock @Resource=N'team2:{run}', @LockMode='Exclusive', @LockOwner='Session', @LockTimeout=1000;
IF @r>=0 PRINT 'TEAM2_{run}_RELEASED';
"""
                try:
                    checked = transport(probe, 3)
                    result["session_cleanup_confirmed"] = (checked.returncode == 0 and
                        (checked.stdout or "").strip() == f"TEAM2_{run}_RELEASED" and not checked.stderr)
                except (Exception, KeyboardInterrupt):
                    pass
        budget.finish(task, run, result["status"], result.get("rows", 0))
    except (ValueError, OSError, sqlite3.Error):
        # A lost acknowledgement after COMMIT is uncertain, never retryable.
        result = {"ok": False, "status": "unknown", "run_id": run, "error": "ledger_update_failed"}
    finally:
        budget.close()
    return result


class SqlcmdTransport:
    def __init__(self, database, user):
        self.database, self.user = database, user

    def __call__(self, sql, timeout):
        args = ["sqlcmd", "-S", DEV_HOST, "-d", self.database, "-U", self.user,
                "-C", "-b", "-x", "-l", "3", "-t", str(timeout), "-h", "-1", "-W"]
        # Drop sqlcmd startup scripts and implicit connection/options settings;
        # keep only its password input. Other OS/runtime variables are retained.
        environment = {key: value for key, value in os.environ.items()
                       if not key.upper().startswith("SQLCMD") or key == "SQLCMDPASSWORD"}
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True, env=environment)
        try:
            stdout, stderr = process.communicate(sql + "\nGO\n", timeout=timeout+8)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(args, 1, stdout, stderr + "\nTimeout expired\n")
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", required=True)
    args = parser.parse_args()
    if not os.environ.get("SQLCMDPASSWORD"):
        print(json.dumps({"ok": False, "status": "rejected", "error": "SQLCMDPASSWORD required"}))
        return 1
    def interrupted(*_):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    result = execute(task=args.task, database=args.database, sql=sys.stdin.read(65537),
                     transport=SqlcmdTransport(args.database, args.user),
                     ledger=Path.home()/".local/state/team2/db-execution.sqlite3")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
