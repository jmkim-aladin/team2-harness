# vault 인덱스 자동 생성 (Sub 4) 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `2026-05-27-vault-index-generator-design.md` 기반으로 `harness/tools/generate_vault_indexes.py`를 작성하고, vault `services/{svc}/_index.md`, `processes/{type}/_index.md`, hub `_index.md`들을 generated block으로 자동 생성·갱신한다.

**Architecture:** stdlib Python 단일 파일. 디렉터리 listing 기반. `<!-- generated:vault-index -->` 블록 안만 자동 갱신, 사람 본문 보존. dry-run 기본 + `--apply` 실 실행.

**Tech Stack:** Python 3 stdlib (`pathlib`, `re`, `argparse`, `subprocess`, `datetime`).

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- `VAULT` = `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`

**규칙:**
- harness branch = `feature/knowledge-scope-separation`
- 모든 commit 사용자 승인 후
- AI co-author footer 금지
- harness commit 1건, vault commit 1건

---

## File Structure

### 신규 (harness)
- `REPO/tools/generate_vault_indexes.py` (~250 라인)

### 갱신 (harness)
- `REPO/tools/README.md` — generate_vault_indexes 섹션 추가

### 신규/갱신 (vault, 도구 산출)
- `VAULT/wiki/services/{svc}/_index.md` 다수 (신규 또는 generated block 갱신)
- `VAULT/wiki/processes/{type}/_index.md` 다수
- `VAULT/wiki/services/_index.md`, `VAULT/wiki/processes/_index.md` (hub)

---

## Phase 0: 사전 점검

### Task 0.1: vault 상태 확인

- [ ] **Step 1: services/processes 디렉터리 목록**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
echo "--- services ---"; /bin/ls "$VAULT/wiki/services" | head
echo "--- processes ---"; /bin/ls "$VAULT/wiki/processes" | head
echo "--- 기존 _index.md ---"; find "$VAULT/wiki/services" "$VAULT/wiki/processes" -name '_index.md' | head
```

Expected: services 5건+, processes 5건+. 기존 _index.md 일부 존재.

- [ ] **Step 2: 기존 _index.md 본문 점검**

```bash
for f in $(find "$VAULT/wiki/services" "$VAULT/wiki/processes" -name '_index.md'); do
  echo "=== $f ==="
  head -10 "$f"
done | head -40
```

Expected: frontmatter + 본문 sample 출력.

---

## Phase 1: 도구 구현

### Task 1.1: `generate_vault_indexes.py` 작성

**Files:**
- Create: `REPO/tools/generate_vault_indexes.py`

- [ ] **Step 1: 전체 본문 작성**

```python
#!/usr/bin/env python3
"""vault 인덱스 자동 생성 도구.

spec: docs/superpowers/specs/2026-05-27-vault-index-generator-design.md

생성 대상:
- wiki/services/{svc}/_index.md
- wiki/processes/{type}/_index.md
- wiki/services/_index.md (hub)
- wiki/processes/_index.md (hub)

generated:vault-index 블록만 자동 갱신, 사람 작성 본문은 보존.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VAULT_INDEX_BLOCK_RE = re.compile(
    r'<!-- generated:vault-index[^>]*-->.*?<!-- /generated -->',
    re.DOTALL,
)

HARNESS_LINK_BLOCK_RE = re.compile(
    r'<!-- generated:harness-link[^>]*-->.*?<!-- /generated -->',
    re.DOTALL,
)

SERVICE_SUB_CATEGORIES = [
    "domains", "analysis", "decisions", "proposals", "processes",
]

# processes/{type} 별 정렬 방식
DATE_SORT_TYPES = {"daily", "weekly", "meetings", "tickets"}


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def list_md_files(dir: Path, sort_by_date_desc: bool = False) -> list[Path]:
    if not dir.exists():
        return []
    files = [p for p in dir.iterdir() if p.is_file() and p.suffix == ".md"
             and p.name != "_index.md"]
    if sort_by_date_desc:
        files.sort(key=lambda p: p.stem, reverse=True)
    else:
        files.sort(key=lambda p: p.stem)
    return files


def list_subdir_indexes(dir: Path) -> list[tuple[str, Path]]:
    """디렉터리 안 sub-dir의 _index.md 목록."""
    if not dir.exists():
        return []
    out = []
    for d in sorted(dir.iterdir()):
        if d.is_dir():
            idx = d / "_index.md"
            out.append((d.name, idx if idx.exists() else None))
    return out


def render_service_index_block(vault: Path, svc: str) -> str:
    svc_dir = vault / "wiki/services" / svc
    sections = []
    for cat in SERVICE_SUB_CATEGORIES:
        cat_dir = svc_dir / cat
        files = list_md_files(cat_dir)
        sub_idx = list_subdir_indexes(cat_dir)
        lines = [f"## {cat}"]
        if not files and not sub_idx:
            lines.append("- (없음)")
        else:
            for f in files:
                lines.append(f"- [[{f.stem}]]")
            for name, idx in sub_idx:
                if idx is not None:
                    lines.append(f"- [[{cat}/{name}/_index|{name}]]")
                else:
                    lines.append(f"- [[{cat}/{name}/]] (인덱스 없음)")
        sections.append("\n".join(lines))
    body = "\n\n".join(sections)
    today_s = today()
    return (
        f"<!-- generated:vault-index source=services/{svc}/ updated={today_s} -->\n"
        f"{body}\n"
        f"<!-- /generated -->"
    )


def render_process_index_block(vault: Path, process_type: str) -> str:
    proc_dir = vault / "wiki/processes" / process_type
    sort_desc = process_type in DATE_SORT_TYPES
    files = list_md_files(proc_dir, sort_by_date_desc=sort_desc)
    sub_idx = list_subdir_indexes(proc_dir)
    lines = []
    if not files and not sub_idx:
        lines.append("- (없음)")
    else:
        for f in files:
            lines.append(f"- [[{f.stem}]]")
        for name, idx in sub_idx:
            if idx is not None:
                lines.append(f"- [[{name}/_index|{name}]]")
            else:
                lines.append(f"- [[{name}/]] (인덱스 없음)")
    body = "\n".join(lines)
    today_s = today()
    return (
        f"<!-- generated:vault-index source=processes/{process_type}/ updated={today_s} -->\n"
        f"{body}\n"
        f"<!-- /generated -->"
    )


def render_hub_index_block(vault: Path, hub: str) -> str:
    """services/ 또는 processes/ hub."""
    hub_dir = vault / "wiki" / hub
    sub_idx = list_subdir_indexes(hub_dir)
    lines = []
    if not sub_idx:
        lines.append("- (없음)")
    else:
        for name, idx in sub_idx:
            if idx is not None:
                lines.append(f"- [[{hub}/{name}/_index|{name}]]")
            else:
                lines.append(f"- [[{hub}/{name}/]] (인덱스 없음)")
    body = "\n".join(lines)
    today_s = today()
    return (
        f"<!-- generated:vault-index source={hub}/ updated={today_s} -->\n"
        f"{body}\n"
        f"<!-- /generated -->"
    )


def new_service_index(svc: str, block: str) -> str:
    today_s = today()
    return (
        f"---\n"
        f"type: service-index\n"
        f"title: {svc}\n"
        f"canonical_id: service:{svc}\n"
        f"status: canonical\n"
        f"updated_at: {today_s}\n"
        f"service_id: {svc}\n"
        f"---\n\n"
        f"# {svc}\n\n"
        f"{block}\n\n"
        f"<!-- generated:harness-link source=team2/catalog/{svc}.yaml updated=N/A -->\n"
        f"(Sub 5에서 채움)\n"
        f"<!-- /generated -->\n"
    )


def new_process_index(process_type: str, block: str) -> str:
    today_s = today()
    return (
        f"---\n"
        f"type: process-index\n"
        f"title: {process_type}\n"
        f"canonical_id: process:{process_type}\n"
        f"status: canonical\n"
        f"updated_at: {today_s}\n"
        f"---\n\n"
        f"# {process_type}\n\n"
        f"{block}\n"
    )


def new_hub_index(hub: str, block: str) -> str:
    today_s = today()
    title_map = {"services": "서비스", "processes": "프로세스"}
    title = title_map.get(hub, hub)
    return (
        f"---\n"
        f"type: index\n"
        f"title: {title}\n"
        f"canonical_id: index:{hub}\n"
        f"status: canonical\n"
        f"updated_at: {today_s}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{block}\n"
    )


def update_existing(text: str, block: str, file_kind: str) -> tuple[str, str]:
    """기존 파일에 generated 블록 교체 또는 추가.

    Returns (new_text, status). status: replaced | inserted | skipped
    """
    if VAULT_INDEX_BLOCK_RE.search(text):
        new_text = VAULT_INDEX_BLOCK_RE.sub(block, text, count=1)
        # frontmatter updated_at 갱신
        new_text = re.sub(
            r'^(updated_at:\s*).*$',
            lambda m: f"{m.group(1)}{today()}",
            new_text,
            count=1,
            flags=re.MULTILINE,
        )
        return new_text, "replaced"
    # 본문이 거의 비어있으면 inserted
    if len(text.strip().splitlines()) <= 5:
        # frontmatter만 있는 수준 — block을 본문 끝에 추가
        new_text = text.rstrip() + "\n\n" + block + "\n"
        return new_text, "inserted"
    # 본문이 있고 generated block 없으면 skip + surface
    return text, "skipped"


def process_service(vault: Path, svc: str, dry_run: bool) -> dict:
    idx_path = vault / "wiki/services" / svc / "_index.md"
    block = render_service_index_block(vault, svc)
    if idx_path.exists():
        text = idx_path.read_text(encoding="utf-8")
        new_text, status = update_existing(text, block, "service")
        if status == "skipped":
            return {"file": str(idx_path.relative_to(vault)),
                    "status": "skipped",
                    "reason": "기존 _index.md에 generated block 없음 (사람 본문 보존)"}
        if not dry_run:
            idx_path.write_text(new_text, encoding="utf-8")
        return {"file": str(idx_path.relative_to(vault)), "status": status}
    if not dry_run:
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        idx_path.write_text(new_service_index(svc, block), encoding="utf-8")
    return {"file": str(idx_path.relative_to(vault)), "status": "created"}


def process_process(vault: Path, process_type: str, dry_run: bool) -> dict:
    idx_path = vault / "wiki/processes" / process_type / "_index.md"
    block = render_process_index_block(vault, process_type)
    if idx_path.exists():
        text = idx_path.read_text(encoding="utf-8")
        new_text, status = update_existing(text, block, "process")
        if status == "skipped":
            return {"file": str(idx_path.relative_to(vault)),
                    "status": "skipped",
                    "reason": "기존 _index.md에 generated block 없음"}
        if not dry_run:
            idx_path.write_text(new_text, encoding="utf-8")
        return {"file": str(idx_path.relative_to(vault)), "status": status}
    if not dry_run:
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        idx_path.write_text(new_process_index(process_type, block), encoding="utf-8")
    return {"file": str(idx_path.relative_to(vault)), "status": "created"}


def process_hub(vault: Path, hub: str, dry_run: bool) -> dict:
    idx_path = vault / "wiki" / hub / "_index.md"
    block = render_hub_index_block(vault, hub)
    if idx_path.exists():
        text = idx_path.read_text(encoding="utf-8")
        new_text, status = update_existing(text, block, "hub")
        if status == "skipped":
            return {"file": str(idx_path.relative_to(vault)),
                    "status": "skipped",
                    "reason": "기존 _index.md에 generated block 없음"}
        if not dry_run:
            idx_path.write_text(new_text, encoding="utf-8")
        return {"file": str(idx_path.relative_to(vault)), "status": status}
    if not dry_run:
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        idx_path.write_text(new_hub_index(hub, block), encoding="utf-8")
    return {"file": str(idx_path.relative_to(vault)), "status": "created"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--target", default="all",
                    choices=["services", "processes", "hubs", "all"])
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    vault = args.vault.resolve()
    dry_run = not args.apply
    results: list[dict] = []

    if args.target in ("services", "all"):
        svc_root = vault / "wiki/services"
        if svc_root.exists():
            for d in sorted(svc_root.iterdir()):
                if d.is_dir():
                    results.append(process_service(vault, d.name, dry_run))

    if args.target in ("processes", "all"):
        proc_root = vault / "wiki/processes"
        if proc_root.exists():
            for d in sorted(proc_root.iterdir()):
                if d.is_dir():
                    results.append(process_process(vault, d.name, dry_run))

    if args.target in ("hubs", "all"):
        results.append(process_hub(vault, "services", dry_run))
        results.append(process_hub(vault, "processes", dry_run))

    # report
    by_status: dict[str, list[dict]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)
    print(f"mode: {'dry-run' if dry_run else 'apply'}", file=sys.stderr)
    for st in ("created", "replaced", "inserted", "skipped"):
        rs = by_status.get(st, [])
        print(f"{st}: {len(rs)}", file=sys.stderr)
        for r in rs:
            extra = f" — {r.get('reason')}" if "reason" in r else ""
            print(f"  - {r['file']}{extra}", file=sys.stderr)

    # staging
    if not dry_run:
        changed = [vault / r["file"] for r in results
                   if r["status"] in ("created", "replaced", "inserted")]
        if changed:
            rel = [str(p.relative_to(vault)) for p in changed]
            subprocess.run(["git", "add", "--"] + rel, cwd=vault, check=False)
            print(f"staged {len(changed)} files", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 문법 점검**

```bash
python3 -m py_compile /Users/jm/Documents/workspace/team2/tools/generate_vault_indexes.py && echo OK
```

Expected: `OK`.

- [ ] **Step 3: --help 동작**

```bash
python3 /Users/jm/Documents/workspace/team2/tools/generate_vault_indexes.py --help
```

Expected: argparse usage (--vault, --target, --apply).

### Task 1.2: `tools/README.md` 갱신

**Files:**
- Modify: `REPO/tools/README.md`

- [ ] **Step 1: 섹션 추가**

기존 `tools/README.md` 끝에 추가:

```markdown

## generate_vault_indexes.py — vault `_index.md` 자동 생성

vault `services/{svc}/`, `processes/{type}/`, hub `_index.md`를 generated block 기반으로 생성·갱신.

### 사용법

\`\`\`bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# dry-run (기본)
python3 tools/generate_vault_indexes.py --vault "$VAULT"

# 실 실행
python3 tools/generate_vault_indexes.py --vault "$VAULT" --apply

# 부분 target
python3 tools/generate_vault_indexes.py --vault "$VAULT" --target services --apply
\`\`\`

### 동작

- `<!-- generated:vault-index ... -->` 블록만 자동 갱신
- 기존 _index.md에 generated block 없으면 skip + surface (사람 본문 보존)
- 없는 _index.md는 신규 생성 (frontmatter + block + harness-link placeholder)
- `--apply` 시 변경 파일만 git add

### 산출

- services/{svc}/_index.md
- processes/{type}/_index.md
- wiki/services/_index.md, wiki/processes/_index.md (hub)

### 의존성

Python 3.10+ stdlib만.
```

(위 백슬래시-`바깥` ``` 펜스는 실제 작성 시 평범한 ``` 펜스로 복원)

- [ ] **Step 2: 검증**

```bash
grep -c "generate_vault_indexes" /Users/jm/Documents/workspace/team2/tools/README.md
```

Expected: ≥ 3.

---

## Phase 2: dry-run 검증

### Task 2.1: dry-run 실 실행

- [ ] **Step 1: 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/generate_vault_indexes.py --vault "$VAULT" 2>&1 | head -40
```

Expected: stderr에 status별 (created/replaced/inserted/skipped) 카운트 + 각 파일 경로.

- [ ] **Step 2: 카운트 합리성**

다음 정도 예상:
- created: ~7 (없던 _index.md 신규)
- replaced: ~3 (기존 services/{caravan,shopping,tobe}/_index.md)
- skipped: 0 (사람 본문 충돌 없음)

실제 결과는 vault 상태에 따라 다름. skipped 있으면 사람 후속.

---

## Phase 3: apply + commit

### Task 3.1: 실 실행

- [ ] **Step 1: --apply**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/generate_vault_indexes.py --vault "$VAULT" --apply
```

Expected: 변경 파일이 git에 staged.

- [ ] **Step 2: staged 확인**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git status --short | grep -E "_index\.md$" | head -15
```

Expected: services/*/_index.md, processes/*/_index.md, hub _index.md 다수 staged.

- [ ] **Step 3: 샘플 diff**

```bash
git diff --cached wiki/services/aasm/_index.md
```

Expected: 신규 파일 전체 본문 출력 (frontmatter + generated block + harness-link placeholder).

- [ ] **Step 4: vault commit (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git commit -m "wiki: Sub 4 _index.md 자동 생성 (services/processes/hub)

services/{svc}/_index.md, processes/{type}/_index.md, hub services/processes _index.md 자동 생성 또는 generated:vault-index 블록 교체. harness-link 블록은 Sub 5 placeholder."
```

- [ ] **Step 5: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

### Task 3.2: harness commit

**Files:**
- `REPO/tools/generate_vault_indexes.py`
- `REPO/tools/README.md` (갱신)
- `REPO/docs/superpowers/plans/2026-05-27-vault-index-generator.md`

- [ ] **Step 1: staging**

```bash
cd /Users/jm/Documents/workspace/team2
git add tools/generate_vault_indexes.py tools/README.md docs/superpowers/plans/2026-05-27-vault-index-generator.md
git status --short | head
```

- [ ] **Step 2: commit (사용자 승인 후)**

```bash
git commit -m "tools/generate_vault_indexes: vault _index 자동 생성기 + Sub 4 plan

services/{svc}, processes/{type}, hubs 단위 _index.md 신규 생성 또는 generated:vault-index 블록 교체. 사람 작성 본문 보존."
```

- [ ] **Step 3: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

---

## Self-Review

**Spec 커버리지:**
- 도구 `generate_vault_indexes.py` (Task 1.1) ✓
- README 갱신 (Task 1.2) ✓
- services/{svc}/_index.md (Task 1.1 process_service) ✓
- processes/{type}/_index.md (Task 1.1 process_process) ✓
- hub _index.md (Task 1.1 process_hub) ✓
- generated block만 갱신 + 사람 본문 보존 (Task 1.1 update_existing) ✓
- skipped surface (update_existing return "skipped") ✓
- frontmatter updated_at 갱신 (Task 1.1 update_existing re.sub) ✓
- dry-run + apply (Task 1.1 main) ✓
- vault commit (Task 3.1) ✓
- harness commit (Task 3.2) ✓

**Placeholder 없음:** 모든 step 실 코드.

**타입 일관:**
- `process_*()` return dict: {"file", "status", ["reason"]}
- status enum: created | replaced | inserted | skipped
- target enum: services | processes | hubs | all
- VAULT_INDEX_BLOCK_RE / HARNESS_LINK_BLOCK_RE 정의 일관

빠진 부분 없음.

## 검증 기준

- 모든 services/{svc}/, processes/{type}/ 안 `_index.md` 존재
- generated:vault-index 블록 listing == 실제 dir 파일
- 기존 _index.md 본문(generated 블록 밖) 변경 없음
- frontmatter `updated_at` 갱신됨
- vault commit 1건, harness commit 1건
- AI footer 0건
