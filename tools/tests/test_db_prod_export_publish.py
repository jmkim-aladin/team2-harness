"""Staging, durable completion, no-replace publication and restart reconciliation (Q3b slice 2)."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_prod_export as ex  # noqa: E402
from db_query_control import Store  # noqa: E402
from test_db_prod_export import COLUMNS, SAMPLE, sqlcmd_stdout  # noqa: E402


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        Store.initialize(root / "control.sqlite3")
        self.store = Store(root / "control.sqlite3")
        self.exports = root / "exports"
        self.ledger = ex.ExportLedger(self.store, self.exports)
        self.request_id = "a" * 32

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, request_id=None):
        rid = request_id or self.request_id
        return ex.canonical_spec(COLUMNS, purpose="개발 참고", max_file_bytes=1 << 20, max_record_bytes=1 << 16,
                                 max_rows=None, artifact_directory=str(self.exports / rid))

    def session(self, request_id=None):
        rid = request_id or self.request_id
        session = ex.ExportSession(self.ledger, self.spec(rid), request_id=rid, run_id="r" + rid[1:],
                                   owner="uid:1", epoch=3, approval_digest="d" * 64)
        session.open()
        return session

    def complete(self, session, stdout=None):
        session.feed(stdout or sqlcmd_stdout(SAMPLE))
        session.finish()
        session.commit_completion()

    def test_rename_no_replace_never_overwrites(self):
        a, b = self.exports / "a", self.exports / "b"
        self.exports.mkdir()
        a.mkdir(); b.mkdir(); (b / "keep").write_text("x")
        with self.assertRaises(FileExistsError):
            ex.rename_no_replace(a, b)
        self.assertTrue(a.is_dir())
        self.assertEqual((b / "keep").read_text(), "x")
        c = self.exports / "c"
        ex.rename_no_replace(a, c)
        self.assertTrue(c.is_dir())
        self.assertFalse(a.exists())

    def test_successful_publication_is_private_complete_and_bound_to_spec(self):
        session = self.session()
        self.assertEqual(self.ledger.status(self.request_id)["state"], "exporting")
        self.complete(session)
        self.assertEqual(self.ledger.status(self.request_id)["state"], "complete")
        self.assertFalse((self.exports / self.request_id).exists(), "completion alone must not publish")
        status = session.publish(gate=lambda: True)
        self.assertEqual(status["state"], "exported")
        final = self.exports / self.request_id
        self.assertEqual(sorted(p.name for p in final.iterdir()), ["data.csv", "manifest.json"])
        self.assertEqual(stat.S_IMODE(final.stat().st_mode), 0o700)
        for name in ("data.csv", "manifest.json"):
            self.assertEqual(stat.S_IMODE((final / name).stat().st_mode), 0o600)
        manifest = json.loads((final / "manifest.json").read_text())
        data = (final / "data.csv").read_bytes()
        self.assertEqual(manifest["csv_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(manifest["spec_digest"], ex.spec_digest(manifest["spec"]))
        self.assertEqual(manifest["spec_digest"], self.spec()["digest"])
        self.assertEqual(manifest["request_id"], self.request_id)
        self.assertEqual(manifest["records"], 2)
        self.assertNotIn("sql", json.dumps(manifest).lower().replace("sqlcmd", ""))
        self.assertEqual([p.name for p in self.exports.iterdir()], [self.request_id])

    def test_stop_before_publication_discards_staging(self):
        session = self.session()
        self.complete(session)
        status = session.publish(gate=lambda: False)
        self.assertEqual(status["state"], "not_published")
        self.assertEqual(status["reason"], "stopped_before_publish")
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_existing_destination_is_left_untouched(self):
        session = self.session()
        self.complete(session)
        (self.exports / self.request_id).mkdir(mode=0o700)
        (self.exports / self.request_id / "mine").write_text("keep")
        status = session.publish(gate=lambda: True)
        self.assertEqual(status["state"], "not_published")
        self.assertEqual(status["reason"], "destination_exists")
        self.assertEqual((self.exports / self.request_id / "mine").read_text(), "keep")
        self.assertEqual([p.name for p in self.exports.iterdir()], [self.request_id])

    def test_codec_failure_or_incomplete_stream_never_publishes(self):
        session = self.session()
        with self.assertRaises(ex.ExportDenied):
            session.feed(b"Lx\n")
        session.abort("query_failed")
        self.assertEqual(self.ledger.status(self.request_id)["state"], "failed")
        self.assertEqual(list(self.exports.iterdir()), [])
        other = self.session("b" * 32)
        other.feed(sqlcmd_stdout(SAMPLE)[:50])
        with self.assertRaises(ex.ExportDenied):
            other.finish()
        with self.assertRaises(ex.ExportDenied):
            other.publish(gate=lambda: True)
        other.abort("export_incomplete")
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_untrusted_exports_root_is_refused(self):
        self.tmp2 = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp2.cleanup)
        os.symlink(self.tmp2.name, self.exports)
        with self.assertRaises(ex.ExportDenied):
            self.session()

    def test_restart_reconciliation(self):
        published = self.session("1" * 32); self.complete(published); published.publish(gate=lambda: True)
        unpublished = self.session("2" * 32); self.complete(unpublished)          # crash before publish
        writing = self.session("3" * 32); writing.feed(sqlcmd_stdout(SAMPLE)[:100])  # crash mid-stream
        renamed = self.session("4" * 32); self.complete(renamed); renamed.write_manifest()
        ex.rename_no_replace(renamed.staging, self.exports / ("4" * 32))         # crash after rename
        tampered = self.session("5" * 32); self.complete(tampered); tampered.write_manifest()
        ex.rename_no_replace(tampered.staging, self.exports / ("5" * 32))
        (self.exports / ("5" * 32) / "data.csv").write_bytes(b"changed")
        self.ledger.mark("5" * 32, "export_unknown", "publish_state_unrecorded")
        ex.ExportLedger(self.store, self.exports)  # a new gateway instance reconciles
        states = {rid: self.ledger.status(rid * 32)["state"] for rid in "12345"}
        self.assertEqual(states, {"1": "exported", "2": "not_published", "3": "failed",
                                  "4": "exported", "5": "export_unknown"})
        self.assertEqual(sorted(p.name for p in self.exports.iterdir()), ["1" * 32, "4" * 32, "5" * 32])
        self.assertEqual((self.exports / ("5" * 32) / "data.csv").read_bytes(), b"changed")

    # --- review fixes (2026-11-05) ---------------------------------------
    def open_rows(self):
        exporting = self.session("1" * 32); exporting.feed(sqlcmd_stdout(SAMPLE)[:100])
        complete = self.session("2" * 32); self.complete(complete)
        unknown = self.session("3" * 32); self.complete(unknown)
        self.ledger.mark("3" * 32, "export_unknown", "publish_state_unrecorded")
        return exporting

    def test_restart_survives_a_deleted_exports_root(self):
        writing = self.open_rows()
        writing.file.close()
        import shutil
        shutil.rmtree(self.exports)
        ex.ExportLedger(self.store, self.exports)  # must not raise: the gateway has to boot
        states = {r: self.ledger.status(r * 32)["state"] for r in "123"}
        self.assertEqual(states, {"1": "failed", "2": "not_published", "3": "export_unknown"})

    def test_restart_survives_an_untrusted_exports_root(self):
        self.open_rows()
        os.chmod(self.exports, 0o755)
        ex.ExportLedger(self.store, self.exports)
        for r in "123":
            self.assertEqual(self.ledger.status(r * 32)["state"], "export_unknown")
            self.assertEqual(self.ledger.status(r * 32)["reason"], "exports_root_untrusted")
        self.assertTrue((self.exports / (".staging-" + "2" * 32)).exists(), "untrusted root is never modified")

    def test_unknown_publication_stays_unknown_when_final_is_gone(self):
        session = self.session(); self.complete(session); session.write_manifest()
        ex.rename_no_replace(session.staging, session.final)
        self.ledger.mark(self.request_id, "export_unknown", "publish_state_unrecorded")
        import shutil
        shutil.rmtree(session.final)
        ex.ExportLedger(self.store, self.exports)
        self.assertEqual(self.ledger.status(self.request_id)["state"], "export_unknown")

    def test_abort_after_a_publish_attempt_never_claims_failure(self):
        session = self.session(); self.complete(session)
        original = self.ledger.mark
        def broken(request_id, state, reason):
            raise OSError("ledger unavailable")
        self.ledger.mark = broken
        try:
            status = session.publish(gate=lambda: True)  # records nothing, but never raises past the rename
        finally:
            self.ledger.mark = original
        self.assertNotEqual(status["state"], "exported")
        session.abort("export_failed")  # e.g. a later step in the job thread failed
        self.assertEqual(self.ledger.status(self.request_id)["state"], "export_unknown")
        self.assertTrue(session.final.exists(), "a published artifact is never removed by abort")

    def test_planted_manifest_is_refused(self):
        session = self.session(); self.complete(session)
        (session.staging / "manifest.json").write_text("{}")
        with self.assertRaises(ex.ExportDenied):
            session.publish(gate=lambda: True)
        self.assertFalse(session.final.exists())

    def test_root_is_rechecked_right_before_publication(self):
        session = self.session(); self.complete(session)
        os.chmod(self.exports, 0o755)
        status = session.publish(gate=lambda: True)
        self.assertNotEqual(status["state"], "exported")
        self.assertFalse(session.final.exists())

    def test_lineage_records_the_approval_digest_and_epoch(self):
        session = self.session(); self.complete(session); session.publish(gate=lambda: True)
        manifest = json.loads((session.final / "manifest.json").read_text())
        self.assertEqual(manifest["approval_digest"], "d" * 64)
        self.assertEqual(manifest["epoch"], 3)
        self.assertEqual(self.ledger.status(self.request_id)["approval_digest"], "d" * 64)

    def test_codec_reason_is_available_after_a_rejected_stream(self):
        session = self.session()
        with self.assertRaises(ex.ExportDenied):
            session.feed(b"Lx\n")
        self.assertEqual(session.failure_reason(), "frame_missing_header")


if __name__ == "__main__":
    unittest.main()
