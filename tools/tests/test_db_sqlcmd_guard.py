"""Offline policy regression checks. No SQL is executed against any database."""

import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("db_sqlcmd_guard", ROOT / "tools/db_sqlcmd_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def command(sql="SELECT TOP 1 name FROM sys.tables", host=guard.DEV_HOST, db="WebCatalog"):
    return f"sqlcmd -S {shlex.quote(host)} -d {shlex.quote(db)} -U test_user -C -b -Q {shlex.quote(sql)}"


class GuardTests(unittest.TestCase):
    def test_allowed_dev_operations(self):
        for sql in [
            "SELECT TOP 10 name FROM sys.tables;",
            "SELECT 'DELETE; DROP TABLE test' AS sample",
            "INSERT INTO dbo.Test (Id, Name) VALUES (1, N'검증'), (2, 'O''Brien');",
            "UPDATE dbo.Test SET Name = N'변경', Flag = 1 WHERE Id = 2;",
            "DELETE FROM dbo.Test WHERE Id IN (1, 2) AND TestRun = 'run-1';",
            "UPDATE dbo.Test SET Name = 'DELETE' WHERE Id = 1",
        ]:
            with self.subTest(sql=sql):
                self.assertIsNone(guard.sql_reason(sql))
                if sql.startswith("SELECT"):
                    self.assertIsNone(guard.command_reason(command(sql)))
                else:
                    self.assertIn("db_execute.py", guard.command_reason(command(sql)))

    def test_ddl_sp_and_admin_denied(self):
        for sql in ["CREATE TABLE t (id int)", "DROP TABLE t", "TRUNCATE TABLE t",
                    "ALTER TABLE t ADD x int", "EXEC dbo.Anything", "GRANT SELECT TO u",
                    "MERGE t USING s ON t.id=s.id WHEN MATCHED THEN DELETE;",
                    "SELECT * INTO copied FROM dbo.Test", "USE OtherDb; SELECT 1"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_unsafe_dml_denied(self):
        for sql in ["UPDATE dbo.Test SET Name = 'all'", "DELETE FROM dbo.Test",
                    "DELETE FROM dbo.Test WHERE 1=1", "UPDATE dbo.Test SET [where] = 1",
                    "DELETE FROM dbo.[WHERE]", "DELETE FROM dbo.Test WHERE Id=1 OR 1=1",
                    "DELETE FROM dbo.Test WHERE Id IN (SELECT Id FROM dbo.Other)",
                    "UPDATE t SET Name='x' FROM dbo.Test t JOIN dbo.Other o ON t.Id=o.Id WHERE o.Id=1",
                    "INSERT INTO dbo.Test (Id) SELECT Id FROM dbo.Other",
                    "INSERT INTO dbo.Test (Id) VALUES (1); DELETE FROM dbo.Test WHERE Id=1",
                    "UPDATE dbo.Test SET Name='x' WHERE Id=1 DELETE FROM dbo.Test WHERE Id=2",
                    "INSERT INTO dbo.Test (Id) VALUES (1)\nGO\nSELECT 1",
                    "INSERT INTO dbo.Test (Id) OUTPUT inserted.Id VALUES (1)",
                    "INSERT INTO dbo.Test (Id) VALUES (dbo.ExternalEffect())"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_insert_row_bound(self):
        for count in [100, 101]:
            sql = "INSERT INTO dbo.Test (Id) VALUES " + ",".join(f"({i})" for i in range(count))
            self.assertEqual(guard.sql_reason(sql) is None, count == 100)
            self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_unknown_prod_staging_dynamic_hosts_denied(self):
        for host in ["prod.example", "staging.example", "$DB_HOST", guard.DEV_HOST + ".evil", "localhost"]:
            with self.subTest(host=host):
                self.assertIsNotNone(guard.command_reason(command(host=host)))
        self.assertIsNotNone(guard.command_reason(command(db="master")))
        self.assertIsNotNone(guard.command_reason(command(db="$DATABASE")))

    def test_remote_references_denied(self):
        for sql in ["SELECT * FROM prod.Db.dbo.Test", "SELECT * FROM OtherDb.dbo.Test",
                    "SELECT * FROM [prod].[Db].[dbo].[Test]",
                    "SELECT * FROM OtherDb..Test", "SELECT * FROM OPENQUERY(prod, 'SELECT 1')"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_dynamic_files_interactive_and_redirection_denied(self):
        prefix = f"sqlcmd -S {guard.DEV_HOST} -d WebCatalog"
        for suffix in ["", "-i /tmp/input.sql", '-Q "$SQL"', '-q "SELECT 1"',
                       '-Q "SELECT 1" -v x=1', '-Q "SELECT 1" > /tmp/result',
                       '-Q "SELECT 1" -S prod.example', '-Q "SELECT 1" -P secret',
                       '<<EOF\nSELECT 1\nEOF']:
            with self.subTest(suffix=suffix):
                self.assertIsNotNone(guard.command_reason(prefix + " " + suffix))

    def test_comments_and_sqlcmd_commands_denied(self):
        for sql in ["SELECT 1 -- comment", "SELECT /* comment */ 1", "SELECT 1\n:r input.sql",
                    "SELECT 1\n!! echo test", "SELECT $(value)", "SELECT 'unterminated"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_wrapped_literal_call_and_multicommand_inspection(self):
        self.assertIsNone(guard.command_reason('SQLCMDPASSWORD="$PW" /opt/homebrew/bin/' + command()))
        self.assertIsNotNone(guard.command_reason(command() + "; " + command(host="prod.example")))
        self.assertIsNotNone(guard.command_reason(command() + "\n" + command(host="prod.example")))
        self.assertIsNone(guard.command_reason("git status --short"))

    def test_attached_options_checked(self):
        self.assertIsNone(guard.command_reason(f"sqlcmd -S{guard.DEV_HOST} -dWebCatalog -Q'SELECT 1'"))
        self.assertIsNotNone(guard.command_reason("sqlcmd -Sprod.example -dWebCatalog -Q'SELECT 1'"))

    def test_real_hook_protocol(self):
        hook = ROOT / ".claude/hooks/sqlcmd-readonly.sh"
        for field in ["command", "cmd"]:
            for allowed in [True, False]:
                event = {"tool_input": {field: command(host=guard.DEV_HOST if allowed else "prod.example")}}
                result = subprocess.run(["bash", str(hook)], input=json.dumps(event), text=True,
                                        capture_output=True, check=True)
                if allowed:
                    self.assertEqual(result.stdout, "")
                else:
                    output = json.loads(result.stdout)["hookSpecificOutput"]
                    self.assertEqual(output["permissionDecision"], "deny")
                    self.assertEqual(output["hookEventName"], "PreToolUse")

    def test_bad_hook_input_fails_closed_without_echoing(self):
        for payload in ["not-json-sensitive", "null", "{}", '{"tool_input":null}']:
            result = subprocess.run(["python3", str(ROOT / "tools/db_sqlcmd_guard.py")],
                                    input=payload, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertNotIn("not-json-sensitive", result.stdout)


if __name__ == "__main__":
    unittest.main()
