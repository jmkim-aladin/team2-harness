"""CLI: CSV preview/run display and exit codes that reflect the job, not the RPC (Q3b slice 3)."""
import io
import json
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_prod_client  # noqa: E402
import test_db_prod_gateway as fixtures  # noqa: E402
import test_db_prod_gateway_export as gx  # noqa: E402  (module import: avoid re-running its tests)
StreamBackend, SELECT = gx.StreamBackend, gx.SELECT


class ClientExportTests(unittest.TestCase):
    setUp = gx.GatewayExportTests.setUp
    tearDown = gx.GatewayExportTests.tearDown

    def cli(self, *argv, stdin=""):
        def rpc(request):
            chunks = []
            result = self.gateway.handle(request, self.uid, publish=chunks.append)
            return chunks[0] if chunks else result
        output = io.StringIO()
        with patch.object(db_prod_client, "rpc", side_effect=rpc), \
                patch.object(db_prod_client, "require_current_gateway"), \
                patch.object(sys, "argv", ["client", *argv]), patch.object(sys, "stdin", io.StringIO(stdin)), \
                redirect_stdout(output):
            code = db_prod_client.main()
        return code, output.getvalue()

    def preview(self, *extra):
        return self.cli("preview", "--target", "lego-prod", "--database", "master", "--timeout", "30",
                        "--output", "csv", "--columns", "s:string,n:number,e:string,flag:boolean",
                        "--purpose", "개발 참고", "--max-file-bytes", "1048576", *extra, stdin=SELECT)

    @staticmethod
    def field(text, name):
        for line in text.splitlines():
            if line.startswith(name + ": "):
                return json.loads(line[len(name) + 2:])
        raise KeyError(name)

    def test_csv_preview_shows_batch_spec_directory_and_action(self):
        code, out = self.preview()
        self.assertEqual(code, 0)
        review = json.loads(out[out.rindex("\n{\n") + 1:])["review"]
        self.assertIn(json.dumps(review["sql"], ensure_ascii=False), out)
        self.assertEqual(self.field(out, "export_spec"), review["export_spec"])
        self.assertEqual(self.field(out, "export_spec_digest"), review["export_spec_digest"])
        self.assertIn("저장 위치: " + review["export_spec"]["artifact_directory"], out)
        self.assertIn("CSV로 저장", out)
        self.assertIn("스프레드시트", out)
        self.assertIn("export_csv", self.field(out, "selected_actions"))

    def test_csv_options_are_rejected_without_csv_output(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), patch("sys.stderr", io.StringIO()):
                self.cli("preview", "--target", "lego-prod", "--database", "master", "--timeout", "30",
                         "--columns", "s:string", stdin=SELECT)
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), patch("sys.stderr", io.StringIO()):
                self.cli("preview", "--target", "lego-prod", "--database", "master", "--timeout", "30",
                         "--output", "csv", "--columns", "s:date", "--purpose", "x", "--max-file-bytes", "10",
                         stdin=SELECT)

    def run_preview(self):
        code, out = self.preview()
        review = json.loads(out[out.rindex("\n{\n") + 1:])["review"]
        return self.cli("run", review["request_id"], "--from-chat-digest", review["approval_digest"])

    def test_run_reports_published_export_and_exits_zero(self):
        code, out = self.run_preview()
        result = json.loads(out[out.rindex("\n{\n") + 1:])
        self.assertEqual(code, 0)
        self.assertEqual(result["job_state"], "completed")
        self.assertEqual(result["export"]["state"], "exported")
        self.assertTrue(Path(result["export"]["directory"], "data.csv").is_file())

    def test_run_exits_nonzero_when_the_export_is_not_published(self):
        lines = StreamBackend.stdout.split(b"\n")
        StreamBackend.stdout = b"\n".join([lines[0], b"Hzz"] + lines[2:])
        code, out = self.run_preview()
        self.assertNotEqual(code, 0)

    def test_run_exits_nonzero_when_the_job_failed(self):
        """Q4 finding: a failed job (cancel/timeout/worker loss) used to exit 0."""
        self.gateway = fixtures.Gateway(self.store, self.vault, self.audit,
                                        {"lego-prod": dict(enabled=True, read_only_verified=True)},
                                        allowed_uids=[self.uid], backend_type=fixtures.Backend)
        fixtures.Backend.result = False
        code, out = self.cli("preview", "--target", "lego-prod", "--database", "master", "--timeout", "5",
                             stdin="SELECT 1 AS v")
        review = json.loads(out[out.rindex("\n{\n") + 1:])["review"]
        code, out = self.cli("run", review["request_id"], "--from-chat-digest", review["approval_digest"])
        result = json.loads(out[out.rindex("\n{\n") + 1:])
        self.assertEqual(result["job_state"], "failed")
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
