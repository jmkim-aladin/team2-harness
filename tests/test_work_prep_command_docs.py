import re
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

    def test_work_prep_judges_strength_and_names_next_verb(self) -> None:
        text = (ROOT / ".claude/commands/ad/work-prep.md").read_text(encoding="utf-8")

        self.assertIn("개발 연결", text)
        self.assertIn("## 구현 계획", text)
        self.assertIn("docs/harness-guide.md", text)
        for verb in ("/ad:eng-review", "/ad:implement", "/ad:code-review-self"):
            self.assertIn(verb, text)


class ImplementationPlanContractTests(unittest.TestCase):
    """work-prep이 쓰고 implement·eng-review·work-close가 읽는 `## 구현 계획` 계약."""

    PLAN_KEYS = ("강도:", "완료 조건", "검증 명령", "경계:", "슬라이스", "구현 중 신호")

    def test_template_sot_defines_plan_below_first_screen_summary(self) -> None:
        text = (ROOT / "docs/sprint/work-prep-note-template.md").read_text(encoding="utf-8")
        body = text[text.index("## 본문 템플릿"):text.index("## 구현 계획 기준")]

        self.assertIn("## 구현 계획 기준", text)
        self.assertIn("## 진행 메모", body)
        self.assertLess(body.index("## 판단 요약"), body.index("## 구현 계획"))
        plan = body[body.index("## 구현 계획"):body.index("## 진행 메모")]
        for key in self.PLAN_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, plan)

    def test_vault_skeleton_carries_plan_section(self) -> None:
        text = (ROOT / "templates/vault-notes/ticket.md").read_text(encoding="utf-8")
        plan = text[text.index("## 구현 계획"):text.index("## 검증 SQL")]
        for key in self.PLAN_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, plan)

    def test_plan_readers_point_to_template_sot(self) -> None:
        for relative in (
            ".claude/commands/ad/implement.md",
            ".claude/commands/ad/eng-review.md",
            ".claude/commands/ad/work-close.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(command=relative):
                self.assertIn("## 구현 계획", text)
                self.assertIn("work-prep-note-template.md", text)

    def test_implement_runs_one_slice_and_keeps_commit_gate(self) -> None:
        text = (ROOT / ".claude/commands/ad/implement.md").read_text(encoding="utf-8")

        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("슬라이스 하나", text)
        self.assertIn("멈춘다", text)
        self.assertIn("사용자 확인", text)


class DevFlowMapNamingTests(unittest.TestCase):
    """harness-guide §작업 플로우가 강도·보조 장치 명칭의 SoT다 — 소유 문서는 같은 이름을 쓴다."""

    GUIDE = ROOT / "docs/harness-guide.md"
    NAMING_FILES = (
        ".claude/commands/ad/work-prep.md",
        ".claude/commands/ad/implement.md",
        ".claude/commands/ad/eng-review.md",
        ".claude/commands/ad/work-close.md",
        ".claude/commands/ad/code-review.md",
        ".claude/commands/ad/code-review-self.md",
        "policies/code-review-policy.md",
        "docs/code-review/personas.md",
        "docs/code-review/cross-model.md",
        "docs/sprint/work-prep-note-template.md",
        "templates/vault-notes/ticket.md",
        "memory/claude-base.md",
        "docs/harness-guide.md",
        "docs/eng-review/review-sections.md",
        "docs/eng-review/doubt-review.md",
        "README.md",
    )
    FORBIDDEN_SYNONYMS = (
        "신호 카드", "수락 기준", "인수 조건", "doubt-driven", "의심 검토",
        "핵심 가정 실행 입증", "게이트 완화 감지", "floor guard", "결정 지도", "안개 지도",
        "강도 레벨", "강도 등급", "교차 모델 검증", "교차검증",
    )

    def test_map_has_four_groups_strength_and_name_table(self) -> None:
        text = self.GUIDE.read_text(encoding="utf-8")
        flow = text[text.index("## 작업 플로우"):text.index("## 실제 작업 흐름")]

        for heading in ("### 4그룹 요약", "### 1. 구상 (티켓 전)", "### 2. 개발 (티켓 하나)",
                        "### 3. 주기 (팀 운영)", "### 4. 상시 (언제든)",
                        "#### 강도 (ceremony level)", "#### 단계별 도구 명칭"):
            with self.subTest(heading=heading):
                self.assertIn(heading, flow)
        for level in ("| 가벼움 |", "| 보통 |", "| 무거움 |", "| 위험 |"):
            with self.subTest(level=level):
                self.assertIn(level, flow)

    GROUP_SECTIONS = {
        "구상": ("### 1. 구상", "### 2. 개발"),
        "개발": ("### 2. 개발", "### 3. 주기"),
        "주기": ("### 3. 주기", "### 4. 상시"),
        "상시": ("### 4. 상시", "### 단계 경계"),
    }
    DESCRIPTION_TAG = re.compile(r"^description: '\[(구상|개발|주기|상시)·[^\]]+\] ")
    MAP_REFERENCE = re.compile(r"→[^|→]*?\(주 소속:[^)]*\)")

    def test_command_description_tag_names_its_map_group(self) -> None:
        """description 앞 `[그룹·단계]` 태그는 지도 주 소속의 사본 — 태그 그룹 절에 `(주 소속: …)` 참조 말고도 등장해야 한다."""
        guide = self.GUIDE.read_text(encoding="utf-8")
        commands = sorted((ROOT / ".claude/commands/ad").glob("*.md"))
        self.assertTrue(commands)
        for command in commands:
            line = command.read_text(encoding="utf-8").splitlines()[1]
            with self.subTest(command=command.stem):
                match = self.DESCRIPTION_TAG.match(line)
                self.assertIsNotNone(match, line)
                start, end = self.GROUP_SECTIONS[match.group(1)]
                section = self.MAP_REFERENCE.sub("", guide[guide.index(start):guide.index(end)])
                self.assertRegex(section, rf"/ad:{re.escape(command.stem)}(?![\w-])")

    def test_map_verbs_exist_as_commands(self) -> None:
        """지도에 남은 `/ad:*`는 모두 command 파일이 있어야 한다 — 스킬을 지우고 지도를 안 고치면 지도가 거짓말을 한다."""
        guide = self.GUIDE.read_text(encoding="utf-8")
        flow = guide[guide.index("## 작업 플로우"):guide.index("## 실제 작업 흐름")]
        commands = {p.stem for p in (ROOT / ".claude/commands/ad").glob("*.md")}
        # 한 글자(`/ad:x`)는 표기 규칙 설명의 자리표시자다
        for verb in sorted(set(re.findall(r"/ad:([a-z0-9]{2,}(?:-[a-z0-9]+)*)", flow))):
            with self.subTest(verb=verb):
                self.assertIn(verb, commands)

    def test_owned_docs_use_canonical_names(self) -> None:
        for relative in self.NAMING_FILES:
            lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
            text = "\n".join(line for line in lines if not line.startswith("금지 동의어"))
            for word in self.FORBIDDEN_SYNONYMS:
                with self.subTest(file=relative, word=word):
                    self.assertNotIn(word, text)


class ReadmeSkillReferenceTests(unittest.TestCase):
    """README §스킬 레퍼런스는 사람이 쓰는 사본이다 — command 집합·그룹 태그·호출 방식과 어긋나면 실패한다.

    SoT는 `.claude/commands/ad/*.md` frontmatter(description `[그룹·단계]` 태그, `disable-model-invocation`).
    스킬을 추가·삭제·이동하고 README를 안 고치면 정문이 거짓말을 한다.
    """

    README = ROOT / "README.md"
    GROUP_HEADING = re.compile(r"^### (구상|개발|주기|상시) ")
    ROW = re.compile(r"^\| `/ad:([a-z0-9-]+)` \|.*\| (모델|사용자) \|$")
    VERB = re.compile(r"/ad:([a-z0-9]{2,}(?:-[a-z0-9]+)*)")
    CODEX_ALIAS = re.compile(r"\$ad-([a-z0-9]{2,}(?:-[a-z0-9]+)*)")

    def reference_rows(self) -> dict:
        text = self.README.read_text(encoding="utf-8")
        section = text[text.index("## 스킬 레퍼런스"):]
        section = section[:section.index("\n## ", 1)]
        rows, group = {}, None
        for line in section.splitlines():
            heading = self.GROUP_HEADING.match(line)
            if heading:
                group = heading.group(1)
                continue
            row = self.ROW.match(line)
            if row:
                self.assertNotIn(row.group(1), rows, f"README 표에 /ad:{row.group(1)} 행이 두 번")
                rows[row.group(1)] = (group, row.group(2))
        return rows

    def commands(self) -> dict:
        out = {}
        for path in sorted((ROOT / ".claude/commands/ad").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            tag = DevFlowMapNamingTests.DESCRIPTION_TAG.match(text.splitlines()[1])
            head = text.split("---")[1]
            user_only = re.search(r"^disable-model-invocation:\s*true\s*$", head, re.M)
            out[path.stem] = (tag.group(1) if tag else None, "사용자" if user_only else "모델")
        return out

    def test_reference_lists_every_command_once(self) -> None:
        commands, rows = self.commands(), self.reference_rows()
        self.assertTrue(commands)
        self.assertEqual(sorted(rows), sorted(commands))

    def test_reference_group_and_invocation_match_frontmatter(self) -> None:
        rows = self.reference_rows()
        for name, expected in self.commands().items():
            with self.subTest(command=name):
                self.assertEqual(rows.get(name), expected)

    def test_readme_names_only_existing_skills(self) -> None:
        """표 밖(다이어그램·본문)의 `/ad:*`·`$ad-*`도 실재해야 한다 — 지운 스킬이 정문에 남지 않게."""
        text = self.README.read_text(encoding="utf-8")
        commands = {p.stem for p in (ROOT / ".claude/commands/ad").glob("*.md")}
        aliases = {p.name[len("ad-"):] for p in (ROOT / ".codex/skills").glob("ad-*") if p.is_dir()}
        for verb in sorted(set(self.VERB.findall(text))):
            with self.subTest(verb=f"/ad:{verb}"):
                self.assertIn(verb, commands)
        for alias in sorted(set(self.CODEX_ALIAS.findall(text))):
            with self.subTest(alias=f"$ad-{alias}"):
                self.assertIn(alias, aliases)


if __name__ == "__main__":
    unittest.main()
