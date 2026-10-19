"""No DB/Keychain access: diagnostics must never serialize raw error text."""
import errno
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_prod_diagnostics import CAPTURE_BYTES, Diagnostics


class DiagnosticTests(unittest.TestCase):
    def test_split_driver_message_is_classified_without_values(self):
        diag = Diagnostics()
        diag.capture("startup", "stderr", b"host.private account.private password.private x5")
        diag.capture("startup", "stderr", b"09: certificate signed by unknown authority")
        result = diag.snapshot()
        self.assertEqual(result[0]["sources"]["stderr"]["signatures"][0]["category"], "tls_certificate")
        self.assertNotIn("private", json.dumps(result))

    def test_unknown_server_text_and_arbitrary_exception_are_withheld(self):
        diag = Diagnostics()
        diag.capture("query", "stderr", b"Msg 50000: SELECT confidential_column; CUSTOMER_PRIVATE")
        diag.failure("query", RuntimeError("PASSWORD_PRIVATE"))
        result = diag.snapshot()[0]
        self.assertEqual(result["code"], "internal_error")
        self.assertEqual(result["sources"]["stderr"]["signatures"], [])
        self.assertEqual(result["sources"]["stderr"]["sql_error_numbers"], [])
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_known_sql_error_number(self):
        diag = Diagnostics()
        diag.capture("startup", "stderr", b"Msg 18456, Level 14, State 1: Login failed for user 'private'")
        result = diag.snapshot()[0]["sources"]["stderr"]
        self.assertEqual(result["sql_error_numbers"], [18456])
        self.assertNotIn("private", json.dumps(result))

    def test_capture_is_bounded_and_reports_truncation(self):
        diag = Diagnostics()
        for _ in range(20):
            diag.capture("startup", "stderr", b"sensitive" * CAPTURE_BYTES)
        self.assertEqual(len(diag._buffers[("startup", "stderr")]), CAPTURE_BYTES)
        self.assertTrue(diag.snapshot()[0]["sources"]["stderr"]["truncated"])
        self.assertLess(len(json.dumps(diag.snapshot())), 300)

    def test_both_streams_share_stage_budget_and_report_discarded_source(self):
        diag = Diagnostics()
        diag.capture("startup", "stdout", b"x" * CAPTURE_BYTES)
        diag.capture("startup", "stderr", b"PRIVATE_OVERFLOW")
        self.assertEqual(sum(map(len, diag._buffers.values())), CAPTURE_BYTES)
        self.assertTrue(diag.snapshot()[0]["sources"]["stderr"]["truncated"])

    def test_normal_handshake_is_not_an_error_stage(self):
        diag = Diagnostics()
        diag.capture("startup", "stdout", b"SQLCMD_READY\n")
        diag.failure("query", code="watchdog_close_failed")
        self.assertEqual(diag.snapshot(), [{"stage": "query", "code": "watchdog_close_failed"}])

    def test_os_error_keeps_errno_not_path_and_first_error_survives(self):
        diag = Diagnostics()
        diag.failure("startup", FileNotFoundError(errno.ENOENT, "PRIVATE_PATH"), code="process_start_failed")
        diag.failure("startup", RuntimeError("startup_failed"))
        item = diag.snapshot()[0]
        self.assertEqual((item["code"], item["errno"], item["os_code"]), ("process_start_failed", 2, "ENOENT"))
        self.assertNotIn("PRIVATE", json.dumps(item))

    def test_timeout_does_not_expose_command(self):
        diag = Diagnostics()
        diag.failure("observer", subprocess.TimeoutExpired("PRIVATE_COMMAND", 2, stderr=b"PRIVATE"))
        self.assertEqual(diag.snapshot(), [{"stage": "observer", "code": "process_timeout"}])
