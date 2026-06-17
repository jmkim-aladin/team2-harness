from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


class CodexSkillTests(unittest.TestCase):
    def test_frequently_loaded_dev2_skills_stay_compact(self) -> None:
        limits = {
            ".codex/skills/dev2-team-harness-ko/SKILL.md": 300,
            ".codex/skills/dev2-ad-commands-ko/SKILL.md": 320,
            ".codex/skills/ad-work-prep/SKILL.md": 160,
            ".codex/skills/ad-work-board/SKILL.md": 140,
        }

        for relative, limit in limits.items():
            text = (ROOT / relative).read_text()
            with self.subTest(skill=relative):
                self.assertLessEqual(word_count(text), limit)
                self.assertIn("description: \"Use when", text)

    def test_dev2_skills_keep_non_negotiable_contracts(self) -> None:
        harness_skill = (ROOT / ".codex/skills/dev2-team-harness-ko/SKILL.md").read_text()
        ad_commands_skill = (ROOT / ".codex/skills/dev2-ad-commands-ko/SKILL.md").read_text()
        work_prep_skill = (ROOT / ".codex/skills/ad-work-prep/SKILL.md").read_text()
        work_board_skill = (ROOT / ".codex/skills/ad-work-board/SKILL.md").read_text()

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
        self.assertIn("Discord API, webhook, bot token은 직접 사용하지 않는다", work_board_skill)


if __name__ == "__main__":
    unittest.main()
