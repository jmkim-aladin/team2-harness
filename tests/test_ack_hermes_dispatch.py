from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "ack_hermes_dispatch.py"
spec = importlib.util.spec_from_file_location("ack_hermes_dispatch", MODULE_PATH)
ack = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(ack)


REQUEST = {
    "schema": "team2.hermes_discord_dispatch_request.v1",
    "request_id": "hdr-1234567890abcdef",
    "target": "hermes",
    "transport": "hermes-existing-discord-bot",
    "dispatch_status": "pending-hermes",
    "payloads": [
        {"payload_id": "hdp-1111111111111111", "channel": "agent-board", "content": "요약"},
        {"payload_id": "hdp-2222222222222222", "channel": "jm-orchestrator", "content": "결정 없음"},
    ],
}


class AckHermesDispatchTests(unittest.TestCase):
    def test_build_ack_marks_all_payloads_dispatched(self) -> None:
        result = ack.build_ack(REQUEST, dispatched_payload_ids=None, acked_at="2026-06-17T00:00:00+09:00")

        self.assertEqual(result["schema"], "team2.hermes_discord_dispatch_ack.v1")
        self.assertEqual(result["request_id"], "hdr-1234567890abcdef")
        self.assertEqual(result["dispatch_status"], "dispatched")
        self.assertEqual([item["status"] for item in result["payloads"]], ["dispatched", "dispatched"])

    def test_build_ack_marks_partial_dispatch(self) -> None:
        result = ack.build_ack(
            REQUEST,
            dispatched_payload_ids={"hdp-1111111111111111"},
            acked_at="2026-06-17T00:00:00+09:00",
        )

        self.assertEqual(result["dispatch_status"], "partial")
        self.assertEqual([item["status"] for item in result["payloads"]], ["dispatched", "pending"])

    def test_write_ack_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "hermes-discord-dispatch-ack.json"
            result = ack.build_ack(REQUEST, dispatched_payload_ids=None, acked_at="2026-06-17T00:00:00+09:00")

            messages = ack.write_ack(out, result, apply=True)

            self.assertEqual(messages, [f"wrote {out}"])
            stored = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(stored["request_id"], "hdr-1234567890abcdef")


if __name__ == "__main__":
    unittest.main()
