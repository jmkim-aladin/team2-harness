from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_hermes_discord_adapter.py"
spec = importlib.util.spec_from_file_location("run_hermes_discord_adapter", MODULE_PATH)
adapter = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(adapter)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_outbox(vault: Path) -> Path:
    base = vault / "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234"
    write_json(
        base / "hdp-board.json",
        {
            "schema": "team2.hermes_discord_outbox_item.v1",
            "request_id": "hdr-1234",
            "payload_id": "hdp-board",
            "channel": "agent-board",
            "content": "board",
        },
    )
    write_json(
        base / "hdp-user.json",
        {
            "schema": "team2.hermes_discord_outbox_item.v1",
            "request_id": "hdr-1234",
            "payload_id": "hdp-user",
            "channel": "jm-orchestrator",
            "content": "digest",
        },
    )
    manifest = {
        "schema": "team2.hermes_discord_outbox.v1",
        "request_id": "hdr-1234",
        "dispatch_required": True,
        "payload_count": 2,
        "base_path": "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234",
        "manifest_path": "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/manifest.json",
        "items": [
            {
                "payload_id": "hdp-board",
                "channel": "agent-board",
                "path": "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/hdp-board.json",
            },
            {
                "payload_id": "hdp-user",
                "channel": "jm-orchestrator",
                "path": "wiki/projects/agentic-os/hermes-discord-outbox/hdr-1234/hdp-user.json",
            },
        ],
    }
    write_json(base / "manifest.json", manifest)
    return base / "manifest.json"


class RunHermesDiscordAdapterTests(unittest.TestCase):
    def test_dry_run_marks_items_skipped_without_writing_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            manifest_path = write_outbox(vault)
            receipt_path = vault / "wiki/projects/agentic-os/hermes-discord-delivery-receipt.json"
            manifest = adapter.read_json(manifest_path)

            receipt, messages = adapter.run_adapter(
                vault,
                manifest,
                adapter_command=[],
                receipt_output=receipt_path,
                apply=False,
            )

            self.assertEqual(receipt["schema"], "team2.hermes_discord_delivery_receipt.v1")
            self.assertEqual([item["status"] for item in receipt["results"]], ["skipped", "skipped"])
            self.assertFalse(receipt_path.exists())
            self.assertIn("would write", messages[-1])

    def test_apply_runs_adapter_command_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            manifest_path = write_outbox(vault)
            receipt_path = vault / "wiki/projects/agentic-os/hermes-discord-delivery-receipt.json"
            script = vault / "fake_adapter.py"
            script.write_text(
                "\n".join(
                    [
                        "import json, pathlib, sys",
                        "item = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))",
                        "if item['payload_id'] == 'hdp-user':",
                        "    print('rate limit', file=sys.stderr)",
                        "    raise SystemExit(2)",
                        "print('discord-message-' + item['payload_id'])",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = adapter.read_json(manifest_path)

            receipt, messages = adapter.run_adapter(
                vault,
                manifest,
                adapter_command=[sys.executable, str(script)],
                receipt_output=receipt_path,
                apply=True,
            )

            self.assertEqual([item["status"] for item in receipt["results"]], ["dispatched", "failed"])
            self.assertEqual(receipt["results"][0]["external_id"], "discord-message-hdp-board")
            self.assertIn("rate limit", receipt["results"][1]["error"])
            self.assertTrue(receipt_path.exists())
            self.assertIn(f"wrote {receipt_path}", messages[-1])


if __name__ == "__main__":
    unittest.main()
