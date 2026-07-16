import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ArchitectureAnalysisSkillTest(unittest.TestCase):
    def test_command_defines_read_only_vault_and_html_contract(self):
        path = ROOT / ".claude/commands/ad/architecture-analysis.md"
        self.assertTrue(path.exists(), f"missing command: {path}")
        command = path.read_text(encoding="utf-8")

        for expected in (
            "/ad:architecture-analysis",
            "--static-only",
            "소스 파일을 생성·수정·삭제하지 않는다",
            "wiki/services/{service_id}/analysis/",
            "analysis/architecture-analysis-{YYYY-MM-DD}-{short_sha}.md",
            "render_architecture_report.py",
            "lint_vault.py",
            "문서를 자동으로 열지 않고 절대경로만 반환한다",
            "P0",
            "Clean·Hexagonal·DDD 평가",
        ):
            self.assertIn(expected, command)

    def test_codex_alias_loads_command_source_of_truth(self):
        skill_path = ROOT / ".codex/skills/ad-architecture-analysis/SKILL.md"
        metadata_path = ROOT / ".codex/skills/ad-architecture-analysis/agents/openai.yaml"
        self.assertTrue(skill_path.exists(), f"missing skill: {skill_path}")
        self.assertTrue(metadata_path.exists(), f"missing metadata: {metadata_path}")
        skill = skill_path.read_text(encoding="utf-8")
        metadata = metadata_path.read_text(encoding="utf-8")

        self.assertIn("name: ad-architecture-analysis", skill)
        self.assertIn("Use when", skill)
        self.assertIn(".claude/commands/ad/architecture-analysis.md", skill)
        self.assertIn('$ad-architecture-analysis', metadata)
        self.assertIn('display_name: "DEV2 아키텍처 분석"', metadata)

    def test_team2_routing_mentions_new_command(self):
        routing_files = (
            ROOT / ".codex/skills/dev2-ad-commands-ko/SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "scripts/setup.sh",
        )
        for path in routing_files:
            with self.subTest(path=path):
                self.assertIn("architecture-analysis", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
