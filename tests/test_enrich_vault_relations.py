from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "enrich_vault_relations.py"
spec = importlib.util.spec_from_file_location("enrich_vault_relations", MODULE_PATH)
relations = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(relations)


class EnrichVaultRelationsTests(unittest.TestCase):
    def test_ticket_service_and_body_ticket_are_promoted_to_relations(self) -> None:
        text = "\n".join(
            [
                "---",
                "type: ticket",
                "title: DEV2-6217 북플 처리",
                "ticket_id: DEV2-6217",
                "service: \"[[blog]]\"",
                "---",
                "",
                "# DEV2-6217",
                "",
                "관련 후속 티켓은 DEV2-6669 이다.",
                "",
            ]
        )

        enriched = relations.enrich_markdown(
            text,
            "wiki/processes/tickets/dev2-6217.md",
            ticket_services={},
            meeting_services={},
            service_keywords=relations.DEFAULT_SERVICE_KEYWORDS,
        )

        self.assertTrue(enriched.changed)
        self.assertIn("related_services:\n  - \"[[blog]]\"", enriched.text)
        self.assertIn("related_tickets:\n  - \"[[dev2-6669]]\"", enriched.text)
        self.assertNotIn("[[dev2-6217]]", relations.get_frontmatter_values(enriched.text, "related_tickets"))
        self.assertIn("relation_status: inferred", enriched.text)
        self.assertIn('  - "auto-backfill"', enriched.text)

    def test_okr_uses_ticket_service_map(self) -> None:
        text = "\n".join(
            [
                "---",
                "type: okr",
                "title: 김정민 2026 Q2",
                "year: 2026",
                "quarter: 2",
                "scope: personal",
                "---",
                "",
                "KR 근거: DEV2-6217, DEV2-5283",
                "",
            ]
        )

        enriched = relations.enrich_markdown(
            text,
            "wiki/processes/okr/2026-q2-kimjeongmin.md",
            ticket_services={
                "DEV2-6217": {"[[blog]]"},
                "DEV2-5283": {"[[storefront]]"},
            },
            meeting_services={},
            service_keywords=relations.DEFAULT_SERVICE_KEYWORDS,
        )

        self.assertIn("related_tickets:\n  - \"[[dev2-5283]]\"\n  - \"[[dev2-6217]]\"", enriched.text)
        self.assertIn("related_services:\n  - \"[[blog]]\"\n  - \"[[storefront]]\"", enriched.text)

    def test_daily_links_meetings_and_inherits_meeting_services(self) -> None:
        text = "\n".join(
            [
                "---",
                "type: daily",
                "date: 2026-06-05",
                "---",
                "",
                "## 오늘의 아젠다",
                "",
                "- [ ] [[dev2-6217|DEV2-6217]]",
                "",
                "## 회의",
                "",
                "- [[2026-06-05-order-and-payment-process-review|주문/결제 프로세스 검토]]",
                "",
            ]
        )

        enriched = relations.enrich_markdown(
            text,
            "wiki/processes/daily/2026-06-05.md",
            ticket_services={"DEV2-6217": {"[[blog]]"}},
            meeting_services={
                "2026-06-05-order-and-payment-process-review": {"[[storefront]]"}
            },
            service_keywords=relations.DEFAULT_SERVICE_KEYWORDS,
        )

        self.assertIn("related_tickets:\n  - \"[[dev2-6217]]\"", enriched.text)
        self.assertIn(
            "related_meetings:\n  - \"[[2026-06-05-order-and-payment-process-review]]\"",
            enriched.text,
        )
        self.assertIn("related_services:\n  - \"[[blog]]\"\n  - \"[[storefront]]\"", enriched.text)

    def test_existing_confirmed_relation_status_is_preserved(self) -> None:
        text = "\n".join(
            [
                "---",
                "type: ticket",
                "ticket_id: DEV2-6217",
                "service: \"[[blog]]\"",
                "relation_status: confirmed",
                "---",
                "",
                "후속 DEV2-6669",
                "",
            ]
        )

        enriched = relations.enrich_markdown(
            text,
            "wiki/processes/tickets/dev2-6217.md",
            ticket_services={},
            meeting_services={},
            service_keywords=relations.DEFAULT_SERVICE_KEYWORDS,
        )

        self.assertIn("relation_status: confirmed", enriched.text)
        self.assertNotIn("relation_status: inferred", enriched.text)

    def test_apply_updates_existing_notes_in_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            ticket = vault / "wiki/processes/tickets/dev2-6217.md"
            ticket.parent.mkdir(parents=True)
            ticket.write_text(
                "\n".join(
                    [
                        "---",
                        "type: ticket",
                        "ticket_id: DEV2-6217",
                        "service: \"[[blog]]\"",
                        "---",
                        "",
                        "후속 DEV2-6669",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            messages = relations.enrich_vault(vault, apply=True)

            self.assertEqual(messages[0], "updated wiki/processes/tickets/dev2-6217.md")
            self.assertIn("related_services:", ticket.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
