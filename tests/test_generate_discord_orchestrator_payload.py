from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_discord_orchestrator_payload.py"
spec = importlib.util.spec_from_file_location("generate_discord_orchestrator_payload", MODULE_PATH)
payloads = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(payloads)


def card(card_id: str, column: str, roles: list[str], **extra: object) -> dict[str, object]:
    return {
        "id": card_id, "column": column, "work_id": card_id, "title": f"{card_id} 작업",
        "path": f"wiki/{card_id}.md", "suggested_roles": roles, **extra,
    }


class GenerateDiscordOrchestratorPayloadTests(unittest.TestCase):
    def test_builds_board_digest_user_digest_and_role_handoffs(self) -> None:
        board = {
            "schema": "team2.hermes_decision_board.v1",
            "updated_at": "2026-06-17",
            "cards": [
                {
                    "column": "Decision Needed",
                    "work_id": "DEV2-1001",
                    "ticket_id": "DEV2-1001",
                    "service": "[[storefront]]",
                    "title": "결제 정책 선택",
                    "summary": "A안 추천",
                    "path": "wiki/processes/tickets/dev2-1001.md",
                    "suggested_roles": ["orchestrator", "planner"],
                    "attention": "agent",
                },
                {
                    "column": "Review Needed",
                    "work_id": "project:agentic-os/discord-orchestration",
                    "ticket_id": "",
                    "service": "",
                    "title": "Discord 오케스트레이션 설계 검토",
                    "summary": "역할 프로필 계약 검토 필요",
                    "path": "wiki/projects/agentic-os/discord-orchestration.md",
                    "suggested_roles": ["orchestrator", "qa", "designer"],
                    "attention": "agent",
                },
            ],
        }

        result = payloads.build_payloads(board)

        self.assertEqual(
            [item["channel"] for item in result],
            ["agent-board", "jm-orchestrator", "agent-planning", "agent-qa", "agent-design"],
        )
        self.assertIn("Decision Needed: 1", result[0]["content"])
        self.assertIn("Review Needed: 1", result[0]["content"])
        self.assertIn("AI 검토 대기: 2", result[0]["content"])
        self.assertNotIn("DEV2-1001", result[1]["content"])
        self.assertIn("AI 검토 대기 2건 · AI 검토·질문 준비 1건", result[1]["content"])
        self.assertIn("## Task Brief", result[2]["content"])
        self.assertIn("Role: planner", result[2]["content"])
        self.assertIn("Ticket: 없음", result[3]["content"])
        self.assertIn("Role: designer", result[4]["content"])

    def test_empty_board_only_reports_no_user_intervention(self) -> None:
        board = {
            "schema": "team2.hermes_decision_board.v1",
            "updated_at": "2026-06-17",
            "cards": [],
        }

        result = payloads.build_payloads(board)

        self.assertEqual([item["channel"] for item in result], ["agent-board", "jm-orchestrator"])
        self.assertIn("현재 사용자에게 올릴 결정·승인 요청 없음", result[1]["content"])
        self.assertIn("AI 검토 대기 0건 · AI 검토·질문 준비 0건", result[1]["content"])

    def test_needs_review_cards_do_not_flood_user_digest(self) -> None:
        cards = [
            card(f"review-{index}", "Review Needed", ["orchestrator", "qa"], attention="agent")
            for index in range(12)
        ]

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": cards})

        digest = result[1]["content"]
        self.assertIn("현재 사용자에게 올릴 결정·승인 요청 없음", digest)
        self.assertIn("AI 검토 대기 12건 · AI 검토·질문 준비 0건", digest)
        self.assertNotIn("###", digest)
        self.assertEqual([item["channel"] for item in result[2:]], ["agent-qa"] * 12)
        self.assertIn("needs-review alone is not a user request", result[2]["content"])

    def test_incomplete_human_packet_goes_to_agent_triage(self) -> None:
        incomplete = card("half", "Decision Needed", ["orchestrator", "planner"], attention="human")
        incomplete["human_request"] = {"question": "A안?", "reason": "비용", "recommendation": "A안", "evidence": "  "}

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": [incomplete]})

        digest = result[1]["content"]
        self.assertNotIn("A안?", digest)
        self.assertIn("AI 검토·질문 준비 1건", digest)
        self.assertIn("human 패킷 미완성 1", result[0]["content"])
        brief = result[2]["content"]
        self.assertEqual(result[2]["channel"], "agent-planning")
        self.assertIn("Attention: human-incomplete", brief)
        self.assertIn("human packet is incomplete", brief)

    def test_approval_and_blocked_cards_stay_unresolved(self) -> None:
        cards = [
            card("approve", "Approval Needed", ["orchestrator"], attention="agent"),
            card("blocked", "Blocked", ["orchestrator"], attention="agent"),
        ]

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": cards})

        self.assertIn("AI 검토·질문 준비 2건", result[1]["content"])
        self.assertIn("요청이 없다는 것이 완료나 승인을 뜻하지 않는다", result[1]["content"])
        for brief in (item["content"] for item in result[2:]):
            self.assertIn("label alone does not establish a human dependency", brief)
            self.assertIn("execution approvals stay pending and are never self-approved", brief)
            self.assertIn("draft human_request", brief)

    def test_brief_carries_source_specific_next_action(self) -> None:
        follow_up = card("follow", "Review Needed", ["qa"], attention="agent",
                         agent_task={"kind": "verify-evidence", "next_action": "develop HEAD에서 revert 커밋 포함 여부를 확인한다"})
        plain = card("plain", "Review Needed", ["qa"], attention="agent", agent_task={"kind": "verify-evidence", "next_action": " "})

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": [follow_up, plain]})

        self.assertIn("- Next Action: develop HEAD에서 revert 커밋 포함 여부를 확인한다", result[2]["content"])
        self.assertNotIn("Next Action", result[3]["content"])

    def test_orchestrator_only_cards_get_fallback_role_brief(self) -> None:
        cards = [
            card("blocked", "Blocked", ["orchestrator"], attention="agent"),
            card("review", "Review Needed", ["orchestrator"], attention="agent"),
            card("unknown-role", "Decision Needed", ["orchestrator", "ghost"], attention="agent"),
        ]

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": cards})

        self.assertEqual(
            [item["channel"] for item in result[2:]],
            ["agent-domain", "agent-qa", "agent-domain"],
        )
        self.assertIn("Role: domain_analyst", result[2]["content"])
        self.assertIn("Role: qa", result[3]["content"])
        self.assertIn("record source revision, environment, result and limits", result[2]["content"])

    def test_legacy_card_without_attention_is_never_sent_to_user(self) -> None:
        legacy = card("legacy", "Decision Needed", ["orchestrator", "planner"])
        legacy["human_request"] = {
            "question": "레거시 질문", "reason": "r", "recommendation": "c", "evidence": "e"}

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": [legacy]})

        self.assertNotIn("레거시 질문", result[1]["content"])
        self.assertIn("attention 미지정 1", result[0]["content"])
        self.assertIn("Attention: legacy-unrouted", result[2]["content"])
        self.assertIn("attention is missing", result[2]["content"])

    def test_complete_human_packet_is_rendered_without_agent_brief(self) -> None:
        ready = card("ready", "Approval Needed", ["orchestrator", "qa"], attention="human")
        ready["human_request"] = {
            "question": "운영 배포를 승인하나?",
            "reason": "배포는 사람 승인 대상이다",
            "recommendation": "로컬 검증 결과로 stage 먼저",
            "evidence": "wiki/sample.md §검증 결과",
        }
        other = card("other", "Review Needed", ["qa"], attention="agent")

        result = payloads.build_payloads({"updated_at": "2026-09-27", "cards": [ready, other]})

        digest = result[1]["content"]
        self.assertIn("사용자 결정·승인 요청 1건.", digest)
        for text in ("질문: 운영 배포를 승인하나?", "이유: 배포는 사람 승인 대상이다",
                     "권장: 로컬 검증 결과로 stage 먼저", "근거: wiki/sample.md §검증 결과"):
            self.assertIn(text, digest)
        self.assertIn("AI 검토 대기 1건", digest)
        self.assertEqual([item["channel"] for item in result[2:]], ["agent-qa"])
        self.assertIn("Card: other", result[2]["content"])

    def test_profile_config_carries_human_request_contract(self) -> None:
        text = (MODULE_PATH.parents[1] / "configs" / "discord-agent-profiles.yaml").read_text(encoding="utf-8")
        for field in payloads.HUMAN_REQUEST_FIELDS:
            self.assertIn(f"      - {field}\n", text)
        self.assertIn("self_verification:", text)
        self.assertIn("never to the user automatically", text)
        self.assertIn("do not establish a human dependency", text)
        self.assertIn("never self-approved", text)
        self.assertNotIn("stay unresolved until the user answers", text)
        self.assertIn("do not canonical-promote", text)

    def test_apply_writes_hermes_dispatch_request_without_sending_to_discord(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "hermes-discord-dispatch-request.json"
            items = [{"channel": "agent-board", "content": "요약"}]

            messages = payloads.write_payloads(out, items, apply=True)

            self.assertEqual(messages, [f"wrote {out}"])
            stored = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(stored["target"], "hermes")
            self.assertEqual(stored["transport"], "hermes-existing-discord-bot")
            self.assertEqual(stored["dispatch_status"], "pending-hermes")
            self.assertRegex(stored["request_id"], r"^hdr-[0-9a-f]{16}$")
            self.assertRegex(stored["payloads"][0]["payload_id"], r"^hdp-[0-9a-f]{16}$")
            self.assertEqual(stored["payloads"][0]["channel"], items[0]["channel"])
            self.assertEqual(stored["payloads"][0]["content"], items[0]["content"])

    def test_render_payload_file_ids_are_stable_for_same_payloads(self) -> None:
        items = [{"channel": "agent-board", "content": "요약"}]

        first = payloads.render_payload_file(items)
        second = payloads.render_payload_file(items)

        self.assertEqual(first["request_id"], second["request_id"])
        self.assertEqual(first["payloads"][0]["payload_id"], second["payloads"][0]["payload_id"])

    def test_verification_contract_reaches_written_outbox(self) -> None:
        board = {"updated_at": "2026-09-14", "cards": [{
            "id": "sample", "work_id": "sample", "title": "격리 검토",
            "path": "wiki/sample.md", "suggested_roles": ["qa"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            batch = vault / "batch.json"
            payloads.write_payloads(batch, payloads.build_payloads(board), apply=True)
            command = [sys.executable, str(MODULE_PATH.with_name("export_hermes_discord_outbox.py")),
                       "--vault", str(vault), "--batch", str(batch), "--apply"]
            proc = subprocess.run(command, capture_output=True, text=True, check=True)
            manifest = json.loads(proc.stdout)
            item = next(x for x in manifest["items"] if x["channel"] == "agent-qa")
            content = json.loads((vault / item["path"]).read_text())["content"]
            self.assertIn("$TEAM2_HARNESS_PATH/docs/agents/verification.md", content)
            self.assertIn("before completion or handoff", content)
            self.assertTrue((MODULE_PATH.parents[1] / "docs/agents/verification.md").is_file())
            self.assertEqual(json.loads(batch.read_text())["dispatch_status"], "pending-hermes")


if __name__ == "__main__":
    unittest.main()
