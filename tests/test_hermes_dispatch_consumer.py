from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "hermes_dispatch_consumer.py"
spec = importlib.util.spec_from_file_location("hermes_dispatch_consumer", MODULE_PATH)
consumer = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(consumer)


REQUEST = {
    "schema": "team2.hermes_discord_dispatch_request.v1",
    "request_id": "hdr-current",
    "target": "hermes",
    "transport": "hermes-existing-discord-bot",
    "dispatch_status": "pending-hermes",
    "payloads": [
        {"payload_id": "hdp-board", "channel": "agent-board", "content": "board"},
        {"payload_id": "hdp-user", "channel": "jm-orchestrator", "content": "digest"},
        {"payload_id": "hdp-dev", "channel": "agent-dev", "content": "brief"},
    ],
}


class HermesDispatchConsumerTests(unittest.TestCase):
    def test_build_batch_returns_all_payloads_without_ack(self) -> None:
        result = consumer.build_batch(REQUEST, ack=None)

        self.assertEqual(result["schema"], "team2.hermes_discord_dispatch_batch.v1")
        self.assertEqual(result["request_id"], "hdr-current")
        self.assertTrue(result["dispatch_required"])
        self.assertEqual([item["payload_id"] for item in result["payloads"]], ["hdp-board", "hdp-user", "hdp-dev"])

    def test_build_batch_skips_fully_dispatched_same_request(self) -> None:
        ack = {
            "schema": "team2.hermes_discord_dispatch_ack.v1",
            "request_id": "hdr-current",
            "dispatch_status": "dispatched",
            "payloads": [
                {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "dispatched"},
                {"payload_id": "hdp-dev", "channel": "agent-dev", "status": "dispatched"},
            ],
        }

        result = consumer.build_batch(REQUEST, ack=ack)

        self.assertFalse(result["dispatch_required"])
        self.assertEqual(result["payloads"], [])

    def test_build_batch_returns_only_pending_for_partial_ack(self) -> None:
        ack = {
            "schema": "team2.hermes_discord_dispatch_ack.v1",
            "request_id": "hdr-current",
            "dispatch_status": "partial",
            "payloads": [
                {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "pending"},
            ],
        }

        result = consumer.build_batch(REQUEST, ack=ack)

        self.assertTrue(result["dispatch_required"])
        self.assertEqual([item["payload_id"] for item in result["payloads"]], ["hdp-user", "hdp-dev"])

    def test_new_request_ignores_ack_for_old_request(self) -> None:
        ack = {
            "schema": "team2.hermes_discord_dispatch_ack.v1",
            "request_id": "hdr-old",
            "dispatch_status": "dispatched",
            "payloads": [
                {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "dispatched"},
            ],
        }

        result = consumer.build_batch(REQUEST, ack=ack)

        self.assertEqual([item["payload_id"] for item in result["payloads"]], ["hdp-board", "hdp-user", "hdp-dev"])

    def test_build_updated_ack_merges_existing_and_newly_dispatched_payloads(self) -> None:
        ack = {
            "schema": "team2.hermes_discord_dispatch_ack.v1",
            "request_id": "hdr-current",
            "dispatch_status": "partial",
            "payloads": [
                {"payload_id": "hdp-board", "channel": "agent-board", "status": "dispatched"},
                {"payload_id": "hdp-user", "channel": "jm-orchestrator", "status": "pending"},
            ],
        }

        result = consumer.build_updated_ack(
            REQUEST,
            ack=ack,
            dispatched_payload_ids={"hdp-user"},
            acked_at="2026-06-17T00:00:00+09:00",
        )

        self.assertEqual(result["dispatch_status"], "partial")
        self.assertEqual([item["status"] for item in result["payloads"]], ["dispatched", "dispatched", "pending"])


if __name__ == "__main__":
    unittest.main()
