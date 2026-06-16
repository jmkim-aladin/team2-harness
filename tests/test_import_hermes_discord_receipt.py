from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "import_hermes_discord_receipt.py"
spec = importlib.util.spec_from_file_location("import_hermes_discord_receipt", MODULE_PATH)
receipt_importer = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(receipt_importer)


REQUEST = {
    "schema": "team2.hermes_discord_dispatch_request.v1",
    "request_id": "hdr-1234",
    "target": "hermes",
    "transport": "hermes-existing-discord-bot",
    "dispatch_status": "pending-hermes",
    "payloads": [
        {"payload_id": "hdp-board", "channel": "agent-board", "content": "board"},
        {"payload_id": "hdp-user", "channel": "jm-orchestrator", "content": "digest"},
        {"payload_id": "hdp-dev", "channel": "agent-dev", "content": "brief"},
    ],
}


class ImportHermesDiscordReceiptTests(unittest.TestCase):
    def test_build_ack_from_receipt_marks_only_dispatched_results(self) -> None:
        receipt = {
            "schema": "team2.hermes_discord_delivery_receipt.v1",
            "request_id": "hdr-1234",
            "results": [
                {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "failed", "error": "rate limit"},
            ],
        }

        result = receipt_importer.build_ack_from_receipt(
            REQUEST,
            receipt,
            existing_ack=None,
            acked_at="2026-06-17T00:00:00+09:00",
        )

        self.assertEqual(result["dispatch_status"], "partial")
        self.assertEqual([item["status"] for item in result["payloads"]], ["dispatched", "pending", "pending"])

    def test_build_ack_from_receipt_merges_existing_dispatched_payloads(self) -> None:
        existing_ack = {
            "schema": "team2.hermes_discord_dispatch_ack.v1",
            "request_id": "hdr-1234",
            "dispatch_status": "partial",
            "payloads": [
                {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "pending"},
                {"payload_id": "hdp-dev", "channel": "agent-dev", "status": "pending"},
            ],
        }
        receipt = {
            "schema": "team2.hermes_discord_delivery_receipt.v1",
            "request_id": "hdr-1234",
            "results": [
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "dispatched"},
            ],
        }

        result = receipt_importer.build_ack_from_receipt(
            REQUEST,
            receipt,
            existing_ack=existing_ack,
            acked_at="2026-06-17T00:00:00+09:00",
        )

        self.assertEqual([item["status"] for item in result["payloads"]], ["dispatched", "dispatched", "pending"])

    def test_request_id_mismatch_is_rejected(self) -> None:
        receipt = {
            "schema": "team2.hermes_discord_delivery_receipt.v1",
            "request_id": "hdr-other",
            "results": [],
        }

        with self.assertRaises(ValueError):
            receipt_importer.build_ack_from_receipt(REQUEST, receipt, existing_ack=None)

    def test_write_ack_from_receipt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ack.json"
            receipt = {
                "schema": "team2.hermes_discord_delivery_receipt.v1",
                "request_id": "hdr-1234",
                "results": [
                    {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                    {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "dispatched"},
                    {"payload_id": "hdp-dev", "channel": "agent-dev", "status": "dispatched"},
                ],
            }

            ack = receipt_importer.build_ack_from_receipt(
                REQUEST,
                receipt,
                existing_ack=None,
                acked_at="2026-06-17T00:00:00+09:00",
            )
            messages = receipt_importer.write_ack(out, ack, apply=True)

            self.assertEqual(messages, [f"wrote {out}"])
            stored = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(stored["dispatch_status"], "dispatched")


if __name__ == "__main__":
    unittest.main()
