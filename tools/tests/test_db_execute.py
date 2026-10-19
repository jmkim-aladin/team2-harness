"""Public execution boundary: bounded commits, failure classification, task budget."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))


class ExecutionContractTests(unittest.TestCase):
    @staticmethod
    def committed(sql, rows):
        marker = re.search(r"TEAM2_([a-f0-9]+)_SESSION", sql).group(1)
        return subprocess.CompletedProcess([], 0, f"TEAM2_{marker}_SESSION\nTEAM2_{marker}_COMMITTED:{rows}\n", "")

    def test_same_task_inflight_blocks_second_transport(self):
        from db_execute import execute
        with tempfile.TemporaryDirectory() as directory:
            args = dict(task="DEV2-SHARED", database="WebCatalog",
                        sql="DELETE FROM dbo.Test WHERE Id=1;", ledger=Path(directory)/"budget.sqlite3")
            def forbidden(*_):
                self.fail("Pending task must not reach the DB a second time")
            def first(sql, timeout):
                other = execute(**args, transport=forbidden)
                self.assertEqual(other["status"], "blocked")
                return self.committed(sql, 1)
            self.assertTrue(execute(**args, transport=first)["ok"])

    def test_budget_is_shared_across_databases_and_survives_new_call(self):
        from db_execute import execute
        with tempfile.TemporaryDirectory() as directory:
            args = dict(task="DEV2-SHARED", sql="DELETE FROM dbo.Test WHERE Id=1;",
                        ledger=Path(directory)/"budget.sqlite3")
            first = execute(**args, database="WebCatalog", transport=lambda sql, _: self.committed(sql, 60))
            self.assertEqual(first["remaining_rows"], 40)
            def second(sql, _):
                self.assertIn("IF @affected > 40", sql)
                return self.committed(sql, 40)
            self.assertEqual(execute(**args, database="Community", transport=second)["remaining_rows"], 0)
            def forbidden(*_):
                self.fail("Exhausted task must not reach the DB")
            self.assertEqual(execute(**args, database="WebCatalog", transport=forbidden)["status"], "blocked")

    def test_invalid_or_production_target_never_calls_transport(self):
        from db_execute import execute
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(*_):
                self.fail("Rejected request must not reach the DB")
            for database, sql in [("Production", "DELETE FROM dbo.Test WHERE Id=1;"),
                                  ("WebCatalog", "ALTER PROCEDURE dbo.Test AS SELECT 1;"),
                                  ("WebCatalog", "DELETE FROM dbo.Test;")]:
                result = execute(task="DEV2-TEST", database=database, sql=sql,
                                 transport=forbidden, ledger=Path(directory)/"budget.sqlite3")
                self.assertEqual(result["status"], "rejected")

    def test_sqlcmd_batch_tokens_inside_literals_are_rejected(self):
        from db_execute import execute
        with tempfile.TemporaryDirectory() as directory:
            for separator in ("GO", "go 2", "\tGO\t"):
                def forbidden(*_):
                    self.fail("sqlcmd separators must be rejected before transport")
                result = execute(task="DEV2-GO", database="WebCatalog",
                                 sql=f"INSERT INTO dbo.Test (Label) VALUES (N'first\n{separator}\nlast');",
                                 transport=forbidden, ledger=Path(directory)/"budget.sqlite3")
                self.assertEqual(result["status"], "rejected")

    def test_timeout_exit_zero_is_failure_and_blocks_replay(self):
        from db_execute import execute
        calls = []
        def transport(sql, timeout):
            calls.append(sql)
            return subprocess.CompletedProcess([], 0, "Timeout expired\n", "")
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "budget.sqlite3"
            result = execute(task="DEV2-TEST", database="WebCatalog", sql="DELETE FROM dbo.Test WHERE Id=1;",
                             transport=transport, ledger=ledger)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["error"], "timeout")
            retry = execute(task="DEV2-TEST", database="WebCatalog", sql="DELETE FROM dbo.Test WHERE Id=1;",
                            transport=transport, ledger=ledger)
            self.assertEqual(retry["status"], "blocked")
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
