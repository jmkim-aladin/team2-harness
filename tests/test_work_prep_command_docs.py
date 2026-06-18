import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkPrepCommandDocsTests(unittest.TestCase):
    def test_work_prep_command_stays_below_500_lines(self) -> None:
        command = ROOT / ".claude/commands/ad/work-prep.md"
        line_count = len(command.read_text(encoding="utf-8").splitlines())
        self.assertLess(line_count, 500)

    def test_work_prep_command_points_to_detail_template(self) -> None:
        command = ROOT / ".claude/commands/ad/work-prep.md"
        template = ROOT / "docs/sprint/work-prep-note-template.md"
        text = command.read_text(encoding="utf-8")

        self.assertTrue(template.exists())
        self.assertIn("docs/sprint/work-prep-note-template.md", text)
        self.assertIn("decision_status", template.read_text(encoding="utf-8"))

    def test_work_prep_command_requires_common_service_impact_check(self) -> None:
        command = ROOT / ".claude/commands/ad/work-prep.md"
        text = command.read_text(encoding="utf-8")

        self.assertIn("policies/common-service-policy.md", text)
        self.assertIn("catalog/common-services/registry.yaml", text)
        self.assertIn("공통 서비스 영향", text)


if __name__ == "__main__":
    unittest.main()
