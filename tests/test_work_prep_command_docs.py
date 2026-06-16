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


if __name__ == "__main__":
    unittest.main()
