"""Offline policy regression checks. No SQL is executed against any database."""

import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("db_sqlcmd_guard", ROOT / "tools/db_sqlcmd_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

# data-requests-dev2 DEV2-12580 query.sql 형태: DECLARE·#temp·Community 3부 이름·주석·DROP #temp.
DEV2_12580 = """\
----------------------------------------------------------------------
-- 티켓: DEV2-12580 — 중고매장 이벤트 앱푸시 대상자
----------------------------------------------------------------------
SET NOCOUNT ON;
DECLARE @OidFrom int = dbo.fn_OID_FirstOfDate('2025-01-01');
DECLARE @OidTo   int = dbo.fn_OID_LastOfDate('2026-10-13');
SELECT @OidFrom AS OidFrom, @OidTo AS OidTo;

IF OBJECT_ID('tempdb..#Online') IS NOT NULL DROP TABLE #Online;
SELECT DISTINCT O.CustKey
INTO #Online
FROM dbo.Orders AS O WITH(NOLOCK)
WHERE O.OID BETWEEN @OidFrom AND @OidTo
  AND NOT EXISTS (SELECT 1 FROM dbo.OrdersPOS AS P WITH(NOLOCK) WHERE P.OID = O.OID);
SELECT COUNT(*) AS [STEP1_온라인구매고객] FROM #Online;
GO
IF OBJECT_ID('tempdb..#Final') IS NOT NULL DROP TABLE #Final;
/* STEP 3: 법인 제외 + 앱푸시 수신 가능 */
SELECT DISTINCT T.CustKey
INTO #Final
FROM #Online AS T
INNER JOIN dbo.Customer AS C WITH(NOLOCK) ON C.CustKey = T.CustKey
INNER JOIN Community.dbo.AppPushToken AS APT WITH(NOLOCK) ON APT.Custkey = T.CustKey
LEFT OUTER JOIN dbo.NotiSetting AS N WITH(NOLOCK) ON N.Custkey = T.CustKey
WHERE ISNULL(C.CustomerType, 0) NOT IN (4, 5, 6, 7)
  AND (N.onEvent IS NULL OR N.onEvent = 1);
SELECT COUNT(*) AS [STEP3_최종대상] FROM #Final;

-- INSERT INTO Lego.WebStat.dbo.tmpMail_YYYYMMDD_DEV2_12580_apppush (CustKey)
-- SELECT CustKey FROM #Final;
DROP TABLE #Online, #Final;
"""


def command(sql="SELECT TOP 1 name FROM sys.tables", host=guard.DEV_HOST, db="WebCatalog"):
    return f"sqlcmd -S {shlex.quote(host)} -d {shlex.quote(db)} -U test_user -C -b -Q {shlex.quote(sql)}"


def file_command(path, host=guard.DEV_HOST, db="WebCatalog", extra=""):
    return f"sqlcmd -S {shlex.quote(host)} -d {shlex.quote(db)} -U test_user -C -b {extra}-i {shlex.quote(str(path))}"


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
        missing = Path(tempfile.mkdtemp()) / "missing.sql"  # -i는 읽기 스크립트로 열렸다 — 못 읽는 파일만 거부
        for suffix in ["", f"-i {missing}", '-Q "$SQL"', '-q "SELECT 1"',
                       '-Q "SELECT 1" -v x=1', '-Q "SELECT 1" > /tmp/result',
                       '-Q "SELECT 1" -S prod.example', '-Q "SELECT 1" -P secret',
                       '<<EOF\nSELECT 1\nEOF']:
            with self.subTest(suffix=suffix):
                self.assertIsNotNone(guard.command_reason(prefix + " " + suffix))

    def test_sqlcmd_commands_variables_and_unterminated_denied(self):
        # 주석(-- · /* */)은 2026-10-22 읽기 스크립트 허용으로 test_read_script_constructs_allowed로 옮겼다.
        for sql in ["SELECT 1\n:r input.sql", "SELECT 1\n!! echo test", "SELECT 1\n:!! ls",
                    "SELECT 1\n  :connect prod.example", "SELECT 1\n:setvar x 1", "SELECT 1\nEXIT(SELECT 1)",
                    "SELECT 1\nED", "SELECT 1\nGO 2", "SELECT 1\nGO -- c", "SELECT $(value)",
                    "SELECT 'unterminated", "SELECT /* unterminated", "SELECT [unterminated",
                    "SELECT 1 /*\nGO\n*/ SELECT 2", "SELECT 'a\nGO\nsp_who --'", "SELECT 1\rGO\rsp_who",
                    "SELECT `x`", "SELECT 1 \\ 2", "SELECT {fn NOW()}", "", "-- only comment"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))
        with self.subTest(sql="file $( )"):
            self.assertIsNotNone(guard.script_reason("SELECT '$(secret)'"))

    def test_read_script_constructs_allowed(self):
        for sql in [
            DEV2_12580, "SELECT 1 -- comment", "SELECT /* comment /* nested */ */ 1",
            "SET NOCOUNT ON; SET STATISTICS IO, TIME ON\nSET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED\nSELECT 1",
            "DECLARE @t TABLE (Id int PRIMARY KEY); INSERT INTO @t VALUES (1); SELECT * FROM @t",
            ";WITH c AS (SELECT 1 AS x) SELECT x INTO #c FROM c; SELECT * FROM #c",
            "CREATE TABLE #x (Id int NOT NULL PRIMARY KEY, Name nvarchar(10) DEFAULT N'a')\n"
            "INSERT INTO #x (Id) SELECT 1; UPDATE #x SET Name = 'b' WHERE Id = 1; DELETE FROM #x WHERE Id = 2\n"
            "DELETE #x; TRUNCATE TABLE #x; DROP TABLE IF EXISTS #x",
            "IF OBJECT_ID('tempdb..#x') IS NOT NULL DROP TABLE #x",
            "WHILE @i < 3 BEGIN SET @i += 1; IF @i = 2 BREAK ELSE CONTINUE END\nPRINT 'done'\nRETURN",
            "SELECT * FROM Community.dbo.AppPushToken a JOIN [WebCatalog].[dbo].[Orders] o ON 1 = 1",
            "SELECT * FROM tempdb.sys.columns", "USE Community\nGO\nSELECT 1\ngo",
            "EXEC sp_help 'dbo.Orders'", "EXEC sys.sp_columns @table_name = N'Orders'", "EXECUTE sp_helptext N'dbo.usp_X'",
            "SELECT x FROM t ORDER BY x OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY",
            "SELECT 'GO; DROP TABLE x; EXEC sp_who' AS s",
            # data-requests-dev2 실제 스크립트 관용구: 임시 테이블 인덱스, 진행 메시지
            "CREATE UNIQUE CLUSTERED INDEX CX_tmp ON #Orders (OID) INCLUDE (CustKey)",
            "RAISERROR(@msg, 0, 1) WITH NOWAIT", "RAISERROR('ABORT', 16, 1)",
        ]:
            with self.subTest(sql=sql[:60]):
                self.assertIsNone(guard.command_reason(command(sql)))
        # 백틱은 -Q에서는 셸 확장이라 거부하지만 파일의 문자열·주석 안에서는 의미가 없다.
        self.assertIsNone(guard.script_reason("SELECT N'`tbl`' AS reply -- `note`"))

    def test_permanent_writes_and_ddl_denied(self):
        for sql in ["SELECT 1; INSERT INTO dbo.Test (Id) VALUES (1)", "SELECT 1\nGO\nUPDATE dbo.Test SET a = 1 WHERE Id = 1",
                    "DELETE a FROM #x a", "UPDATE STATISTICS dbo.Test",
                    DEV2_12580.replace("-- INSERT INTO Lego", "INSERT INTO Lego").replace("-- SELECT CustKey", "SELECT CustKey")]:
            with self.subTest(sql=sql[:60]):
                reason = guard.command_reason(command(sql))
                self.assertIsNotNone(reason)
                if not sql.startswith("UPDATE STATISTICS"):
                    self.assertIn("db_execute.py", reason)
        for sql in ["SELECT * INTO dbo.Copied FROM #x", "SELECT * INTO tempdb.dbo.Copied FROM #x",
                    "DELETE #x OUTPUT deleted.* INTO dbo.Perm", "SELECT * INTO ##g FROM t", "CREATE TABLE ##g (a int)",
                    "CREATE INDEX ix ON dbo.Test (a)", "CREATE INDEX ix ON ##g (a)", "ALTER TABLE #x ADD b int",
                    "DROP TABLE #x, dbo.Test", "CREATE TABLE Lego.WebStat.dbo.tmpMail (CustKey int)",
                    "MERGE #x USING t ON 1 = 1 WHEN MATCHED THEN DELETE;", "TRUNCATE TABLE dbo.Test"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_exec_dynamic_sql_and_session_control_denied(self):
        for sql in ["EXEC dbo.Anything", "EXEC sp_executesql N'SELECT 1'", "EXEC ('SELECT 1')", "EXEC @sql",
                    "EXECUTE AS USER = 'u'", "EXEC sp_help @name", "EXEC master.dbo.sp_help 'x'",
                    "sp_who", "SELECT 1\nGO\nxp_cmdshell 'dir'", "SELECT 1; xp_cmdshell 'dir'",
                    "BEGIN TRAN; SELECT 1", "BEGIN TRANSACTION", "SELECT 1 COMMIT", "ROLLBACK", "SAVE TRANSACTION s",
                    "WAITFOR DELAY '00:00:05'", "SET IMPLICIT_TRANSACTIONS ON", "SET ANSI_NULLS, IMPLICIT_TRANSACTIONS ON",
                    "SET IDENTITY_INSERT #x ON", "DECLARE c CURSOR FOR SELECT 1", "SELECT NEXT VALUE FOR dbo.Seq",
                    "RAISERROR(@msg, 0, 1) WITH NOWAIT, LOG", "SELECT `x`",
                    "GRANT SELECT ON t TO u", "DBCC CHECKDB", "KILL 52", "BULK INSERT #x FROM 'f'",
                    "SELECT * FROM OPENROWSET('a', 'b', 'c')", "ENABLE TRIGGER t ON dbo.Test"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))

    def test_database_and_server_scope(self):
        for sql in ["SELECT * FROM master.sys.databases", "SELECT * FROM Lego.WebStat.dbo.T",
                    "SELECT dbo.Test.Id FROM dbo.Test", "USE master", "USE OtherDb; SELECT 1"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(guard.command_reason(command(sql)))
        for host in ["prod.example", guard.DEV_HOST + ".evil"]:
            with self.subTest(host=host):
                self.assertIn("운영", guard.command_reason(command(DEV2_12580, host=host)))

    def test_input_file_scripts(self):
        folder = Path(tempfile.mkdtemp())
        good, bad, legacy, fifo = (folder / name for name in ["good.sql", "bad.sql", "legacy.sql", "fifo.sql"])
        good.write_text(DEV2_12580, encoding="utf-8")
        bad.write_text("SELECT 1;\nINSERT INTO dbo.Test (Id) VALUES (1);\n", encoding="utf-8")
        legacy.write_bytes("SELECT N'한글'".encode("cp949"))
        os.mkfifo(fifo)
        credential = 'PW=$(security find-generic-password -s "cool-dev" -a "$(whoami)" -w)\n'
        for allowed in [file_command(good), file_command(good, extra="-f 65001 "),
                        f'{credential}SQLCMDPASSWORD="$PW" {file_command(good)}\nunset PW']:
            with self.subTest(command=allowed[-40:]):
                self.assertIsNone(guard.command_reason(allowed))
        self.assertIn("db_execute.py", guard.command_reason(file_command(bad)))
        for denied in [file_command(folder / "missing.sql"), file_command("good.sql"), file_command(legacy),
                       file_command(fifo), file_command(f"{good},{bad}"), file_command(good, extra="-f 949 "),
                       file_command(good, host="prod.example"), file_command(good, db="master"),
                       file_command(good) + " -Q 'SELECT 1'", file_command(good) + " | head",
                       f"cp {bad} {good}; {file_command(good)}", f"cd {folder} && {file_command(good)}",
                       f"cat > {good} <<'EOF'\nDROP TABLE x\nEOF\n{file_command(good)}",
                       f'X="$(cp {bad} {good})" {file_command(good)}']:
            with self.subTest(command=denied[-60:]):
                self.assertIsNotNone(guard.command_reason(denied))

    def test_shell_continuation_and_comments_follow_bash(self):
        # 이어 쓴 줄의 -S도 같은 호출이다 — 정책 문서의 여러 줄 예시는 허용, 운영 호스트 추가는 거부.
        documented = (f'SQLCMDPASSWORD="$PW" sqlcmd -S "{guard.DEV_HOST}" \\\n'
                      "  -U u -C -d WebCatalog -h -1 -W -Q \"SELECT TOP 10 name FROM sys.tables\"")
        self.assertIsNone(guard.command_reason(documented))
        for denied in [command() + " \\\n  -S prod.example", command(db="WebCatalog#x") + " -S prod.example",
                       "# it's\n" + command() + " \\\n -S prod.example\n# '",
                       f"sqlcmd -S {guard.DEV_HOST} -d WebCatalog -Q $'SELECT 1\\nDROP TABLE x'"]:
            with self.subTest(command=denied[-50:]):
                self.assertIsNotNone(guard.command_reason(denied))
        self.assertIsNone(guard.command_reason(command("SELECT 1") + " # it's a comment"))

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
