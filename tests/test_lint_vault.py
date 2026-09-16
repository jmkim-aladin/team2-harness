import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.lint_vault import lint_file, parse_frontmatter


class ParseFrontmatterTest(unittest.TestCase):
    def test_nested_resource_type_does_not_override_document_type(self):
        text = """---
type: analysis
service_id: storefront
resources:
  - path: ./assets/source.html
    type: html
    role: source
---

# Sample
"""

        fm = parse_frontmatter(text)

        self.assertIsNotNone(fm)
        self.assertEqual(fm["type"], "analysis")
        self.assertEqual(fm["service_id"], "storefront")

    def test_service_design_note_is_valid_under_proposals(self):
        text = """---
type: design
service_id: aasm
status: draft
---

# AASM design
"""

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "wiki/services/aasm/proposals/cross-network-release-share-common-base-design.md"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")

            violations = lint_file(
                "wiki/services/aasm/proposals/cross-network-release-share-common-base-design.md",
                path,
            )

        self.assertEqual(violations, [])


class TicketFilenameTest(unittest.TestCase):
    def lint_ticket(self, filename, ticket_id):
        rel = f"wiki/processes/tickets/{filename}"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / rel
            path.parent.mkdir(parents=True)
            path.write_text(
                f"---\ntype: ticket\nticket_id: {ticket_id}\n"
                "ticket_status: in-progress\nassignee: jmkim\n"
                "service: max\nsprint: 2026-09\n---\n\n# Ticket\n",
                encoding="utf-8",
            )
            return lint_file(rel, path)

    def test_ticket_notes_allow_other_project_ids(self):
        for ticket_id in ("DEV1-10525", "DEV1-8246", "DEV2-9253"):
            with self.subTest(ticket_id=ticket_id):
                self.assertEqual(self.lint_ticket(f"{ticket_id.lower()}.md", ticket_id), [])

    def test_ticket_filename_still_requires_lowercase_project_and_number(self):
        for filename in ("DEV1-10525.md", "dev1-abc.md", "10525.md", "dev1-10525-draft.md"):
            with self.subTest(filename=filename):
                violations = self.lint_ticket(filename, "DEV1-10525")
                self.assertTrue(any("파일명 패턴 위반" in v for v in violations))


if __name__ == "__main__":
    unittest.main()
