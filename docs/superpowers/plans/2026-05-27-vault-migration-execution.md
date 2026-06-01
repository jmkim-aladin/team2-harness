# vault 이관 실행 (Sub 3) 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `2026-05-27-vault-migration-execution-design.md` 기반으로 `harness/tools/migrate_vault.py`를 작성하고, Sub 2 산출(`migration-plan.json`)의 `move/merge/delete` 134건을 일괄 실행하고 wikilink를 재작성한다.

**Architecture:** stdlib only Python 단일 도구. 3-phase (이관/wikilink/검증). `--dry-run` 기본, `--apply` 명시 실행. vault repo cwd에서 `git mv`/`git rm`, untracked는 `mv`/`rm` + `git add` fallback. wikilink 재작성은 정규식 기반.

**Tech Stack:** Python 3 stdlib (`pathlib`, `re`, `json`, `argparse`, `subprocess`, `shutil`, `collections`).

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- `VAULT` = `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`

**규칙:**
- harness branch = `feature/knowledge-scope-separation`
- 모든 commit 사용자 승인 후
- AI co-author footer 금지
- vault commit과 harness commit 분리
- 도구 실행은 우선 `--dry-run`, 검증 후 `--apply`

---

## File Structure

### 신규 (harness)
- `REPO/tools/migrate_vault.py` — 이관 도구 (단일 Python 파일, ~350 라인)

### 갱신 (harness)
- `REPO/tools/README.md` — migrate_vault 섹션 추가

### 신규 (vault)
- `VAULT/wiki/guides/_audit/migration-log.md` — 실행 결과 로그

### 갱신 (vault, 도구 실행 결과)
- 다수 md 파일 이관 (`git mv`/`git rm`)
- wikilink 재작성 (다수 md 본문 변경)

---

## Phase 0: 사전 점검

### Task 0.1: 입력 파일 존재 확인

**Files:** N/A

- [ ] **Step 1: plan.json + audit_vault.py 존재**

```bash
ls -la "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/_audit/migration-plan.json"
ls -la /Users/jm/Documents/workspace/team2/tools/audit_vault.py
```

Expected: 두 파일 모두 존재.

- [ ] **Step 2: vault 상태 확인**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git status --short | head -10
git branch --show-current
```

Expected: branch (main 등) + status. 본 도구는 vault status 깨끗 여부 강제하지 않으나, 새 변경물(untracked wiki/ 작업물)은 그대로 두고 도구만 plan 대상 파일만 다룸.

---

## Phase 1: `migrate_vault.py` 구현

### Task 1.1: 도구 본문 작성

**Files:**
- Create: `REPO/tools/migrate_vault.py`

- [ ] **Step 1: 전체 본문 작성**

Write 도구로 다음 본문 그대로 작성:

```python
#!/usr/bin/env python3
"""vault 이관 실행 도구.

spec: docs/superpowers/specs/2026-05-27-vault-migration-execution-design.md

Usage:
    # dry-run (기본 — 변경 없음)
    python3 tools/migrate_vault.py \\
        --vault "$VAULT" \\
        --plan  "$VAULT/wiki/guides/_audit/migration-plan.json"

    # 실 실행
    python3 tools/migrate_vault.py \\
        --vault "$VAULT" \\
        --plan  "$VAULT/wiki/guides/_audit/migration-plan.json" \\
        --apply

    # 단계 분리
    python3 tools/migrate_vault.py ... --phase 1 --apply   # 파일 이관만
    python3 tools/migrate_vault.py ... --phase 2 --apply   # wikilink 재작성만
    python3 tools/migrate_vault.py ... --phase 3           # 검증만
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

WIKILINK_RE = re.compile(
    r'\[\[((?:\.\./)*(?:[^/\]|#]+/)*)([^|#\]]+?)(\.md)?(#[^|\]]+)?(\|[^\]]+)?\]\]'
)


def load_plan(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, check=check,
                          capture_output=True, text=True)


def git_mv_or_add(vault: Path, src_rel: str, dst_rel: str, dry_run: bool) -> str:
    """git mv 시도, 실패 시 mv + git add."""
    if dry_run:
        return "dry-run"
    src = vault / src_rel
    dst = vault / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_git(["mv", src_rel, dst_rel], cwd=vault)
        return "git mv"
    except subprocess.CalledProcessError:
        shutil.move(str(src), str(dst))
        run_git(["add", dst_rel], cwd=vault)
        return "mv+add"


def git_rm_or_rm(vault: Path, src_rel: str, dry_run: bool) -> str:
    if dry_run:
        return "dry-run"
    src = vault / src_rel
    try:
        run_git(["rm", src_rel], cwd=vault)
        return "git rm"
    except subprocess.CalledProcessError:
        if src.exists():
            src.unlink()
        return "rm"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            return text[end + 4:].lstrip("\n")
    return text


def do_merge(vault: Path, src_rel: str, dst_rel: str, dry_run: bool) -> str:
    """dst 존재: append, dst 미존재: move 변환."""
    src = vault / src_rel
    dst = vault / dst_rel
    if not dst.exists():
        # move로 변환
        return git_mv_or_add(vault, src_rel, dst_rel, dry_run) + " (merge→move)"
    if dry_run:
        return "dry-run merge"
    src_body = strip_frontmatter(src.read_text(encoding="utf-8"))
    dst_text = dst.read_text(encoding="utf-8")
    merged = dst_text.rstrip() + f"\n\n## (merged from {src.name})\n\n" + src_body
    dst.write_text(merged, encoding="utf-8")
    run_git(["add", dst_rel], cwd=vault)
    return git_rm_or_rm(vault, src_rel, dry_run=False) + " (merged)"


def phase1_migrate(vault: Path, plan: list[dict], actions: set[str],
                   dry_run: bool) -> dict:
    """파일 이관."""
    stats = Counter()
    merge_surface = []
    errors = []
    for row in plan:
        a = row["action"]
        stats[a] += 1
        if a not in actions:
            continue
        if a in ("keep", "review"):
            continue
        src = row["src"]
        dst = row.get("dst")
        try:
            if a == "move":
                if not dst:
                    errors.append(f"move 누락 dst: {src}")
                    continue
                result = git_mv_or_add(vault, src, dst, dry_run)
                stats[f"move_{result}"] += 1
            elif a == "merge":
                if not dst:
                    errors.append(f"merge 누락 dst: {src}")
                    continue
                result = do_merge(vault, src, dst, dry_run)
                merge_surface.append({"src": src, "dst": dst, "result": result})
                stats[f"merge_{result}"] += 1
            elif a == "delete":
                result = git_rm_or_rm(vault, src, dry_run)
                stats[f"delete_{result}"] += 1
        except Exception as e:
            errors.append(f"{a} {src} → {dst}: {e}")
    return {"stats": dict(stats), "merge_surface": merge_surface, "errors": errors}


def build_rename_map(plan: list[dict]) -> dict[str, str]:
    """plan에서 옛 stem → 새 stem 매핑. 충돌 시 None 표시."""
    rename: dict[str, str | None] = {}
    for row in plan:
        if row["action"] not in ("move", "merge"):
            continue
        src = row["src"]
        dst = row.get("dst")
        if not dst:
            continue
        old = Path(src).stem
        new = Path(dst).stem
        if old == new:
            continue
        if old in rename:
            if rename[old] != new:
                rename[old] = None  # 충돌 마킹
        else:
            rename[old] = new
    return rename


def phase2_wikilinks(vault: Path, rename: dict[str, str | None],
                     dry_run: bool) -> dict:
    """wikilink 재작성."""
    changed_files: list[str] = []
    conflicts: list[str] = []
    link_count = 0
    wiki_dir = vault / "wiki"

    def repl(m: re.Match) -> str:
        nonlocal link_count
        path_prefix, name, ext, section, display = m.groups()
        if name not in rename:
            return m.group(0)
        new_name = rename[name]
        if new_name is None:
            conflicts.append(name)
            return m.group(0)
        link_count += 1
        return f"[[{path_prefix or ''}{new_name}{ext or ''}{section or ''}{display or ''}]]"

    for md in sorted(wiki_dir.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_text = WIKILINK_RE.sub(repl, text)
        if new_text != text:
            changed_files.append(str(md.relative_to(vault)))
            if not dry_run:
                md.write_text(new_text, encoding="utf-8")

    if not dry_run and changed_files:
        run_git(["add", "-A", "wiki/"], cwd=vault, check=False)

    return {
        "changed_files": changed_files,
        "link_count": link_count,
        "conflicts": sorted(set(conflicts)),
    }


def phase3_verify(vault: Path, rename: dict[str, str | None]) -> dict:
    """잔존 옛 이름 wikilink surface."""
    surface: dict[str, list[str]] = {}
    wiki_dir = vault / "wiki"
    for md in wiki_dir.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for old in rename:
            pattern = re.compile(
                r'\[\[(?:\.\./)*(?:[^/\]|#]+/)*' + re.escape(old) +
                r'(\.md)?(#[^|\]]+)?(\|[^\]]+)?\]\]'
            )
            if pattern.search(text):
                surface.setdefault(old, []).append(str(md.relative_to(vault)))
    return surface


def render_log(plan_path: Path, p1: dict | None, p2: dict | None,
               p3: dict | None, dry_run: bool) -> str:
    lines = [
        "---",
        "type: audit-log",
        "title: vault 이관 실행 로그",
        "canonical_id: audit:migration-log",
        "status: canonical",
        f"updated_at: {datetime.now().strftime('%Y-%m-%d')}",
        "---",
        "",
        "# vault 이관 실행 로그",
        "",
        f"- 입력 plan: `{plan_path}`",
        f"- 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 모드: {'dry-run' if dry_run else 'apply'}",
        "",
    ]
    if p1:
        lines += ["## Phase 1 (파일 이관)", ""]
        for k, v in sorted(p1["stats"].items()):
            lines.append(f"- {k}: {v}")
        if p1["merge_surface"]:
            lines += ["", "### merge surface", ""]
            for m in p1["merge_surface"]:
                lines.append(f"- {m['src']} → {m['dst']} ({m['result']})")
        if p1["errors"]:
            lines += ["", "### errors", ""]
            for e in p1["errors"]:
                lines.append(f"- {e}")
        lines += [""]
    if p2:
        lines += ["## Phase 2 (wikilink 재작성)", ""]
        lines += [f"- 변경된 파일: {len(p2['changed_files'])}",
                  f"- 갱신된 링크 수: {p2['link_count']}",
                  f"- 충돌 (옛 이름이 여러 새 이름으로 분기): {len(p2['conflicts'])}"]
        if p2["conflicts"]:
            lines += ["", "### 충돌 목록", ""]
            for c in p2["conflicts"]:
                lines.append(f"- {c}")
        lines += [""]
    if p3:
        lines += ["## Phase 3 (검증)", ""]
        if not p3:
            lines.append("- 잔존 끊긴 wikilink: 0")
        else:
            lines.append(f"- 잔존 끊긴 wikilink (옛 이름 → 발견 파일 수): {len(p3)}")
            for old, files in sorted(p3.items()):
                lines.append(f"  - `{old}`: {len(files)}개 파일")
        lines += [""]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--phase", default="all",
                    choices=["1", "2", "3", "all"])
    ap.add_argument("--action", default="move,merge,delete",
                    help="처리할 action 목록 (콤마 구분)")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true",
                    help="실 실행 (--dry-run 무시)")
    ap.add_argument("--log-out", type=Path, default=None)
    args = ap.parse_args()

    dry_run = not args.apply
    vault = args.vault.resolve()
    plan = load_plan(args.plan)
    actions = set(args.action.split(","))

    p1 = p2 = p3 = None
    rename = build_rename_map(plan)

    if args.phase in ("1", "all"):
        p1 = phase1_migrate(vault, plan, actions, dry_run)
    if args.phase in ("2", "all"):
        p2 = phase2_wikilinks(vault, rename, dry_run)
    if args.phase in ("3", "all"):
        p3 = phase3_verify(vault, rename)

    log_text = render_log(args.plan, p1, p2, p3, dry_run)

    log_out = args.log_out or (vault / "wiki/guides/_audit/migration-log.md")
    if not dry_run:
        log_out.parent.mkdir(parents=True, exist_ok=True)
        log_out.write_text(log_text, encoding="utf-8")
        print(f"log: {log_out}", file=sys.stderr)
    else:
        print(log_text)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 문법 점검**

```bash
python3 -m py_compile /Users/jm/Documents/workspace/team2/tools/migrate_vault.py && echo OK
```

Expected: `OK`.

- [ ] **Step 3: --help 동작**

```bash
python3 /Users/jm/Documents/workspace/team2/tools/migrate_vault.py --help
```

Expected: argparse usage 출력 (required: --vault, --plan).

### Task 1.2: `tools/README.md` 갱신

**Files:**
- Modify: `REPO/tools/README.md`

- [ ] **Step 1: migrate_vault 섹션 추가**

기존 `tools/README.md` 끝에 다음 섹션 추가 (Edit 도구):

```markdown

## migrate_vault.py — vault 일괄 이관

audit_vault.py 산출(`migration-plan.json`)을 입력으로 받아 파일 이관 + wikilink 재작성.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# 1) dry-run으로 영향 확인 (기본)
python3 tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan  "$VAULT/wiki/guides/_audit/migration-plan.json"

# 2) 단계별 실 실행
python3 tools/migrate_vault.py --vault "$VAULT" --plan "...migration-plan.json" --phase 1 --apply
python3 tools/migrate_vault.py --vault "$VAULT" --plan "...migration-plan.json" --phase 2 --apply
python3 tools/migrate_vault.py --vault "$VAULT" --plan "...migration-plan.json" --phase 3
```

### Phase

- 1: 파일 이관 (action: move/merge/delete)
- 2: wikilink 재작성 (옛 이름 → 새 이름)
- 3: 잔존 끊긴 wikilink 검증 + surface

### 옵션

- `--dry-run` (기본) — 실 변경 없음, 영향만 출력
- `--apply` — 실 실행 (`git mv`/`git rm`/append/sed)
- `--phase 1|2|3|all` — 기본 all
- `--action move,merge,delete` — 처리 대상 action 필터
- `--log-out <path>` — 로그 출력 경로 (기본 vault/wiki/guides/_audit/migration-log.md)

### 안전장치

- 기본 dry-run, `--apply` 명시해야 실 실행
- merge에서 dst 존재 시 자동 append + surface (사람 후속 검토)
- git mv 실패(untracked) 시 mv + git add fallback
- wikilink 충돌(동명 다른 새 이름) 시 변경 안 함 + surface
```

- [ ] **Step 2: 검증**

```bash
grep -c "migrate_vault" /Users/jm/Documents/workspace/team2/tools/README.md
```

Expected: ≥ 3.

---

## Phase 2: dry-run 검증

### Task 2.1: dry-run 실 실행

**Files:** N/A

- [ ] **Step 1: 전체 dry-run**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan "$VAULT/wiki/guides/_audit/migration-plan.json"
```

Expected: stdout에 log 출력 (Phase 1 stats, Phase 2 changed/links/conflicts, Phase 3 잔존). 모든 stats에 `dry-run` 접미사. 에러 0건.

- [ ] **Step 2: 카운트 검증**

dry-run 출력의 Phase 1 stats에서:
- `move`: 128
- `merge`: 3
- `delete`: 3
- `keep`: 34
- `review`: 439

(plan json 통계와 일치)

- [ ] **Step 3: 충돌·에러 확인**

dry-run 출력에:
- Phase 1 errors == 0
- Phase 2 conflicts 목록 — 있으면 row 수 surface (대응은 사람이 plan 갱신 또는 별도)

충돌·에러 0건이면 다음 phase 진행 가능. 있으면 사용자 확인 후 어떻게 처리할지 결정.

---

## Phase 3: Phase 1 (파일 이관) 실 실행

### Task 3.1: Phase 1만 `--apply`

**Files:** vault의 다수 md (이관)

- [ ] **Step 1: 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan "$VAULT/wiki/guides/_audit/migration-plan.json" \
  --phase 1 --apply
```

Expected: stderr에 `log: ...migration-log.md`. vault git status에 다수 stage 변경.

- [ ] **Step 2: 영향 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
cd "$VAULT" && git status --short | grep -E "^(R|A|D)" | wc -l
echo "---log---"
head -40 "$VAULT/wiki/guides/_audit/migration-log.md"
```

Expected: ~134건 변경 (move=128 R/A, merge=3, delete=3 D). log 본문에 stats.

- [ ] **Step 3: vault commit Phase 1 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/guides/_audit/migration-log.md
git commit -m "wiki: Sub 3 Phase 1 — 파일 이관 (move/merge/delete) 일괄 실행

134건 (move=128, merge=3, delete=3). migrate_vault.py --phase 1 --apply 결과.
merge surface 항목은 wiki/guides/_audit/migration-log.md 참조."
```

- [ ] **Step 4: footer 검사**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

---

## Phase 4: Phase 2 (wikilink) 실 실행

### Task 4.1: Phase 2만 `--apply`

**Files:** vault md 본문 다수 (wikilink 재작성)

- [ ] **Step 1: 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan "$VAULT/wiki/guides/_audit/migration-plan.json" \
  --phase 2 --apply
```

Expected: stderr `log: ...`. log 본문에 Phase 2 stats (changed_files, link_count, conflicts).

- [ ] **Step 2: 영향 확인**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git status --short | grep -E "^ M" | wc -l
echo "---phase 2 log---"
grep -A 10 "Phase 2" "wiki/guides/_audit/migration-log.md"
```

Expected: M 파일 수 = changed_files 수.

- [ ] **Step 3: vault commit Phase 2 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/guides/_audit/migration-log.md
git commit -m "wiki: Sub 3 Phase 2 — wikilink 재작성 일괄 실행

옛 이름 → 새 이름 매핑 기반 [[wikilink]] 갱신. migrate_vault.py --phase 2 --apply 결과."
```

---

## Phase 5: Phase 3 (검증) + 마무리

### Task 5.1: Phase 3 검증

**Files:** N/A (read-only)

- [ ] **Step 1: 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan "$VAULT/wiki/guides/_audit/migration-plan.json" \
  --phase 3
```

Expected: stdout에 잔존 끊긴 wikilink surface (0 또는 옛이름→파일 목록).

- [ ] **Step 2: 잔존 0이면 완료, 있으면 사람 후속**

surface 있으면 사용자가 해당 파일 본문 확인 후 수동 갱신 또는 plan 보정. Sub 3 도구 작업은 종료.

### Task 5.2: harness commit (도구 + README + plan)

**Files:**
- `REPO/tools/migrate_vault.py`
- `REPO/tools/README.md` (갱신)
- `REPO/docs/superpowers/plans/2026-05-27-vault-migration-execution.md` (본 plan)

- [ ] **Step 1: staging**

```bash
cd /Users/jm/Documents/workspace/team2
git add tools/migrate_vault.py tools/README.md docs/superpowers/plans/2026-05-27-vault-migration-execution.md
git status --short | head
```

Expected: 3건 staged (A migrate_vault.py, M README.md, A plan).

- [ ] **Step 2: commit (사용자 승인 후)**

```bash
git commit -m "tools/migrate_vault: vault 일괄 이관·wikilink 재작성 도구 + Sub 3 plan

migration-plan.json 입력 → 3-phase 실행 (이관/wikilink/검증). dry-run 기본·--apply 명시 실행. merge 자동 append + surface, git mv fallback 처리."
```

- [ ] **Step 3: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

---

## Self-Review

**Spec 커버리지:**
- 도구 `migrate_vault.py` (Task 1.1) ✓
- README 갱신 (Task 1.2) ✓
- Phase 1 (이관) ✓ Task 3.1
- Phase 2 (wikilink) ✓ Task 4.1
- Phase 3 (검증) ✓ Task 5.1
- dry-run + apply 분리 ✓ Task 1.1 main argparse
- migration-log.md 산출 ✓ Task 1.1 render_log
- merge 자동 append + surface ✓ Task 1.1 do_merge
- git mv fallback ✓ Task 1.1 git_mv_or_add
- wikilink 5 변형 ✓ Task 1.1 WIKILINK_RE
- 충돌 처리 ✓ Task 1.1 build_rename_map (None 마킹) + phase2_wikilinks

**Placeholder 없음**: 모든 step에 실 코드/명령.

**타입 일관:**
- action enum 5종 (move/merge/keep/delete/review) 일관
- phase enum (1/2/3/all) 일관
- rename dict[str, str | None] 일관
- log render section header 일관

빠진 부분 없음.

## 검증 기준

- `migrate_vault.py --help` 동작
- dry-run stats == plan.json action 통계 일치
- Phase 1 실행 후 vault status에 ~134건 staged
- Phase 2 실행 후 wikilink 갱신 카운트 > 0 (옛 이름 매핑 존재 시)
- Phase 3 잔존 wikilink 0 또는 surface 목록 출력
- vault commit 2건 (Phase 1, Phase 2)
- harness commit 1건 (도구 + README + plan)
- AI footer 0건
