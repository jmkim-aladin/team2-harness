from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


class CodexSkillTests(unittest.TestCase):
    def test_wiki_and_knowledge_base_terminology_is_explicit(self) -> None:
        policy = (ROOT / "policies/knowledge-base-policy.md").read_text()
        agents = (ROOT / "AGENTS.md").read_text()
        claude = (ROOT / "CLAUDE.md").read_text()
        harness_skill = (ROOT / ".codex/skills/dev2-team-harness-ko/SKILL.md").read_text()
        ralph_guide = (ROOT / "docs/ralph-loop-domain-knowledge-guide.md").read_text()

        for text in (policy, agents, claude, harness_skill):
            self.assertTrue('"위키"는' in text or "**위키**는" in text)
            self.assertIn("로컬 Obsidian", text)
            self.assertIn("기술자료", text)

        self.assertIn('"위키에 저장/올려줘"', policy)
        self.assertIn("로컬 위키 파일 작성으로 해석", policy)
        self.assertNotIn("YouTrack KB인지 Obsidian인지 모호", ralph_guide)

    def test_frequently_loaded_dev2_skills_stay_compact(self) -> None:
        limits = {
            ".codex/skills/dev2-team-harness-ko/SKILL.md": 300,
            # 매핑 목록 대신 memory/claude-base.md 생성 블록(작업 플로우 요약, 약 175단어)을 싣는다 — 2026-10-21 Codex 패리티
            ".codex/skills/dev2-ad-commands-ko/SKILL.md": 380,
            ".codex/skills/ad-work-prep/SKILL.md": 160,
        }

        for relative, limit in limits.items():
            text = (ROOT / relative).read_text()
            with self.subTest(skill=relative):
                self.assertLessEqual(word_count(text), limit)
                self.assertRegex(text, r'description: "(\[[^\]]+\] )?Use when')

    def test_dev2_skills_keep_non_negotiable_contracts(self) -> None:
        harness_skill = (ROOT / ".codex/skills/dev2-team-harness-ko/SKILL.md").read_text()
        ad_commands_skill = (ROOT / ".codex/skills/dev2-ad-commands-ko/SKILL.md").read_text()
        work_prep_skill = (ROOT / ".codex/skills/ad-work-prep/SKILL.md").read_text()

        for phrase in (
            "$TEAM2_HARNESS_PATH",
            "$LOCAL_WIKI_PATH",
            "YouTrack/KB/git",
            "DB/SP",
            "프로덕션 배포",
            "로컬 Obsidian vault",
        ):
            self.assertIn(phrase, harness_skill)

        self.assertIn("command 파일을 source of truth", ad_commands_skill)
        self.assertIn("토큰은 출력하지 않는다", ad_commands_skill)
        self.assertIn("위키 노트 생성·갱신·종료 반영", work_prep_skill)

    CLAUDE_TAG = re.compile(r"^description: '(\[[^\]]+\]) ", re.M)
    CODEX_TAG = re.compile(r'^description: "(\[[^\]]+\]) ', re.M)

    def test_codex_alias_parity_with_claude_commands(self) -> None:
        """`/ad:{name}` ↔ `$ad-{name}` 1:1, 메뉴 태그 `[그룹·단계]`도 같다 — 한쪽만 바뀌면 실패한다."""
        commands = {p.stem: p for p in (ROOT / ".claude/commands/ad").glob("*.md")}
        aliases = {p.name[3:]: p / "SKILL.md" for p in (ROOT / ".codex/skills").glob("ad-*") if p.is_dir()}
        self.assertTrue(commands)
        self.assertEqual(sorted(commands), sorted(aliases))
        for name, command in sorted(commands.items()):
            with self.subTest(skill=name):
                claude_tag = self.CLAUDE_TAG.search(command.read_text(encoding="utf-8"))
                codex_tag = self.CODEX_TAG.search(aliases[name].read_text(encoding="utf-8"))
                self.assertIsNotNone(claude_tag)
                self.assertIsNotNone(codex_tag)
                self.assertEqual(claude_tag.group(1), codex_tag.group(1))


if __name__ == "__main__":
    unittest.main()
