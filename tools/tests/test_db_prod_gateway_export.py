"""Gateway CSV export mode: reviewed batch + bound spec -> detached job -> published artifact (Q3b slice 2)."""
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_db_prod_gateway as fixtures  # noqa: E402
from test_db_prod_export import COLUMNS, SAMPLE, sqlcmd_stdout  # noqa: E402
import db_prod_export as ex  # noqa: E402
from db_prod_gateway import Gateway  # noqa: E402
from db_query_control import Denied  # noqa: E402

SELECT = "SELECT s, n, e, flag FROM dbo.sample ORDER BY s"
EXPORT = dict(columns=COLUMNS, purpose="개발 참고", max_file_bytes=1 << 20, max_record_bytes=1 << 16, max_rows=None)


class StreamBackend(fixtures.Backend):
    stdout = sqlcmd_stdout(SAMPLE)
    dispatched = []

    def attach_stream_sink(self, sink):
        self.sink = sink

    def dispatch(self, sql, limits):
        type(self).dispatched.append((sql, dict(limits)))
        for offset in range(0, len(self.stdout), 4096):
            try:
                self.sink.feed(self.stdout[offset:offset + 4096])
            except Exception:
                type(self).result = False
                return

    def output_bytes(self):
        return b""


class GatewayExportTests(unittest.TestCase):
    def setUp(self):
        fixtures.GatewayTests.setUp(self)
        StreamBackend.started, StreamBackend.result, StreamBackend.dispatched = 0, True, []
        StreamBackend.stdout = sqlcmd_stdout(SAMPLE)
        self.gateway = Gateway(self.store, self.vault, self.audit,
                               {"lego-prod": dict(enabled=True, read_only_verified=True)},
                               allowed_uids=[self.uid], backend_type=StreamBackend)
        self.exports = Path(self.store.path).parent / "exports"

    tearDown = fixtures.GatewayTests.tearDown

    def preview(self, **changes):
        request = dict(action="prepare", api_version=2, output_mode="csv", target="lego-prod",
                       database="master", timeout=30, select_sql=SELECT, export=dict(EXPORT))
        request.update(changes)
        return self.gateway.handle(request, self.uid)["review"]

    def submit(self, review):
        return self.gateway.handle(dict(action="approve_submit", request_id=review["request_id"],
                                        approval_digest=review["approval_digest"],
                                        selected_actions=review["selected_actions"],
                                        approval_source="explicit-user-chat"), self.uid)

    def wait(self, review):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = self.gateway.handle(dict(action="job_status", request_id=review["request_id"]), self.uid)
            if status["job_state"] in ("completed", "failed", "recovery_required", "unknown"):
                # A terminal job must already carry its settled export state.
                self.assertNotIn((status.get("export") or {}).get("state"), ("exporting", "complete"))
                return status
            time.sleep(0.005)
        self.fail("job did not settle")

    def test_review_shows_the_complete_batch_and_binds_the_export_spec(self):
        review = self.preview()
        spec = ex.canonical_spec(artifact_directory=str(self.exports / review["request_id"]), **EXPORT)
        self.assertEqual(review["output_mode"], "csv")
        self.assertEqual(review["sql"], ex.build_batch(SELECT, spec))
        self.assertEqual(review["export_spec"], spec["spec"])
        self.assertEqual(review["export_spec_digest"], spec["digest"])
        self.assertIn("export_csv", review["selected_actions"])
        self.assertIsNone(review["max_rows"])
        self.assertEqual(review["max_bytes"], spec["spec"]["max_source_bytes"])
        other = self.preview(export=dict(EXPORT, max_rows=5))
        self.assertNotEqual(other["export_spec_digest"], review["export_spec_digest"])
        self.assertFalse(self.exports.exists(), "preview must not touch the filesystem")

    def test_csv_mode_requires_v2_a_single_select_and_a_valid_spec(self):
        bad = [dict(api_version=1), dict(sql="SELECT 1"), dict(select_sql="SELECT 1; SELECT 2"),
               dict(export=dict(EXPORT, columns=[])), dict(export=dict(EXPORT, max_file_bytes=None)),
               dict(export=dict(EXPORT, unknown=1)), dict(output_mode="xlsx")]
        for change in bad:
            with self.subTest(change=change), self.assertRaises(Denied):
                self.preview(**change)

    def test_approved_export_publishes_once_and_job_reports_it(self):
        review = self.preview()
        self.assertEqual(self.submit(review)["status"], "accepted")
        status = self.wait(review)
        self.assertEqual(status["job_state"], "completed")
        self.assertEqual(status["result_state"], "none", "CSV mode keeps no memory result")
        export = status["export"]
        self.assertEqual(export["state"], "exported")
        final = self.exports / review["request_id"]
        self.assertEqual(export["directory"], str(final))
        self.assertEqual(export["records"], 2)
        self.assertEqual(sorted(p.name for p in final.iterdir()), ["data.csv", "manifest.json"])
        manifest = json.loads((final / "manifest.json").read_text())
        self.assertEqual(manifest["spec_digest"], review["export_spec_digest"])
        self.assertEqual(export["csv_sha256"], manifest["csv_sha256"])
        self.assertEqual(len(StreamBackend.dispatched), 1)
        sql, limits = StreamBackend.dispatched[0]
        self.assertEqual(sql, review["sql"], "the dispatched batch is exactly the reviewed text")
        self.assertEqual(limits["max_bytes"], review["max_bytes"])
        self.assertIsNone(limits["max_rows"])
        again = self.submit(review)
        self.assertTrue(again.get("already_submitted"))
        self.assertEqual(len(StreamBackend.dispatched), 1)

    def test_stop_before_publication_publishes_nothing(self):
        review = self.preview()
        with patch.object(Gateway, "_export_gate", return_value=False):
            self.submit(review)
            status = self.wait(review)
        self.assertEqual(status["export"]["state"], "not_published")
        self.assertEqual(status["export"]["reason"], "stopped_before_publish")
        self.assertNotIn("directory", status["export"])
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_terminal_job_never_reports_an_unsettled_export(self):
        review = self.preview()
        original = Gateway._export_gate
        def slow_gate(gateway, epoch):
            time.sleep(0.3)
            return original(gateway, epoch)
        with patch.object(Gateway, "_export_gate", slow_gate):
            self.submit(review)
            status = self.wait(review)
        self.assertEqual(status["export"]["state"], "exported")

    def test_existing_destination_is_never_overwritten(self):
        review = self.preview()
        final = Path(review["export_spec"]["artifact_directory"])
        self.exports.mkdir(mode=0o700)
        final.mkdir(mode=0o700)
        (final / "mine.txt").write_text("keep")
        self.submit(review)
        status = self.wait(review)
        self.assertEqual(status["export"]["state"], "not_published", status["export"])
        self.assertEqual(status["export"]["reason"], "destination_exists")
        self.assertEqual(sorted(p.name for p in final.iterdir()), ["mine.txt"])

    def test_rejected_stream_fails_the_job_and_leaves_no_files(self):
        lines = StreamBackend.stdout.split(b"\n")
        StreamBackend.stdout = b"\n".join([lines[0], b"Hzz"] + lines[2:])
        review = self.preview()
        self.submit(review)
        status = self.wait(review)
        self.assertNotEqual(status["job_state"], "completed")
        self.assertEqual(status["export"]["state"], "failed")
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_transport_without_stream_support_never_dispatches(self):
        gateway = Gateway(self.store, self.vault, self.audit,
                          {"lego-prod": dict(enabled=True, read_only_verified=True)},
                          allowed_uids=[self.uid], backend_type=fixtures.Backend)
        self.gateway = gateway
        review = self.preview()
        self.submit(review)
        status = self.wait(review)
        self.assertNotEqual(status["job_state"], "completed")
        self.assertEqual(fixtures.Backend.started, 0)

    # --- review fixes (2026-11-05) ---------------------------------------
    def test_untrusted_exports_root_is_refused_before_approval(self):
        self.exports.mkdir(mode=0o755)
        with self.assertRaises(Denied):
            self.preview()

    def test_csv_job_records_no_empty_memory_result(self):
        review = self.preview(); self.submit(review); status = self.wait(review)
        self.assertIsNone(status["result_digest"])
        self.assertNotIn("output_bytes", status)
        self.assertNotIn("output_sha256", status)

    def test_rejection_reason_reaches_the_export_ledger(self):
        review = self.preview(export=dict(EXPORT, max_file_bytes=12))
        self.submit(review); status = self.wait(review)
        self.assertEqual(status["export"]["state"], "failed")
        self.assertEqual(status["export"]["reason"], "export_file_bytes_exceeded")

    def test_audit_carries_no_result_digest_and_lineage_uses_the_run_epoch(self):
        events = []
        self.gateway.audit = type("A", (), {"write": lambda _s, event, **d: events.append((event, d))})()
        review = self.preview(); self.submit(review); status = self.wait(review)
        settled = [d for e, d in events if e == "export_settled"]
        self.assertEqual(len(settled), 1)
        self.assertNotIn("csv_sha256", settled[0]); self.assertNotIn("records", settled[0])
        manifest = json.loads((Path(status["export"]["directory"]) / "manifest.json").read_text())
        self.assertEqual(manifest["approval_digest"], review["approval_digest"])
        self.assertEqual(manifest["epoch"], status["epoch"])


if __name__ == "__main__":
    unittest.main()
