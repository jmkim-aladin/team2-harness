"""lint_harness_rules 단위 테스트 — tempdir fixture 만 쓴다.

실제 repo 상태에 의존하는 검사는 tests/test_lint_harness_rules_smoke.py 에 있다.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/lint_harness_rules.py"
spec = importlib.util.spec_from_file_location("lint_harness_rules", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FENCE = "```"


def write(root: Path, name: str, lines) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def lint(root: Path, baseline=None):
    md, yamls = module.collect_targets(str(root), [str(root)])
    return module.scan(str(root), md, yamls, baseline)


def by_rule(found, rule, path=None):
    return [f for f in found if f["rule"] == rule and (path is None or f["path"] == path)]


class ReasonRuleTests(unittest.TestCase):
    """R1a — 하드룰에 근거 단서가 붙었는지."""

    def test_same_heading_prose_is_reason_but_sibling_rule_is_not(self):
        """절의 설명 문단은 그 절 규칙들의 이유다. 형제 규칙 항목에 있는 이유로는 면책되지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "policies/a.md", ["# a", "", "## 절", "",
                  "범위를 넘긴 리뷰는 작성자 시간을 쓰게 만들기 때문에 아래를 지킨다.", "",
                  "- diff 밖 파일은 지적하지 않는다", "- 확대해석 금지"])
            write(root, "policies/b.md", ["# b", "", "## 절", "",
                  "- 첫 규칙은 이유가 있다 — 되돌릴 수 없기 때문이다", "- 둘째 규칙은 금지다"])
            found = lint(root)
            self.assertEqual(by_rule(found, "R1a", "policies/a.md"), [])
            self.assertEqual(len(by_rule(found, "R1a", "policies/b.md")), 1)

    def test_size_rule_counts_tokens_not_bytes(self):
        """같은 바이트라도 한국어는 토큰이 3배 — 한도는 추정 토큰으로 본다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "policies/ko.md", ["# ko", "", "가" * 4500])          # ≈4500 tok > 4000
            write(root, "policies/en.md", ["# en", "", "a" * 13500])          # 13.5KB but ≈3375 tok
            found = lint(root)
            self.assertEqual(len(by_rule(found, "R5", "policies/ko.md")), 1)
            self.assertEqual(by_rule(found, "R5", "policies/en.md"), [])

    def test_korean_causal_ending_counts_as_reason(self):
        """'~이므로'·'~라서'는 이유 표현이다 — 없다고 보면 잘 쓴 규칙이 부채로 잡힌다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "policies/p.md", ["# p", "", "## 절", "",
                  "- Draft PR은 리뷰하지 않는다. 작성자가 아직 완료 신호를 주지 않은 상태이므로 diff를 읽지 않는다",
                  "- 게시 전 사용자 확인은 필수다. 되돌릴 수 없는 외부 행동이라서 그렇다"])
            self.assertEqual(by_rule(lint(root), "R1a", "policies/p.md"), [])

    def test_reason_presence_decides_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "ok.md", [
                "# 문서", "", "## 커밋 게이트", "",
                "- 커밋 전 사용자에게 반드시 확인한다 — 근거: 2026-01-01 강제 푸시 사고",
            ])
            write(root, "bad.md", [
                "# 문서", "", "## 배포 절차", "",
                "- 배포 전 체크리스트를 반드시 채운다",
            ])
            write(root, "ancestor.md", [
                "# 문서", "", "## 승인 게이트", "",
                "근거: 2026-01-01 무단 머지 사고.", "",
                "### 하위 절", "",
                "- 승인 없이 머지 금지",
            ])
            write(root, "sibling.md", [
                "# 문서", "", "## 스키마", "",
                "### 규칙 절", "",
                "- 스키마 변경은 반드시 승인받는다", "",
                "### 설명 절", "",
                "근거: 2026-01-01 장애.",
            ])
            found = lint(root)
            self.assertEqual(len(by_rule(found, "R1a", "ok.md")), 0)
            self.assertEqual(len(by_rule(found, "R1a", "bad.md")), 1)
            self.assertEqual(len(by_rule(found, "R1a", "ancestor.md")), 0)
            self.assertEqual(len(by_rule(found, "R1a", "sibling.md")), 1,
                             "형제 heading 의 근거로는 면책하지 않는다")

    def test_ancestor_needs_explicit_marker_not_em_dash(self):
        """조상 preamble 은 `근거:|의도:|이유:` 만 인정한다 — em dash 서술은 하위 하드룰을 못 덮는다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "loose.md", [
                "# 문서", "", "## 조상 절", "",
                "기본 순서다 — 조정 가능", "",
                "### 하위 절", "",
                "- 배포 전 체크리스트를 반드시 채운다",
            ])
            write(root, "marked.md", [
                "# 문서", "", "## 조상 절", "",
                "근거: 2026-01-01 배포 누락", "",
                "### 하위 절", "",
                "- 배포 전 체크리스트를 반드시 채운다",
            ])
            found = lint(root)
            self.assertEqual(len(by_rule(found, "R1a", "loose.md")), 1)
            self.assertEqual(by_rule(found, "R1a", "marked.md"), [])

    def test_fenced_code_and_frontmatter_are_out_of_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "code.md", [
                "---", "title: 반드시 지켜라", "---", "",
                "# 예제", "",
                FENCE, "- 배포는 반드시 수동으로 한다", FENCE,
            ])
            found = lint(root)
            self.assertEqual(by_rule(found, "R1a", "code.md"), [])
            self.assertEqual(by_rule(found, "R3", "code.md"), [])


class ModelOverlapTests(unittest.TestCase):
    """R2 — 모델 내장 행동 재지시. 규약 설명문(NEGATED)은 제외."""

    def test_directive_hits_but_convention_text_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "r2.md", [
                "# 지시", "",
                "- 작업이 끝나면 결과를 다시 확인하라",
                '- 사고 과정 재지시는 넣지 않는다 — "단계별로 생각하라" 같은 문장은 삭제한다',
            ])
            hits = by_rule(lint(root), "R2", "r2.md")
            self.assertEqual(len(hits), 1)
            self.assertIn("다시 확인", hits[0]["excerpt"])


class EmphasisTests(unittest.TestCase):
    """R3 — 대문자 강조·중복 강조. 굵은 글씨 자체는 강조 인플레이션이 아니다."""

    def test_uppercase_and_exact_bold_hit_but_bold_phrase_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "caps.md", ["# 강조", "", "- IMPORTANT: 배포 승인을 받는다"])
            write(root, "phrase.md", ["# 강조", "", "- **필수 작성 요소**"])
            write(root, "exact.md", ["# 강조", "", "- **반드시** 승인을 받는다"])
            write(root, "twice.md", ["# 강조", "", "- 반드시 승인받고 반드시 기록한다"])
            found = lint(root)
            self.assertEqual(len(by_rule(found, "R3", "caps.md")), 1)
            self.assertEqual(by_rule(found, "R3", "phrase.md"), [])
            self.assertEqual(len(by_rule(found, "R3", "exact.md")), 1)
            self.assertEqual(len(by_rule(found, "R3", "twice.md")), 1)


class FixedSequenceTests(unittest.TestCase):
    """R4 — Step 시퀀스에 이탈 여지가 있는지."""

    def test_step_group_without_flex_cue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "steps.md", [
                "# 작업 흐름", "",
                "## Step 1 준비", "", "준비한다.", "",
                "## Step 2 실행", "", "실행한다.", "",
                "## Step 3 검증", "", "검증한다.",
            ])
            hits = by_rule(lint(root), "R4", "steps.md")
            self.assertEqual(len(hits), 1, "Step heading 3개는 부모 기준 1건으로 묶인다")
            self.assertEqual(hits[0]["heading"], "작업 흐름")

    def test_numbered_sections_in_guides_are_not_sequences(self):
        """가이드·템플릿의 'N. 제목' 절 번호와 번호 목록은 에이전트 고정 시퀀스가 아니다 — 절차 문서 범위만 본다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guide = ["# 가이드", "", "## 1. 개요", "", "설명.", "",
                     "## 2. 단계별 절차", "", "1. 하나", "2. 둘", "3. 셋", "4. 넷", "5. 다섯"]
            write(root, "docs/sprint/guide.md", guide)
            write(root, ".claude/commands/ad/skill.md", guide)
            found = lint(root)
            self.assertEqual(by_rule(found, "R4", "docs/sprint/guide.md"), [])
            self.assertEqual(len(by_rule(found, "R4", ".claude/commands/ad/skill.md")), 1,
                             "같은 본문이라도 스킬 디렉토리면 번호 목록 4개 이상은 시퀀스로 본다")

    def test_root_preamble_flex_cue_clears_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "steps.md", [
                "기본 순서, 이탈 가능.", "",
                "# 작업 흐름", "",
                "## Step 1 준비", "", "준비한다.", "",
                "## Step 2 실행", "", "실행한다.", "",
                "## Step 3 검증", "", "검증한다.",
            ])
            self.assertEqual(by_rule(lint(root), "R4", "steps.md"), [])


class CatalogVerificationTests(unittest.TestCase):
    """R6 — 서비스 프로파일의 검증 루프 누락."""

    def test_service_profile_needs_verification_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "catalog/bad.yaml", ["service_id: bad", "type: new"])
            write(root, "catalog/ok.yaml", ["service_id: ok", "verification:", "  - make test"])
            write(root, "catalog/plain.yaml", ["name: 그냥 설정", "value: 1"])
            found = lint(root)
            self.assertEqual(len(by_rule(found, "R6", "catalog/bad.yaml")), 1)
            self.assertEqual(by_rule(found, "R6", "catalog/ok.yaml"), [])
            self.assertEqual(by_rule(found, "R6", "catalog/plain.yaml"), [])


class GeneratedBlockTests(unittest.TestCase):
    """R7 — canonical ↔ generated 블록 드리프트·누락."""

    CANON = ["# 소스", "", "<!-- canonical:contract -->", "계약 본문 한 줄",
             "<!-- /canonical:contract -->"]
    CANON_TARGETED = ["# 소스", "", "<!-- canonical:contract targets=dst.md -->", "계약 본문 한 줄",
                      "<!-- /canonical:contract -->"]
    GEN_OK = ["# 대상", "", "<!-- generated:contract source=src.md -->", "계약 본문 한 줄",
              "<!-- /generated:contract -->"]

    def test_drift_is_found_then_cleared_by_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src.md", self.CANON)
            dst = write(root, "dst.md", [
                "# 대상", "", "<!-- generated:contract source=src.md -->", "낡은 본문",
                "<!-- /generated:contract -->",
            ])
            self.assertEqual(len(by_rule(lint(root), "R7", "dst.md")), 1)
            md, _ = module.collect_targets(str(root), [str(root)])
            changed = module.sync_generated(str(root), md, module.canonical_index(str(root), md))
            self.assertEqual(changed, ["dst.md"])
            self.assertIn("계약 본문 한 줄", dst.read_text(encoding="utf-8"))
            self.assertEqual(by_rule(lint(root), "R7", "dst.md"), [])

    def test_missing_canonical_source_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "dst.md", [
                "# 대상", "", "<!-- generated:contract source=nowhere.md -->", "본문",
                "<!-- /generated:contract -->",
            ])
            hits = by_rule(lint(root), "R7", "dst.md")
            self.assertEqual(len(hits), 1)
            self.assertIn("canonical:contract 블록 없음", hits[0]["excerpt"])

    def test_target_block_pointing_at_other_source_does_not_satisfy_targets(self):
        """targets= 선언은 그 canonical 파일을 source 로 가리키는 블록만 인정한다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "memory/base.md", ["<!-- canonical:c targets=AGENTS.md -->", "본문", "<!-- /canonical:c -->"])
            write(root, "other/base.md", ["<!-- canonical:c -->", "본문", "<!-- /canonical:c -->"])
            write(root, "AGENTS.md", ["<!-- generated:c source=other/base.md -->", "본문", "<!-- /generated:c -->"])
            msgs = [f["excerpt"] for f in by_rule(lint(root), "R7")]
            self.assertTrue(any("source=memory/base.md" in m and "0개" in m for m in msgs), msgs)
            self.assertTrue(any("중복" in m for m in msgs), "같은 이름 canonical 2개는 원본 불명 — R7")

    def test_separated_numbered_lists_are_not_one_sequence(self):
        """한 절에 흩어진 번호 목록(2+2)은 합산하지 않고, 연속 4개만 시퀀스로 본다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, ".claude/commands/ad/a.md", ["# a", "", "## 절", "",
                  "1. 하나", "2. 둘", "", "설명 문단.", "", "1. 셋", "2. 넷"])
            write(root, ".claude/commands/ad/b.md", ["# b", "", "## 절", "",
                  "1. 하나", "2. 둘", "3. 셋", "4. 넷"])
            found = lint(root)
            self.assertEqual(by_rule(found, "R4", ".claude/commands/ad/a.md"), [])
            self.assertEqual(len(by_rule(found, "R4", ".claude/commands/ad/b.md")), 1)

    def test_targets_declaration_requires_exactly_one_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src.md", self.CANON_TARGETED)
            write(root, "dst.md", self.GEN_OK)
            self.assertEqual(by_rule(lint(root), "R7"), [], "선언대로 1개면 발견 없음")

            write(root, "dst.md", ["# 대상", "", "블록이 사라졌다"])
            hits = by_rule(lint(root), "R7")
            self.assertEqual(len(hits), 1)
            self.assertIn("generated:contract 블록이 0개", hits[0]["excerpt"])

            write(root, "dst.md", self.GEN_OK + self.GEN_OK[2:])
            hits = by_rule(lint(root), "R7")
            self.assertEqual(len(hits), 1)
            self.assertIn("한 파일에 2개", hits[0]["excerpt"])

    def test_unclosed_markers_are_found_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src.md", self.CANON_TARGETED)
            write(root, "dst.md", self.GEN_OK[:-1])   # 닫기 마커만 삭제
            hits = by_rule(lint(root), "R7")
            self.assertEqual(len(hits), 1, "닫기 누락은 1건으로만 보고한다")
            self.assertIn("닫기 마커 없음", hits[0]["excerpt"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src.md", self.CANON[:-1])    # canonical 닫기 마커 삭제
            hits = by_rule(lint(root), "R7", "src.md")
            self.assertEqual(len(hits), 1)
            self.assertIn("canonical:contract 닫기 마커 없음", hits[0]["excerpt"])


class FingerprintTests(unittest.TestCase):
    """fingerprint — 강조·공백 변경에 흔들리지 않고 문장 변경에는 반응한다."""

    def test_normalization_is_stable_across_emphasis_and_spacing(self):
        fp = lambda text: module.fingerprint("R1a", "a.md", "H", module.normalize(text))
        self.assertEqual(fp("**반드시** 승인을 받는다"), fp("반드시  승인을   받는다"))
        self.assertEqual(fp("`반드시` 승인을 받는다"), fp("반드시 승인을 받는다"))
        self.assertNotEqual(fp("반드시 승인을 받는다"), fp("반드시 승인을 건너뛴다"))


class CliMixin:
    def run_cli(self, root: Path, *args):
        return subprocess.run([sys.executable, str(TOOL), str(root),
                               "--baseline", str(root / "baseline.json"), *args],
                              capture_output=True, text=True)

    def baseline(self, root: Path):
        return json.loads((root / "baseline.json").read_text(encoding="utf-8"))


class RatchetCliTests(CliMixin, unittest.TestCase):
    """실제 CLI 로 ratchet 왕복 — 신규 차단 / 해결분 하향 / R1b 회귀."""

    def test_baseline_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "rules.md", [
                "# 문서", "", "## 배포 절차", "",
                "- 배포 전 체크리스트를 반드시 채운다", "",
                "## 롤백", "",
                "- 롤백 스크립트는 필수다",
            ])
            # reasoned.md 의 `근거:` 문단은 같은 절 규칙의 이유다 — R1a 0건, reasoned_headings 등재 (v7)
            write(root, "reasoned.md", [
                "# 게이트", "", "## 커밋 게이트", "",
                "- 커밋 전 사용자 확인을 반드시 거친다", "",
                "근거: 2026-01-01 강제 푸시 사고",
            ])

            proc = self.run_cli(root, "--check")
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("베이스라인 없음", proc.stdout)

            self.assertEqual(self.run_cli(root, "--update-baseline").returncode, 1,
                             "초기 생성은 --accept-new 없이 통과하지 않는다")

            proc = self.run_cli(root, "--update-baseline", "--accept-new", "초기")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            data = self.baseline(root)
            self.assertEqual(data["schema_version"], module.SCHEMA_VERSION)
            self.assertEqual(data["matcher_version"], module.MATCHER_VERSION)
            first_count = len(data["findings"])
            self.assertGreaterEqual(first_count, 2)
            batch_ids = set(data["acceptance_batches"])
            self.assertEqual(len(batch_ids), 1)
            self.assertEqual(next(iter(data["acceptance_batches"].values()))["reason"], "초기")
            self.assertTrue(all(v["acceptance_id"] in batch_ids for v in data["findings"].values()))
            self.assertIn("reasoned.md::게이트 > 커밋 게이트", data["reasoned_headings"])

            self.assertEqual(self.run_cli(root, "--check").returncode, 0)

            new_file = write(root, "extra.md", [
                "# 추가", "", "## 신규 규칙", "",
                "- 롤백은 무조건 수동으로 한다",
            ])
            proc = self.run_cli(root, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("extra.md", proc.stdout)

            new_file.unlink()
            self.assertEqual(self.run_cli(root, "--check").returncode, 0)

            write(root, "rules.md", [
                "# 문서", "", "## 배포 절차", "",
                "- 배포 전 체크리스트를 반드시 채운다 — 근거: 2026-02-02 누락 배포",
            ])
            proc = self.run_cli(root, "--update-baseline")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertLess(len(self.baseline(root)["findings"]), first_count,
                            "해결된 위반은 베이스라인에서 내려간다")

            write(root, "reasoned.md", [
                "# 게이트", "", "## 커밋 게이트", "",
                "- 커밋 전 사용자 확인을 반드시 거친다",
            ])
            proc = self.run_cli(root, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("R1b", proc.stdout)

    def test_schema_or_matcher_mismatch_blocks_until_regenerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "rules.md", ["# 문서", "", "## 절", "", "- 배포는 반드시 승인받는다"])
            self.assertEqual(self.run_cli(root, "--update-baseline", "--accept-new", "초기").returncode, 0)
            data = self.baseline(root)
            data["matcher_version"] = module.MATCHER_VERSION + 1
            (root / "baseline.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            proc = self.run_cli(root, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("스키마/matcher 불일치", proc.stdout)
            self.assertEqual(self.run_cli(root, "--update-baseline").returncode, 1)
            self.assertEqual(self.run_cli(root, "--update-baseline", "--accept-new", "재생성").returncode, 0)
            self.assertEqual(self.baseline(root)["matcher_version"], module.MATCHER_VERSION)

    def test_repeated_identical_sentence_is_counted(self):
        """같은 heading 안 동일 문장은 fingerprint 가 같다 — count 로 ratchet 해야 한다."""
        rule = "- 배포 전 체크리스트를 반드시 채운다"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "rules.md", ["# 문서", "", "## 절", "", rule, rule])
            self.assertEqual(self.run_cli(root, "--update-baseline", "--accept-new", "초기").returncode, 0)
            entry = next(iter(self.baseline(root)["findings"].values()))
            self.assertEqual(entry["count"], 2)

            write(root, "rules.md", ["# 문서", "", "## 절", "", rule, rule, rule])
            proc = self.run_cli(root, "--check")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("2→3건", proc.stdout)

            write(root, "rules.md", ["# 문서", "", "## 절", "", rule])
            self.assertEqual(self.run_cli(root, "--check").returncode, 0)
            self.assertEqual(self.run_cli(root, "--update-baseline").returncode, 0)
            self.assertEqual(next(iter(self.baseline(root)["findings"].values()))["count"], 1)

    def test_moving_a_violation_between_files(self):
        """block 위반 이동은 신규 유입, warn 그룹 이동은 통과."""
        block_rule = ["# 문서", "", "## 절", "", "- 배포 전 체크리스트를 반드시 채운다"]
        steps = ["# 작업 흐름", "",
                 "## Step 1 준비", "", "준비한다.", "",
                 "## Step 2 실행", "", "실행한다.", "",
                 "## Step 3 검증", "", "검증한다."]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "a.md", block_rule)
            write(root, "steps_a.md", steps)
            self.assertEqual(self.run_cli(root, "--update-baseline", "--accept-new", "초기").returncode, 0)
            self.assertEqual(self.run_cli(root, "--check").returncode, 0)

            (root / "a.md").unlink()
            write(root, "b.md", block_rule)
            proc = self.run_cli(root, "--check")
            self.assertEqual(proc.returncode, 1, "경로가 바뀐 block 위반은 신규다")
            self.assertIn("b.md", proc.stdout)

            (root / "b.md").unlink()
            write(root, "a.md", block_rule)
            self.assertEqual(self.run_cli(root, "--check").returncode, 0)

            (root / "steps_a.md").unlink()
            write(root, "steps_b.md", steps)
            self.assertEqual(self.run_cli(root, "--check").returncode, 0,
                             "warn 규칙 이동은 차단하지 않는다")

    def test_sync_generated_cli_reports_change_then_no_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "src.md", [
                "# 소스", "",
                "<!-- canonical:contract targets=dst.md -->", "계약 본문",
                "<!-- /canonical:contract -->",
            ])
            write(root, "dst.md", [
                "# 대상", "",
                "<!-- generated:contract source=src.md -->", "낡은 본문",
                "<!-- /generated:contract -->",
            ])
            proc = self.run_cli(root, "--sync-generated")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("갱신: dst.md", proc.stdout)
            self.assertIn("변경 없음", self.run_cli(root, "--sync-generated").stdout)


if __name__ == "__main__":
    unittest.main()
