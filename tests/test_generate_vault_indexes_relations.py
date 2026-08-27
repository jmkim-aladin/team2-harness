from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_vault_indexes.py"
spec = importlib.util.spec_from_file_location("generate_vault_indexes", MODULE_PATH)
indexes = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(indexes)


class GenerateVaultIndexRelationsTests(unittest.TestCase):
    def test_service_index_uses_human_readable_korean_title(self) -> None:
        text = indexes.new_service_index("storefront", "<!-- generated:vault-index -->\n<!-- /generated -->")

        self.assertIn("title: 스토어프론트", text)
        self.assertIn("# 스토어프론트", text)
        self.assertIn("service_id: storefront", text)

    def test_existing_service_title_is_normalized_without_renaming_file_identity(self) -> None:
        text = "\n".join(
            [
                "---",
                "type: service",
                "title: storefront",
                "service_id: storefront",
                "---",
                "",
                "# storefront",
                "",
            ]
        )

        normalized, changed = indexes.normalize_service_title(text, "storefront")

        self.assertTrue(changed)
        self.assertIn("title: 스토어프론트", normalized)
        self.assertIn("# 스토어프론트", normalized)
        self.assertIn("service_id: storefront", normalized)

    def test_service_related_notes_block_collects_relation_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            service = vault / "wiki/services/storefront/storefront.md"
            ticket = vault / "wiki/processes/tickets/dev2-5283.md"
            meeting = vault / "wiki/processes/meetings/2026-06-05-order.md"
            okr = vault / "wiki/processes/okr/2026-q2-kimjeongmin.md"
            for path in [service, ticket, meeting, okr]:
                path.parent.mkdir(parents=True, exist_ok=True)
            service.write_text("---\ntype: service\nservice_id: storefront\n---\n", encoding="utf-8")
            ticket.write_text(
                "---\ntype: ticket\ntitle: DEV2-5283 설계\nticket_id: DEV2-5283\nservice: \"[[storefront]]\"\n---\n",
                encoding="utf-8",
            )
            meeting.write_text(
                "---\ntype: meeting\ntitle: 주문 회의\nrelated_services:\n  - \"[[storefront]]\"\n---\n",
                encoding="utf-8",
            )
            okr.write_text(
                "---\ntype: okr\ntitle: Q2 OKR\nrelated_services:\n  - \"[[storefront]]\"\n---\n",
                encoding="utf-8",
            )

            block = indexes.render_service_related_notes_block(vault, "storefront")

            self.assertIn("<!-- generated:related-notes", block)
            self.assertIn("## 관련 티켓", block)
            self.assertIn("[[dev2-5283|DEV2-5283 설계]]", block)
            self.assertIn("## 관련 회의", block)
            self.assertIn("[[2026-06-05-order|주문 회의]]", block)
            self.assertIn("## 관련 OKR", block)
            self.assertIn("[[2026-q2-kimjeongmin|Q2 OKR]]", block)

    def test_duplicate_note_stems_use_vault_relative_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            first = vault / "wiki/services/blog/analysis/query-cache-sp-candidates.md"
            second = vault / "wiki/services/shopping/analysis/query-cache-sp-candidates.md"
            for path, service in [(first, "blog"), (second, "shopping")]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "---\n"
                    "type: analysis\n"
                    f"title: {service} 후보\n"
                    f"service_id: {service}\n"
                    "---\n",
                    encoding="utf-8",
                )

            block = indexes.render_service_related_notes_block(vault, "blog")

            self.assertIn(
                "[[wiki/services/blog/analysis/query-cache-sp-candidates|blog 후보]]",
                block,
            )
            self.assertNotIn("[[query-cache-sp-candidates|blog 후보]]", block)

            index_block = indexes.render_service_index_block(vault, "blog")
            self.assertIn(
                "[[wiki/services/blog/analysis/query-cache-sp-candidates]]",
                index_block,
            )
            self.assertNotIn("- [[query-cache-sp-candidates]]", index_block)

    def test_root_note_collision_qualifies_generated_service_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            service_note = vault / "wiki/services/blog/analysis/runbook.md"
            root_note = vault / "templates/runbook.md"
            service_note.parent.mkdir(parents=True, exist_ok=True)
            root_note.parent.mkdir(parents=True, exist_ok=True)
            service_note.write_text(
                "---\ntype: analysis\ntitle: Blog runbook\nservice_id: blog\n---\n",
                encoding="utf-8",
            )
            root_note.write_text("# Template runbook\n", encoding="utf-8")

            index_block = indexes.render_service_index_block(vault, "blog")

            self.assertIn("[[wiki/services/blog/analysis/runbook]]", index_block)
            self.assertNotIn("- [[runbook]]", index_block)

    def test_root_note_collision_qualifies_generated_process_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            process_note = vault / "wiki/processes/tickets/dev2-5855.md"
            root_note = vault / "dev2-5855.md"
            process_note.parent.mkdir(parents=True, exist_ok=True)
            process_note.write_text("# Ticket\n", encoding="utf-8")
            root_note.write_text("# Legacy ticket\n", encoding="utf-8")

            index_block = indexes.render_process_index_block(vault, "tickets")

            self.assertIn("[[wiki/processes/tickets/dev2-5855]]", index_block)
            self.assertNotIn("- [[dev2-5855]]", index_block)

    def test_root_note_collision_qualifies_generated_hub_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            service_index = vault / "wiki/services/blog/blog.md"
            root_note = vault / "templates/blog.md"
            service_index.parent.mkdir(parents=True, exist_ok=True)
            root_note.parent.mkdir(parents=True, exist_ok=True)
            service_index.write_text("# Blog\n", encoding="utf-8")
            root_note.write_text("# Blog template\n", encoding="utf-8")

            index_block = indexes.render_hub_index_block(vault, "services")

            self.assertIn("[[wiki/services/blog/blog|blog]]", index_block)
            self.assertNotIn("- [[blog|blog]]", index_block)

    def test_non_wiki_relation_note_is_not_projected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            wiki_note = vault / "wiki/services/blog/analysis/real-note.md"
            template_note = vault / "templates/template-ticket.md"
            wiki_note.parent.mkdir(parents=True, exist_ok=True)
            template_note.parent.mkdir(parents=True, exist_ok=True)
            wiki_note.write_text(
                "---\ntype: analysis\ntitle: Real note\nservice_id: blog\n---\n",
                encoding="utf-8",
            )
            template_note.write_text(
                "---\ntype: ticket\ntitle: Template ticket\nservice_id: blog\n---\n",
                encoding="utf-8",
            )

            block = indexes.render_service_related_notes_block(vault, "blog")

            self.assertIn("[[real-note|Real note]]", block)
            self.assertNotIn("Template ticket", block)


if __name__ == "__main__":
    unittest.main()
