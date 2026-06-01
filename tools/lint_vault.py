#!/usr/bin/env python3
"""vault lint — 5 룰 hard-code, stdlib only.

룰:
1. frontmatter `type` 필수 + type별 필수 필드
2. 파일 위치 = type 기반 결정 트리 일치
3. 파일명 = kebab-case, 서비스 prefix 금지 (예외: {name}-index.md, storefront-ddd-* 시리즈)
4. file size warn (≥500 line)
5. {name}-index.md 안 <!-- llm-hint --> 블록 의무

Usage:
    # 전체 vault lint (정기 sweep)
    python3 tools/lint_vault.py --vault "$VAULT" --all

    # staged diff lint (pre-commit)
    python3 tools/lint_vault.py --vault "$VAULT" --files wiki/foo.md wiki/bar.md

Exit:
    0 = 모든 검사 통과
    1 = 검사 실패 (위반 surface)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# type별 필수 필드 + 허용 위치
TYPE_RULES: dict[str, dict] = {
    "ticket": {
        "required": ["ticket_id", "ticket_status", "assignee", "service", "sprint"],
        "location": r"^wiki/processes/tickets/",
        "filename": r"^dev2-\d+\.md$",
    },
    "worksheet": {
        "required": ["ticket_id", "target_yearmonth"],
        "location": r"^wiki/processes/tickets/",
        "filename": r"^dev2-\d+-worksheet-\d+\.md$",
    },
    "weekly-report": {
        "required": ["year", "month", "week_in_month", "assignee"],
        "location": r"^wiki/processes/weekly/",
        "filename": r"^\d{4}-\d{2}-\d{1,2}W-[a-z0-9-]+\.md$",
    },
    "daily": {
        "required": ["date"],
        "location": r"^wiki/processes/daily/",
        "filename": r"^\d{4}-\d{2}-\d{2}\.md$",
    },
    "meeting": {
        # filename: 단일일자(YYYY-MM-DD) 또는 월간(YYYY-MM) 모두 허용. 일자는 date/meeting_date에 명시.
        "required": [],
        "location": r"^wiki/processes/meetings/",
        "filename": r"^\d{4}-\d{2}(-\d{2})?-[a-z0-9-]+\.md$",
    },
    "okr": {
        # taxonomy: okr/ = 분기/연간 OKR. 분기 문서는 frontmatter에 quarter, 연간(예: 2026-team-okr)은 quarter 없음.
        "required": ["year", "scope"],
        "location": r"^wiki/processes/okr/",
        "filename": r"^\d{4}-(q[1-4](-[a-z0-9-]+)?|[a-z][a-z0-9-]+)\.md$",
    },
    "incident": {
        "required": ["date"],
        "location": r"^wiki/processes/incidents/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "capacity-plan": {
        "required": ["year", "month"],
        "location": r"^wiki/processes/capacity/",
        "filename": r"^\d{4}-\d{2}(-[a-z0-9-]+)?\.md$",
    },
    "sprint": {
        "required": [],
        "location": r"^wiki/processes/sprint/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "domain": {
        "required": ["service_id"],
        "location": r"^wiki/services/[a-z0-9-]+/domains/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "service": {  # 서비스 home 엔티티 (그래프 허브)
        "required": ["service_id"],
        "location": r"^wiki/services/[a-z0-9-]+/[a-z0-9-]+\.md$",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "analysis": {
        "required": ["service_id"],
        "location": r"^wiki/services/[a-z0-9-]+/analysis/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "decision": {
        "required": ["service_id"],
        "location": r"^wiki/services/[a-z0-9-]+/decisions/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "proposal": {
        "required": ["service_id"],
        "location": r"^wiki/services/[a-z0-9-]+/proposals/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "guide": {
        "required": [],
        "location": r"^wiki/guides/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "glossary": {
        "required": [],
        "location": r"^wiki/glossary/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "project": {
        "required": [],
        "location": r"^wiki/projects/",
        "filename": r"^([a-z0-9-]+\.md|_index\.md)$",
    },
    "index": {
        "required": [],
        "location": r"^wiki/.*-index\.md$",
        "filename": r"^[a-z0-9-]+-index\.md$",
    },
    "Type": {  # Tolaria 타입정의 문서 (vault root)
        "required": [],
        "location": r"^[a-z0-9-]+\.md$",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "audit-report": {
        "required": [],
        "location": r"^wiki/guides/_audit/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "audit-log": {
        "required": [],
        "location": r"^wiki/guides/_audit/",
        "filename": r"^[a-z0-9-]+\.md$",
    },
    "log": {
        "required": [],
        "location": r"^wiki/_log\.md$",
        "filename": r"^_log\.md$",
    },
}

# 파일명에 서비스 prefix 금지 (dir이 표현). 단 _index.md 등 예외.
SERVICE_PREFIX = ("tobe-", "max-", "naru-", "bazaar-", "aasm-", "shopping-",
                  "caravan-", "blog-", "storefront-", "web-aladin-")

# prefix 룰 예외: storefront-ddd-* 는 prefixed HTML 렌더 시리즈의 source .md.
# .md↔.html stem parity 유지 위해 디렉터리-표현 룰에서 제외.
PREFIX_EXEMPT = re.compile(r"^storefront-ddd-")

SIZE_WARN_LINES = 500

# advisory 태그. 이 문자열을 포함한 violation은 경고로 분류 — exit code에 영향 없음.
WARN_TAG = "WARN —"


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and v != "":
            fm[k] = v
    return fm


def lint_file(rel: str, abs_path: Path) -> list[str]:
    """단일 파일 lint. violation 리스트 반환 (empty == pass)."""
    violations: list[str] = []
    try:
        text = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        return [f"{rel}: 읽기 실패 — {e}"]

    # 1. frontmatter type 필수
    fm = parse_frontmatter(text)
    if fm is None:
        return [f"{rel}: frontmatter 없음 (--- 으로 시작 필요)"]
    if "type" not in fm:
        return [f"{rel}: frontmatter `type` 필드 누락"]

    t = fm["type"]
    rules = TYPE_RULES.get(t)
    if rules is None:
        violations.append(f"{rel}: 알 수 없는 type=`{t}` (TYPE_RULES에 정의되지 않음)")
        return violations

    # 1b. type별 필수 필드
    for field in rules["required"]:
        if field not in fm:
            violations.append(
                f"{rel}: type=`{t}` 필수 필드 `{field}` 누락"
            )

    # 2. 위치
    if not re.search(rules["location"], rel):
        violations.append(
            f"{rel}: type=`{t}` 위치 위반. 기대 패턴=`{rules['location']}`"
        )

    # 3. 파일명
    fname = abs_path.name
    if not re.match(rules["filename"], fname):
        violations.append(
            f"{rel}: type=`{t}` 파일명 패턴 위반. 기대=`{rules['filename']}`, 실제=`{fname}`"
        )
    # 3b. 서비스 prefix 금지 (단 {name}-index.md는 stem uniqueness 위해 허용)
    if not fname.endswith("-index.md") and fname != "_log.md" and not PREFIX_EXEMPT.match(fname):
        for p in SERVICE_PREFIX:
            if fname.startswith(p):
                violations.append(
                    f"{rel}: 파일명에 서비스 prefix `{p}` 금지 (디렉터리가 표현)"
                )
                break

    # 4. 파일 크기 warn
    line_count = text.count("\n")
    if line_count >= SIZE_WARN_LINES:
        violations.append(
            f"{rel}: {WARN_TAG} {line_count} lines (≥{SIZE_WARN_LINES}). atomic 분리 권장"
        )

    # 5. {name}-index.md llm-hint 블록
    if fname.endswith("-index.md"):
        if "<!-- llm-hint -->" not in text or "<!-- /llm-hint -->" not in text:
            violations.append(
                f"{rel}: {fname} 안 `<!-- llm-hint -->` ~ `<!-- /llm-hint -->` 블록 의무 누락"
            )

    return violations


SKIP_DIRS = {"templates", "_audit"}  # placeholder 포함 또는 도구 자체 산출물


def is_skip(rel: str) -> bool:
    parts = Path(rel).parts
    return any(d in parts for d in SKIP_DIRS)


def collect_files(vault: Path, files: list[str] | None) -> list[Path]:
    if files:
        out = []
        for f in files:
            p = Path(f)
            if not p.is_absolute():
                p = vault / f
            if p.exists() and p.suffix == ".md":
                try:
                    rel = str(p.relative_to(vault))
                except ValueError:
                    rel = str(p)
                if not is_skip(rel):
                    out.append(p)
        return out
    # all wiki/**/*.md (skip templates/, _audit/)
    out = []
    for p in sorted((vault / "wiki").rglob("*.md")):
        rel = str(p.relative_to(vault))
        if not is_skip(rel):
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--all", action="store_true", help="vault 전체 lint")
    ap.add_argument("--files", nargs="*", default=None,
                    help="특정 파일만 lint (vault root 기준 상대 또는 절대)")
    args = ap.parse_args()

    vault = args.vault.resolve()
    files = collect_files(vault, args.files)

    if not files:
        print("lint_vault: 검사 대상 없음", file=sys.stderr)
        return 0

    all_violations: list[str] = []
    for abs_path in files:
        try:
            rel = str(abs_path.relative_to(vault))
        except ValueError:
            rel = str(abs_path)
        all_violations.extend(lint_file(rel, abs_path))

    hard = [v for v in all_violations if WARN_TAG not in v]
    warns = [v for v in all_violations if WARN_TAG in v]

    for v in all_violations:
        print(v, file=sys.stderr)

    if hard:
        print(
            f"\nlint_vault: 위반 {len(hard)}건, 경고 {len(warns)}건, 검사 파일 {len(files)}건",
            file=sys.stderr,
        )
        return 1

    ok = f"lint_vault: OK — 검사 파일 {len(files)}건"
    if warns:
        ok = f"lint_vault: OK (경고 {len(warns)}건) — 검사 파일 {len(files)}건"
    print(ok, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
