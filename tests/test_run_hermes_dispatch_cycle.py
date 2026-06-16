from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_hermes_dispatch_cycle.py"
spec = importlib.util.spec_from_file_location("run_hermes_dispatch_cycle", MODULE_PATH)
cycle = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(cycle)


def write_note(vault: Path, rel_path: str, text: str) -> None:
    path = vault / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RunHermesDispatchCycleTests(unittest.TestCase):
    def test_dry_run_builds_pending_batch_without_writing_projection_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_note(
                vault,
                "wiki/processes/tickets/dev2-1001.md",
                "\n".join(
                    [
                        "---",
                        "type: ticket",
                        "title: DEV2-1001 결제 정책 선택",
                        "ticket_id: DEV2-1001",
                        "ticket_status: in-progress",
                        "decision_status: decision-needed",
                        "service: \"[[storefront]]\"",
                        "---",
                        "",
                        "A안 추천",
                        "",
                    ]
                ),
            )

            result = cycle.run_cycle(vault, apply=False, updated_at="2026-06-17")

            self.assertEqual(result["schema"], "team2.hermes_dispatch_cycle.v1")
            self.assertEqual(result["mode"], "dry-run")
            self.assertEqual(result["board"]["cards"], 1)
            self.assertEqual(result["dispatch_request"]["payload_count"], 3)
            self.assertEqual(result["batch"]["payload_count"], 3)
            self.assertTrue(result["batch"]["dispatch_required"])
            self.assertFalse((vault / "wiki/projects/agentic-os/hermes-decision-board.json").exists())
            self.assertFalse((vault / "wiki/projects/agentic-os/hermes-discord-dispatch-request.json").exists())

    def test_apply_writes_projection_request_and_optional_batch_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            batch_output = vault / "wiki/projects/agentic-os/hermes-discord-dispatch-batch.json"

            result = cycle.run_cycle(vault, apply=True, updated_at="2026-06-17", batch_output=batch_output)

            self.assertEqual(result["mode"], "apply")
            self.assertTrue((vault / "wiki/projects/agentic-os/hermes-decision-board.json").exists())
            self.assertTrue((vault / "wiki/projects/agentic-os/hermes-discord-dispatch-request.json").exists())
            self.assertTrue(batch_output.exists())
            stored = json.loads(batch_output.read_text(encoding="utf-8"))
            self.assertEqual(stored["schema"], "team2.hermes_discord_dispatch_batch.v1")
            self.assertEqual(stored["payload_count"], 2)

    def test_apply_can_export_outbox_for_adapter_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            batch_output = vault / "wiki/projects/agentic-os/hermes-discord-dispatch-batch.json"
            outbox_base = "wiki/projects/agentic-os/hermes-discord-outbox"

            result = cycle.run_cycle(
                vault,
                apply=True,
                updated_at="2026-06-17",
                batch_output=batch_output,
                outbox_base=outbox_base,
            )

            manifest_path = vault / result["outbox"]["manifest_path"]
            self.assertTrue(manifest_path.exists())
            self.assertEqual(result["outbox"]["schema"], "team2.hermes_discord_outbox.v1")
            self.assertEqual(result["outbox"]["payload_count"], 2)
            first_item_path = vault / result["outbox"]["items"][0]["path"]
            self.assertTrue(first_item_path.exists())

    def test_existing_ack_suppresses_duplicate_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            first = cycle.run_cycle(vault, apply=True, updated_at="2026-06-17")
            request_id = first["dispatch_request"]["request_id"]
            payloads = first["batch"]["payloads"]
            ack_path = vault / "wiki/projects/agentic-os/hermes-discord-dispatch-ack.json"
            ack_path.write_text(
                json.dumps(
                    {
                        "schema": "team2.hermes_discord_dispatch_ack.v1",
                        "request_id": request_id,
                        "acked_at": "2026-06-17T00:00:00+09:00",
                        "dispatch_status": "dispatched",
                        "payloads": [
                            {"payload_id": item["payload_id"], "channel": item["channel"], "status": "dispatched"}
                            for item in payloads
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            second = cycle.run_cycle(vault, apply=False, updated_at="2026-06-17")

            self.assertFalse(second["batch"]["dispatch_required"])
            self.assertEqual(second["batch"]["payload_count"], 0)


if __name__ == "__main__":
    unittest.main()
