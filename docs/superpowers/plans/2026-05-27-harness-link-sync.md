# harness ↔ vault sync (Sub 5) 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `2026-05-27-harness-link-sync-design.md` 기반으로 `harness/tools/sync_harness_links.py`를 작성하고, vault `services/{svc}/_index.md`의 `<!-- generated:harness-link -->` 블록, 신규 `processes/team/_index.md`의 `<!-- generated:team-members -->` 블록, `wiki/_index.md`의 `<!-- generated:policy-index -->` 블록을 catalog/policies/team-members 데이터로 채운다.

**Architecture:** stdlib Python 단일 도구. catalog yaml은 정규식 shallow 파싱 (필요 필드만). team-members.md는 정규식 행 파싱. policies는 파일 listing + H1 다음 행 추출. dry-run 기본, `--apply` 명시 실 실행.

**Tech Stack:** Python 3 stdlib (`pathlib`, `re`, `argparse`, `subprocess`, `datetime`).

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- `VAULT` = `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`

**규칙:**
- harness branch = `feature/knowledge-scope-separation`
- 모든 commit 사용자 승인 후
- AI co-author footer 금지

---

## File Structure

### 신규 (harness)
- `REPO/tools/sync_harness_links.py` (~280 라인)

### 갱신 (harness)
- `REPO/tools/README.md` — sync_harness_links 섹션

### 신규/갱신 (vault, 도구 산출)
- `VAULT/wiki/services/{aasm,max}/_index.md` 등 harness-link 블록 채워짐
- `VAULT/wiki/processes/team/_index.md` 신규 생성
- `VAULT/wiki/_index.md` policy-index 블록 추가/갱신

---

## Phase 0: 사전 점검

### Task 0.1: 입력 파일 존재

- [ ] **Step 1: catalog + policies + team-members 확인**

```bash
ls /Users/jm/Documents/workspace/team2/catalog/*.yaml | wc -l
ls /Users/jm/Documents/workspace/team2/policies/*.md | wc -l
ls /Users/jm/Documents/workspace/team2/policies/team-members.md
```

Expected: catalog ≥ 9, policies ≥ 18, team-members.md 존재.

### Task 0.2: vault placeholder 확인

- [ ] **Step 1: services/{aasm,max}/_index.md placeholder 존재**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
grep -l "generated:harness-link" "$VAULT/wiki/services/aasm/_index.md" "$VAULT/wiki/services/max/_index.md"
```

Expected: 두 파일 모두 매치.

---

## Phase 1: 도구 구현

### Task 1.1: `sync_harness_links.py` 작성

**Files:**
- Create: `REPO/tools/sync_harness_links.py`

- [ ] **Step 1: 전체 본문 작성**

```python
#!/usr/bin/env python3
"""harness ↔ vault sync.

spec: docs/superpowers/specs/2026-05-27-harness-link-sync-design.md

생성·갱신 대상:
- services/{svc}/_index.md 의 generated:harness-link 블록
- processes/team/_index.md 의 generated:team-members 블록 (없으면 파일 신규 생성)
- wiki/_index.md 의 generated:policy-index 블록
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HARNESS_LINK_RE = re.compile(
    r'<!-- generated:harness-link[^>]*-->.*?<!-- /generated -->',
    re.DOTALL,
)
TEAM_MEMBERS_RE = re.compile(
    r'<!-- generated:team-members[^>]*-->.*?<!-- /generated -->',
    re.DOTALL,
)
POLICY_INDEX_RE = re.compile(
    r'<!-- generated:policy-index[^>]*-->.*?<!-- /generated -->',
    re.DOTALL,
)


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# -------- catalog yaml shallow parser --------

def parse_catalog_yaml(path: Path) -> dict:
    """필요 필드만 정규식 추출. nested owners 처리."""
    text = path.read_text(encoding="utf-8")
    out: dict = {}
    for key in ("service_id", "name", "type", "status"):
        m = re.search(rf'^{key}:\s*(.+)$', text, re.MULTILINE)
        if m:
            v = m.group(1).strip().strip('"').strip("'")
            # 인라인 주석 제거
            v = re.sub(r'\s+#.*$', '', v)
            out[key] = v.strip()
    # owners block
    owners: dict = {}
    om = re.search(r'^owners:\s*$\n((?:[ \t]+.+\n?)+)', text, re.MULTILINE)
    if om:
        block = om.group(1)
        for line in block.splitlines():
            line = line.rstrip()
            if not line.strip():
                continue
            # primary/backup/additional
            m2 = re.match(r'^[ \t]+(primary|backup|additional):\s*(.+?)(?:\s+#.*)?$', line)
            if m2:
                k = m2.group(1)
                v = m2.group(2).strip().strip('"').strip("'")
                owners[k] = v
                continue
            # stakeholders 리스트 (간단)
            m3 = re.match(r'^[ \t]+-\s*(.+?)(?:\s+#.*)?$', line)
            if m3:
                owners.setdefault("stakeholders", []).append(
                    m3.group(1).strip().strip('"').strip("'"))
    out["owners"] = owners
    return out


def parse_catalog_dir(catalog_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in sorted(catalog_dir.glob("*.yaml")):
        try:
            data = parse_catalog_yaml(f)
            sid = data.get("service_id") or f.stem
            out[sid] = data
        except Exception as e:
            print(f"WARN: catalog parse 실패 {f}: {e}", file=sys.stderr)
    return out


# -------- team-members parser --------

EMAIL_NAME_RE = re.compile(
    r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\w.+-]+)@[^|]+?\(\s*([\w.+-]+?)\s*\)?'
)


def parse_team_members(path: Path) -> tuple[dict[str, str], list[dict]]:
    """team-members.md 정규직·프리랜서 표 파싱.

    Returns (name_map, rows):
    - name_map: dict[email_or_id → '한글이름 (id)']
    - rows: list[{역할, 이름, id, email, 담당}]
    """
    text = path.read_text(encoding="utf-8")
    name_map: dict[str, str] = {}
    rows: list[dict] = []
    # 표 행: | 역할 | 이름 | email | 담당 |
    for m in re.finditer(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+@[^|]+)\s*\|\s*([^|]*?)\s*\|',
        text, re.MULTILINE,
    ):
        role, name, email_field, charge = m.groups()
        role = role.strip(); name = name.strip(); charge = charge.strip()
        # email_field 형식: "jmkim@aladin.co.kr" 또는 "jmkim@aladin.co.kr (YouTrack ID)"
        em = re.match(r'\s*([\w.+-]+)@[\w.-]+', email_field.strip())
        if not em:
            continue
        ident = em.group(1)
        if role in ("역할",):  # 헤더 행 skip
            continue
        if name in ("이름",):
            continue
        display = f"{name} ({ident})"
        full_email = email_field.strip().split()[0]
        name_map[full_email] = display
        name_map[ident] = display
        rows.append({"role": role, "name": name, "id": ident,
                     "email": full_email, "charge": charge})
    return name_map, rows


# -------- policies listing --------

POLICY_SKIP = set()  # 필요 시 제외 파일

def list_policies(policies_dir: Path) -> list[dict]:
    out = []
    for f in sorted(policies_dir.glob("*.md")):
        if f.name in POLICY_SKIP:
            continue
        # H1 다음 첫 본문 줄을 1행 요약으로
        lines = f.read_text(encoding="utf-8").splitlines()
        summary = ""
        seen_h1 = False
        for line in lines:
            if not seen_h1 and line.startswith("# "):
                seen_h1 = True
                continue
            if seen_h1 and line.strip():
                summary = line.strip()
                # link 마크다운 등 제거 — 간단히 첫 마침표 또는 80자 cut
                if "." in summary:
                    summary = summary.split(".")[0] + "."
                summary = summary[:120]
                break
        out.append({"name": f.stem, "path": str(f), "summary": summary})
    return out


# -------- block builders --------

def build_harness_link_block(svc: str, cat: dict, name_map: dict[str, str],
                              harness: Path) -> str:
    fields = cat
    owners = fields.get("owners", {})

    def lookup(v: str | None) -> str:
        if not v:
            return ""
        return name_map.get(v, v) or v

    primary = lookup(owners.get("primary"))
    backup = lookup(owners.get("backup"))
    additional = lookup(owners.get("additional"))
    stakeholders = [lookup(s) for s in owners.get("stakeholders", []) or []]

    owners_line = f"- 오너: {primary or '(미지정)'}"
    if backup:
        owners_line += f" · 백업: {backup}"
    if additional:
        owners_line += f" · 추가: {additional}"
    if stakeholders:
        owners_line += f" · 이해관계자: {' '.join(stakeholders)}"

    lines = [
        f"<!-- generated:harness-link source=team2/catalog/{svc}.yaml updated={today()} -->",
        f"- 이름: {fields.get('name', svc)}",
        f"- 분류: {fields.get('type', '(미지정)')}",
    ]
    if "status" in fields:
        lines.append(f"- 상태: {fields['status']}")
    cat_path = harness / "catalog" / f"{svc}.yaml"
    lines.append(f"- 카탈로그: [`catalog/{svc}.yaml`](file://{cat_path})")
    lines.append(owners_line)
    lines.append("<!-- /generated -->")
    return "\n".join(lines)


def build_team_members_block(rows: list[dict], catalog: dict[str, dict],
                              harness: Path) -> str:
    # 정규직만 (역할별 매칭은 단순)
    # 담당 서비스는 team-members.md의 charge 컬럼 그대로
    lines = [
        f"<!-- generated:team-members source=team2/policies/team-members.md updated={today()} -->",
        "| 역할 | 이름 | 담당 서비스 |",
        "|---|---|---|",
    ]
    for r in rows:
        if r["role"] in ("팀장", "디자이너", "기획자"):
            continue  # dev만
        if "프리랜서" in r["charge"]:
            continue
        display = f"{r['name']} ({r['id']})"
        lines.append(f"| {r['role']} | {display} | {r['charge']} |")
    lines.append("<!-- /generated -->")
    return "\n".join(lines)


def build_policy_index_block(policies: list[dict], harness: Path) -> str:
    lines = [
        f"<!-- generated:policy-index source=team2/policies/ updated={today()} -->",
    ]
    for p in policies:
        path = harness / "policies" / f"{p['name']}.md"
        summary = p.get("summary") or ""
        lines.append(f"- [`{p['name']}`](file://{path}) — {summary}")
    lines.append("<!-- /generated -->")
    return "\n".join(lines)


# -------- vault file updaters --------

def replace_or_skip(text: str, block_re: re.Pattern, new_block: str) -> tuple[str, str]:
    if block_re.search(text):
        new_text = block_re.sub(new_block, text, count=1)
        # frontmatter updated_at 갱신
        new_text = re.sub(
            r'^(updated_at:\s*).*$',
            lambda m: f"{m.group(1)}{today()}",
            new_text, count=1, flags=re.MULTILINE,
        )
        return new_text, "replaced"
    return text, "skipped"


def update_service_index(vault: Path, svc: str, cat: dict,
                          name_map: dict[str, str], harness: Path,
                          dry_run: bool) -> dict:
    idx = vault / "wiki/services" / svc / "_index.md"
    if not idx.exists():
        return {"file": str(idx.relative_to(vault)), "status": "missing",
                "reason": "_index.md 없음 (Sub 4 generate 필요)"}
    text = idx.read_text(encoding="utf-8")
    block = build_harness_link_block(svc, cat, name_map, harness)
    new_text, status = replace_or_skip(text, HARNESS_LINK_RE, block)
    if status == "skipped":
        return {"file": str(idx.relative_to(vault)), "status": "skipped",
                "reason": "generated:harness-link 블록 없음 (사람 본문 보존)"}
    if not dry_run:
        idx.write_text(new_text, encoding="utf-8")
    return {"file": str(idx.relative_to(vault)), "status": status}


def update_team_index(vault: Path, name_map: dict[str, str],
                       rows: list[dict], catalog: dict[str, dict],
                       harness: Path, dry_run: bool) -> dict:
    idx = vault / "wiki/processes/team/_index.md"
    block = build_team_members_block(rows, catalog, harness)
    if idx.exists():
        text = idx.read_text(encoding="utf-8")
        if TEAM_MEMBERS_RE.search(text):
            new_text, status = replace_or_skip(text, TEAM_MEMBERS_RE, block)
            if not dry_run:
                idx.write_text(new_text, encoding="utf-8")
            return {"file": str(idx.relative_to(vault)), "status": status}
        # 블록 없으면 본문 끝에 추가
        new_text = text.rstrip() + "\n\n" + block + "\n"
        if not dry_run:
            idx.write_text(new_text, encoding="utf-8")
        return {"file": str(idx.relative_to(vault)), "status": "inserted"}
    # 신규 생성
    today_s = today()
    body = (
        f"---\n"
        f"type: process-index\n"
        f"title: 팀\n"
        f"canonical_id: process:team\n"
        f"status: canonical\n"
        f"updated_at: {today_s}\n"
        f"---\n\n"
        f"# 팀\n\n"
        f"{block}\n"
    )
    if not dry_run:
        idx.parent.mkdir(parents=True, exist_ok=True)
        idx.write_text(body, encoding="utf-8")
    return {"file": str(idx.relative_to(vault)), "status": "created"}


def update_policy_index(vault: Path, policies: list[dict], harness: Path,
                         dry_run: bool) -> dict:
    idx = vault / "wiki/_index.md"
    if not idx.exists():
        return {"file": "wiki/_index.md", "status": "missing",
                "reason": "wiki/_index.md 없음"}
    text = idx.read_text(encoding="utf-8")
    block = build_policy_index_block(policies, harness)
    if POLICY_INDEX_RE.search(text):
        new_text, status = replace_or_skip(text, POLICY_INDEX_RE, block)
        if not dry_run:
            idx.write_text(new_text, encoding="utf-8")
        return {"file": str(idx.relative_to(vault)), "status": status}
    # 본문 끝에 신규 블록 추가
    new_text = text.rstrip() + "\n\n## 팀 정책 인덱스\n\n" + block + "\n"
    if not dry_run:
        idx.write_text(new_text, encoding="utf-8")
    return {"file": str(idx.relative_to(vault)), "status": "inserted"}


# -------- main --------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--harness", required=True, type=Path)
    ap.add_argument("--target", default="all",
                    choices=["services", "team", "policies", "all"])
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    vault = args.vault.resolve()
    harness = args.harness.resolve()
    dry_run = not args.apply

    catalog = parse_catalog_dir(harness / "catalog")
    name_map, rows = parse_team_members(harness / "policies/team-members.md")
    policies = list_policies(harness / "policies")

    results: list[dict] = []

    if args.target in ("services", "all"):
        for svc, cat in catalog.items():
            results.append(update_service_index(
                vault, svc, cat, name_map, harness, dry_run))

    if args.target in ("team", "all"):
        results.append(update_team_index(
            vault, name_map, rows, catalog, harness, dry_run))

    if args.target in ("policies", "all"):
        results.append(update_policy_index(vault, policies, harness, dry_run))

    # report
    by_status: dict[str, list[dict]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)
    print(f"mode: {'dry-run' if dry_run else 'apply'}", file=sys.stderr)
    for st in ("created", "replaced", "inserted", "skipped", "missing"):
        rs = by_status.get(st, [])
        print(f"{st}: {len(rs)}", file=sys.stderr)
        for r in rs:
            extra = f" — {r['reason']}" if "reason" in r else ""
            print(f"  - {r['file']}{extra}", file=sys.stderr)

    if not dry_run:
        changed = [r["file"] for r in results
                   if r["status"] in ("created", "replaced", "inserted")]
        if changed:
            subprocess.run(["git", "add", "--"] + changed, cwd=vault, check=False)
            print(f"staged {len(changed)} files", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 문법 점검**

```bash
python3 -m py_compile /Users/jm/Documents/workspace/team2/tools/sync_harness_links.py && echo OK
```

Expected: `OK`.

- [ ] **Step 3: --help 동작**

```bash
python3 /Users/jm/Documents/workspace/team2/tools/sync_harness_links.py --help
```

Expected: argparse usage (--vault, --harness, --target, --apply).

### Task 1.2: `tools/README.md` 갱신

**Files:**
- Modify: `REPO/tools/README.md`

- [ ] **Step 1: 섹션 추가**

기존 `tools/README.md` 끝에 추가 (실제 작성 시 inner ``` 펜스 복원):

```markdown

## sync_harness_links.py — harness ↔ vault sync

harness `catalog/*.yaml`, `policies/team-members.md`, `policies/*.md`를 vault 안 generated 블록에 반영.

### 사용법

\`\`\`bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
REPO="/Users/jm/Documents/workspace/team2"

# dry-run
python3 tools/sync_harness_links.py --vault "$VAULT" --harness "$REPO"

# 실 실행
python3 tools/sync_harness_links.py --vault "$VAULT" --harness "$REPO" --apply

# target 한정
python3 tools/sync_harness_links.py --vault "$VAULT" --harness "$REPO" --target services --apply
\`\`\`

### 갱신 대상 블록

- `services/{svc}/_index.md` 의 `<!-- generated:harness-link -->`
- `processes/team/_index.md` 의 `<!-- generated:team-members -->` (없으면 파일 신규 생성)
- `wiki/_index.md` 의 `<!-- generated:policy-index -->` (없으면 본문 끝에 추가)

### 동작

- catalog yaml은 정규식 shallow 파싱 (service_id, name, type, status, owners.{primary,backup,additional,stakeholders})
- team-members.md 정규직 표 파싱 + 이메일 → '한글이름 (id)' 매핑
- policies/*.md 파일 listing + H1 다음 첫 행 = 1행 요약
- 기존 _index.md에 해당 블록 없으면 skip + surface (services 케이스)

### 의존성

Python 3.10+ stdlib.
```

- [ ] **Step 2: 검증**

```bash
grep -c "sync_harness_links" /Users/jm/Documents/workspace/team2/tools/README.md
```

Expected: ≥ 3.

---

## Phase 2: dry-run 검증

### Task 2.1: dry-run

- [ ] **Step 1: 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/sync_harness_links.py \
  --vault "$VAULT" \
  --harness /Users/jm/Documents/workspace/team2 2>&1 | head -40
```

Expected: status별 카운트
- services: 9 (catalog 파일 수와 일치, replaced/skipped/missing 분포)
- team: 1 (created or replaced or inserted)
- policy: 1 (replaced or inserted)

- [ ] **Step 2: missing/skipped 검토**

services에서 `missing` (services/{svc}/_index.md 없음) 또는 `skipped` (블록 없음) row 확인:
- Sub 4에서 신규 생성된 aasm/max → replaced 예상
- Sub 4에서 skipped된 caravan/shopping/tobe → skipped (사람 본문에 harness-link block placeholder 없음)
- catalog에 있지만 vault dir 없는 서비스 (예: naru, bazaar, blog) → missing

---

## Phase 3: apply + commit

### Task 3.1: apply

- [ ] **Step 1: 실 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/sync_harness_links.py \
  --vault "$VAULT" \
  --harness /Users/jm/Documents/workspace/team2 --apply 2>&1 | head -30
```

Expected: status별 + staged 카운트.

- [ ] **Step 2: 샘플 diff**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git diff --cached wiki/services/max/_index.md | head -30
git diff --cached wiki/processes/team/_index.md 2>/dev/null | head -20
git diff --cached wiki/_index.md | head -25
```

Expected: harness-link 블록 안에 이름·분류·오너 등 채워짐. team-members 표·policy-index 표 출력.

- [ ] **Step 3: vault commit (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git commit -m "wiki: Sub 5 harness-link · team-members · policy-index 블록 채움

services/{aasm,max}/_index.md harness-link 블록 catalog 데이터로 채움. processes/team/_index.md 신규 생성. wiki/_index.md policy-index 블록 추가/갱신."
```

- [ ] **Step 4: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

### Task 3.2: harness commit

**Files:**
- `REPO/tools/sync_harness_links.py`
- `REPO/tools/README.md`
- `REPO/docs/superpowers/plans/2026-05-27-harness-link-sync.md`

- [ ] **Step 1: staging + commit (사용자 승인 후)**

```bash
cd /Users/jm/Documents/workspace/team2
git add tools/sync_harness_links.py tools/README.md docs/superpowers/plans/2026-05-27-harness-link-sync.md
git commit -m "tools/sync_harness_links: harness ↔ vault sync 도구 + Sub 5 plan

catalog yaml + team-members + policies를 shallow 파싱해 vault 안 generated 블록 채움. stdlib only. dry-run 기본·--apply 명시 실행."
```

- [ ] **Step 2: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

---

## Self-Review

**Spec 커버리지:**
- 도구 `sync_harness_links.py` (Task 1.1) ✓
- README 갱신 (Task 1.2) ✓
- catalog yaml shallow 파싱 (parse_catalog_yaml) ✓
- team-members 파싱 + 이메일 → 한글이름 매핑 (parse_team_members) ✓
- policies listing + 요약 (list_policies) ✓
- services 블록 갱신 (update_service_index) ✓
- team 블록 생성/갱신 (update_team_index) ✓
- policy-index 블록 추가/갱신 (update_policy_index) ✓
- skipped surface (services missing/skipped) ✓
- vault commit + harness commit ✓

**Placeholder 없음:** 모든 step 실 코드.

**타입 일관:**
- catalog dict 키: `service_id, name, type, status, owners{primary,backup,additional,stakeholders}`
- team-members rows: `{role, name, id, email, charge}`
- policies list: `[{name, path, summary}]`
- status enum: created | replaced | inserted | skipped | missing
- 모두 일관.

빠진 부분 없음.

## 검증 기준

- services 9개 중 placeholder 있는 것은 replaced
- processes/team/_index.md 생성 또는 갱신
- wiki/_index.md policy-index 블록 존재
- 사람 본문 변경 0
- vault commit 1건, harness commit 1건
- AI footer 0건
