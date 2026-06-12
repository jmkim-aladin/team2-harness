import unittest

from tools.lint_vault import parse_frontmatter


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


if __name__ == "__main__":
    unittest.main()
