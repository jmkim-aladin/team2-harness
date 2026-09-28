from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_decision_board.py"
spec = importlib.util.spec_from_file_location("generate_decision_board", MODULE_PATH)
board = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(board)


def write_note(vault: Path, rel_path: str, text: str) -> None:
    path = vault / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class GenerateDecisionBoardTests(unittest.TestCase):
    def test_collects_work_without_equating_review_with_human_intervention(self) -> None:
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
                        "related_services:",
                        "  - \"[[storefront]]\"",
                        "---",
                        "",
                        "## 결정 패킷",
                        "",
                        "- 추천: A안",
                        "",
                    ]
                ),
            )
            write_note(
                vault,
                "wiki/processes/tickets/dev2-1002.md",
                "\n".join(
                    [
                        "---",
                        "type: ticket",
                        "title: DEV2-1002 자체 진행 가능",
                        "ticket_id: DEV2-1002",
                        "ticket_status: in-progress",
                        "decision_status: none",
                        "service: \"[[max]]\"",
                        "---",
                        "",
                        "agent가 계속 진행한다.",
                        "",
                    ]
                ),
            )
            write_note(
                vault,
                "wiki/services/storefront/analysis/payment-impact.md",
                "\n".join(
                    [
                        "---",
                        "type: analysis",
                        "title: 결제 영향 분석",
                        "service_id: storefront",
                        "review_state: needs-review",
                        "evidence_level: E2",
                        "---",
                        "",
                        "검토 필요.",
                        "",
                    ]
                ),
            )
            write_note(
                vault,
                "wiki/projects/agentic-os/discord-orchestration-upgrade.md",
                "\n".join(
                    [
                        "---",
                        "type: project",
                        "title: Discord 오케스트레이션 고도화",
                        "canonical_id: project:agentic-os/discord-orchestration-upgrade",
                        "decision_status: approval-needed",
                        "---",
                        "",
                        "역할 프로필 적용 승인 필요.",
                        "",
                    ]
                ),
            )

            cards = board.collect_cards(vault)

        self.assertEqual([card["column"] for card in cards], ["Decision Needed", "Approval Needed", "Review Needed"])
        self.assertEqual(cards[0]["ticket_id"], "DEV2-1001")
        self.assertEqual(cards[0]["work_id"], "DEV2-1001")
        self.assertEqual(cards[0]["suggested_roles"], ["orchestrator", "planner"])
        self.assertEqual(cards[1]["ticket_id"], "")
        self.assertEqual(cards[1]["work_id"], "project:agentic-os/discord-orchestration-upgrade")
        self.assertEqual(cards[1]["suggested_roles"], ["orchestrator"])
        self.assertEqual(cards[2]["suggested_roles"], ["orchestrator", "qa"])
        self.assertEqual(cards[2]["service"], "[[storefront]]")
        self.assertTrue(all(card["attention"] == "agent" for card in cards))
        self.assertTrue(all(not card["human_request"] for card in cards))

    def test_only_explicit_complete_packet_routes_to_human(self) -> None:
        fm = {"attention": "human", "human_question": "부분 취소 시 이용권을 유지할까요?",
              "human_reason": "새 상품에 적용할 정책이 없다.", "human_recommendation": "유지",
              "human_evidence": "wiki/policy.md:12"}
        self.assertEqual(board.attention_fields(fm, "Decision Needed")["attention"], "human")
        for missing in fm:
            with self.subTest(missing=missing):
                incomplete = {key: value for key, value in fm.items() if key != missing}
                self.assertEqual(board.attention_fields(incomplete, "Decision Needed")["attention"], "agent")
        fm["human_reason"] = "  "
        self.assertEqual(board.attention_fields(fm, "Decision Needed")["attention"], "agent")

    def test_approval_without_packet_stays_pending_not_approved(self) -> None:
        result = board.attention_fields({"decision_status": "approval-needed"}, "Approval Needed")
        self.assertEqual(result["attention"], "agent")
        self.assertEqual(result["agent_task"]["kind"], "prepare-approval")
        self.assertIn("승인 전", result["agent_task"]["next_action"])

    def test_incomplete_human_packet_has_action_and_evidence_list_is_preserved(self) -> None:
        fm = {"attention": "human", "human_question": "선택?", "human_reason": ">",
              "human_recommendation": "보류", "human_evidence": ["wiki/a.md", "repo/b.py:10"]}
        incomplete = board.attention_fields(fm, "Decision Needed")
        self.assertEqual(incomplete["agent_task"]["kind"], "complete-human-request")
        self.assertIn("reason", incomplete["agent_task"]["missing_human_fields"])
        fm["human_reason"] = "정책 미확정"
        self.assertEqual(board.attention_fields(fm, "Decision Needed")["human_request"]["evidence"],
                         "wiki/a.md; repo/b.py:10")

    def test_malformed_human_card_stays_in_agent_details(self) -> None:
        card = {"id": "wiki/a.md", "path": "wiki/a.md", "work_id": "a", "title": "불완전 요청",
                "column": "Review Needed", "suggested_roles": ["qa"], "attention": "human", "human_request": {}}
        result = board.render_markdown([card], "2026-09-27")
        self.assertEqual(board.render_json([card], "2026-09-27")["human_requests"], 0)
        self.assertLess(result.index("<details>"), result.index("[[a|불완전 요청]]"))

    def test_summary_prefers_problem_to_extraction_metadata(self) -> None:
        self.assertEqual(board.note_summary("## 실행 근거\n- 추출: 2026-09-27\n## 판단\n- 문제: 응답이 누락된다."),
                         "문제: 응답이 누락된다.")

    def test_renders_markdown_and_json_projection(self) -> None:
        cards = [
            {
                "id": "wiki/processes/tickets/dev2-1001.md",
                "column": "Decision Needed",
                "title": "DEV2-1001 결제 정책 선택",
                "work_id": "DEV2-1001",
                "ticket_id": "DEV2-1001",
                "service": "[[storefront]]",
                "type": "ticket",
                "path": "wiki/processes/tickets/dev2-1001.md",
                "summary": "A안 추천",
                "suggested_roles": ["orchestrator", "planner"],
            }
        ]

        markdown = board.render_markdown(cards, "2026-06-17")
        payload = board.render_json(cards, "2026-06-17")

        self.assertIn("type: project", markdown)
        self.assertIn("<!-- generated:decision-board", markdown)
        self.assertIn("## Decision Needed", markdown)
        self.assertIn("[[dev2-1001|DEV2-1001]]", markdown)
        self.assertIn("작업: `DEV2-1001`", markdown)
        self.assertEqual(payload["updated_at"], "2026-06-17")
        self.assertEqual(payload["cards"][0]["suggested_roles"], ["orchestrator", "planner"])
        self.assertEqual(payload["human_requests"], 0)
        self.assertEqual(payload["agent_reviews"], 1)
        self.assertLess(markdown.index("<details>"), markdown.index("[[dev2-1001|DEV2-1001]]"))

    def test_ready_human_question_visible_and_review_details_collapsed(self) -> None:
        card = {"id": "wiki/a.md", "path": "wiki/a.md", "work_id": "a", "title": "정책",
                "column": "Decision Needed", "suggested_roles": ["orchestrator"],
                **board.attention_fields({"attention": "human", "human_question": "정책을 선택할까요?",
                                          "human_reason": "업무 기준 미확정", "human_recommendation": "기존 유지",
                                          "human_evidence": "wiki/policy.md"}, "Decision Needed")}
        result = board.render_markdown([card], "2026-09-27")
        self.assertLess(result.index("정책을 선택할까요?"), result.index("<details>"))
        self.assertIn("사람이 필요한 이유: 업무 기준 미확정", result)

    def test_apply_writes_default_projection_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            cards = [
                {
                    "id": "wiki/processes/tickets/dev2-1001.md",
                    "column": "Approval Needed",
                    "title": "DEV2-1001 PR 승인",
                    "work_id": "DEV2-1001",
                    "ticket_id": "DEV2-1001",
                    "service": "[[storefront]]",
                    "type": "ticket",
                    "path": "wiki/processes/tickets/dev2-1001.md",
                    "summary": "PR 생성 승인 필요",
                    "suggested_roles": ["orchestrator"],
                }
            ]

            result = board.write_projection(vault, cards, "2026-06-17", apply=True)

            markdown_path = vault / "wiki/projects/agentic-os/hermes-decision-board.md"
            json_path = vault / "wiki/projects/agentic-os/hermes-decision-board.json"
            self.assertEqual(result, ["wrote wiki/projects/agentic-os/hermes-decision-board.md", "wrote wiki/projects/agentic-os/hermes-decision-board.json"])
            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("Approval Needed", markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["cards"][0]["column"], "Approval Needed")


if __name__ == "__main__":
    unittest.main()
