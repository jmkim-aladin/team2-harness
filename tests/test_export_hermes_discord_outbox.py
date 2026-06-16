from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "export_hermes_discord_outbox.py"
spec = importlib.util.spec_from_file_location("export_hermes_discord_outbox", MODULE_PATH)
outbox = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(outbox)


BATCH = {
    "schema": "team2.hermes_discord_dispatch_batch.v1",
    "request_id": "hdr-1234",
    "dispatch_required": True,
    "payload_count": 2,
    "payloads": [
        {"payload_id": "hdp-board", "channel": "agent-board", "content": "board summary"},
        {"payload_id": "hdp-user", "channel": "jm-orchestrator", "content": "user digest"},
    ],
}


class ExportHermesDiscordOutboxTests(unittest.TestCase):
    def test_build_outbox_manifest_lists_payload_files(self) -> None:
        result = outbox.build_outbox(BATCH, base_rel_path="wiki/projects/agentic-os/hermes-discord-outbox")

        self.assertEqual(result["schema"], "team2.hermes_discord_outbox.v1")
        self.assertEqual(result["request_id"], "hdr-1234")
        self.assertEqual(result["payload_count"], 2)
        self.assertEqual(
            [item["path"] for item in result["items"]],
            [
                "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/hdp-board.json",
                "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/hdp-user.json",
            ],
        )

    def test_write_outbox_writes_manifest_and_payload_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            manifest = outbox.build_outbox(BATCH, base_rel_path="wiki/projects/agentic-os/hermes-discord-outbox")

            messages = outbox.write_outbox(vault, BATCH, manifest, apply=True)

            manifest_path = vault / "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/manifest.json"
            payload_path = vault / "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/hdp-board.json"
            self.assertIn(f"wrote {manifest_path}", messages)
            self.assertTrue(manifest_path.exists())
            self.assertTrue(payload_path.exists())
            stored_payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(stored_payload["schema"], "team2.hermes_discord_outbox_item.v1")
            self.assertEqual(stored_payload["payload_id"], "hdp-board")
            self.assertEqual(stored_payload["channel"], "agent-board")
            self.assertEqual(stored_payload["content"], "board summary")

    def test_empty_batch_writes_empty_manifest_without_payload_files(self) -> None:
        batch = {
            "schema": "team2.hermes_discord_dispatch_batch.v1",
            "request_id": "hdr-empty",
            "dispatch_required": False,
            "payload_count": 0,
            "payloads": [],
        }

        result = outbox.build_outbox(batch, base_rel_path="wiki/projects/agentic-os/hermes-discord-outbox")

        self.assertFalse(result["dispatch_required"])
        self.assertEqual(result["items"], [])


if __name__ == "__main__":
    unittest.main()
