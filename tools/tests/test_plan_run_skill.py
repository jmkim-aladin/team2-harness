import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PlanRunSkillTest(unittest.TestCase):
    def test_command_defines_internal_milestone_execution_contract(self):
        path = ROOT / ".claude/commands/ad/plan-run.md"
        self.assertTrue(path.exists(), f"missing command: {path}")
        command = path.read_text(encoding="utf-8")

        for expected in (
            "/ad:plan-run",
            "disable-model-invocation: true",
            "milestone 하나",
            "planned",
            "in-progress",
            "completed",
            "blocked",
            "execution_mode",
            "execution_ref",
            "evidence",
            "CHG-*",
            "catalog/{service_id}.yaml",
            "vendor/mattpocock/implement/SKILL.md",
            "커밋 전 사용자 확인",
        ):
            self.assertIn(expected, command)

    def test_codex_alias_loads_command_source_of_truth(self):
        skill_path = ROOT / ".codex/skills/ad-plan-run/SKILL.md"
        metadata_path = ROOT / ".codex/skills/ad-plan-run/agents/openai.yaml"
        self.assertTrue(skill_path.exists(), f"missing skill: {skill_path}")
        self.assertTrue(metadata_path.exists(), f"missing metadata: {metadata_path}")
        skill = skill_path.read_text(encoding="utf-8")
        metadata = metadata_path.read_text(encoding="utf-8")

        self.assertIn("name: ad-plan-run", skill)
        self.assertIn("Use when", skill)
        self.assertIn(".claude/commands/ad/plan-run.md", skill)
        self.assertIn("$ad-plan-run", metadata)
        self.assertIn('display_name: "DEV2 계획 실행"', metadata)
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_plan_and_routing_expose_internal_execution_path(self):
        expected_by_path = {
            ROOT / ".claude/commands/ad/plan.md": (
                "단계 현황",
                "execution_mode",
                "execution_ref",
                "/ad:plan-run",
            ),
            ROOT / ".codex/skills/dev2-ad-commands-ko/SKILL.md": ("plan-run",),
            ROOT / "AGENTS.md": ("ad-plan-run", "사용자 호출 전용 6종"),
            ROOT / "CLAUDE.md": ("ad:plan-run", "사용자 호출 전용 6종"),
            ROOT / "docs/harness-guide.md": ("/ad:plan-run", "internal milestone"),
            ROOT / "skills/README.md": ("ad:plan-run",),
        }

        for path, phrases in expected_by_path.items():
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in phrases:
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
