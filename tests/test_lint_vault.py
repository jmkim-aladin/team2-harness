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


if __name__ == "__main__":
    unittest.main()
