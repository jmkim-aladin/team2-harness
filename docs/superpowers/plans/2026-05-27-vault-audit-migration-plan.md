# vault 감사·분류 매트릭스 (Sub 2) 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `2026-05-27-vault-audit-migration-plan-design.md`에 정의된 분류 룰을 구현하는 `harness/tools/audit_vault.py`를 작성하고, vault 607개 md 파일 분류 결과를 `migration-plan.md` + `migration-plan.json`으로 산출한다.

**Architecture:** stdlib only Python 단일 파일 도구. 입력 = vault 경로 + catalog 디렉터리. 처리 = filename prefix + dir + frontmatter 기반 룰 매핑. 출력 = markdown 표 + json. 실제 이관·wikilink 재작성은 Sub 3 비범위.

**Tech Stack:** Python 3 (stdlib only — `pathlib`, `re`, `json`, `argparse`, `collections`). 단위 테스트는 inline fixtures.

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- `VAULT` = `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`

**규칙:**
- harness branch = `feature/knowledge-scope-separation`
- 모든 commit은 사용자 승인 후
- AI co-author footer 금지
- vault commit과 harness commit 분리

---

## File Structure

### 신규 (harness)
- `REPO/tools/audit_vault.py` — 분류 도구 (단일 Python 파일, ~250 라인)
- `REPO/tools/README.md` — 도구 사용법 + 검토 절차

### 신규 (vault)
- `VAULT/wiki/guides/_audit/migration-plan.md` — 분류 결과 markdown (도구 출력)
- `VAULT/wiki/guides/_audit/migration-plan.json` — 분류 결과 json (도구 출력)

### 갱신 없음

기존 vault 파일 일체 손대지 않음 (이관은 Sub 3).

---

## Phase 0: 사전 점검

### Task 0.1: harness `tools/` 디렉터리 확인

**Files:** N/A

- [ ] **Step 1: 디렉터리 존재 확인**

```bash
ls -d /Users/jm/Documents/workspace/team2/tools 2>/dev/null && echo "exists" || echo "create"
```

Expected: 보통 `create` (없음). 없으면 다음 step에서 생성.

- [ ] **Step 2: 디렉터리 생성 (필요 시)**

```bash
mkdir -p /Users/jm/Documents/workspace/team2/tools
```

### Task 0.2: vault `_audit/` 디렉터리 확인

- [ ] **Step 1: 존재 확인**

```bash
ls -d "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/_audit" 2>/dev/null && echo "exists" || echo "create"
```

Expected: `create`. 도구가 출력 디렉터리 자동 생성하지만 사전 확인.

### Task 0.3: vault md 파일 총수 baseline

- [ ] **Step 1: 카운트**

```bash
find "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki" -type f -name '*.md' | wc -l
```

Expected: ~607. 도구 출력 row 수와 비교 baseline. 도구 자기 출력(`_audit/migration-plan.md`) 추가되면 +1.

---

## Phase 1: `audit_vault.py` 구현

### Task 1.1: 도구 단일 파일 작성

**Files:**
- Create: `REPO/tools/audit_vault.py`

- [ ] **Step 1: 전체 본문 작성**

Write 도구로 다음 본문 그대로 작성:

```python
#!/usr/bin/env python3
"""vault 파일 감사·분류 도구.

spec: docs/superpowers/specs/2026-05-27-vault-audit-migration-plan-design.md

Usage:
    python3 tools/audit_vault.py \\
        --vault "/Users/.../iCloud~md~obsidian/Documents/team2" \\
        --catalog catalog/ \\
        --output-md "<vault>/wiki/guides/_audit/migration-plan.md" \\
        --output-json "<vault>/wiki/guides/_audit/migration-plan.json"
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# 서비스 prefix → catalog service_id
SERVICE_PREFIX = {
    "tobe": "tobe",
    "web": "shopping",          # web-aladin = shopping
    "web-aladin": "shopping",
    "max": "max",
    "aasm": "aasm",
    "shopping": "shopping",
    "caravan": "caravan",
    "naru": "naru",
    "bazaar": "bazaar",
    "storefront": "storefront",
    "b2b-store": "storefront",
    "blog": "blog",
    "bookple": "blog",
}

# guides/ 잔류 메타 파일명 (서비스 prefix 매치 안 되는 위키 운영 메타)
GUIDES_META_KEEP = {
    "taxonomy.md", "frontmatter-spec.md", "document-placement.md",
    "skills-integration.md", "harness-link-protocol.md",
    "ai-human-readable-structure.md", "lint-wiki-spec.md",
    "lint-and-stale-policy.md", "domain-term-linking-rule.md",
    "daily-meeting-operating-rule.md", "generated-block-policy.md",
    "graphify-sidecar-policy.md", "projection-policy.md",
    "incident-report-rule.md", "business-process-knowledge-document-rule.md",
    "local-wiki-git-management.md", "semantic-knowledge-graph-rule.md",
    "harness-catalog-mirror-rule.md",
}

# 자동 폐기 디렉터리
AUTO_DELETE_DIRS = {"indexes"}

# 사람 판정 디렉터리 (action=review)
REVIEW_DIRS = {
    "briefs", "execution", "archive", "exports", "patterns",
    "imports", "templates", "tasks", "usecases", "processes",
    "projects",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    """간이 frontmatter 파싱. stdlib only — yaml 미사용."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("\"'")
    return fm


def detect_service(filename: str, fm: dict[str, str]) -> tuple[str | None, str]:
    """파일명 prefix + frontmatter로 service 추정. (service_id, source) 반환."""
    if "service" in fm:
        sid = fm["service"]
        if sid in set(SERVICE_PREFIX.values()):
            return sid, "frontmatter"
    if "service_id" in fm:
        sid = fm["service_id"]
        if sid in set(SERVICE_PREFIX.values()):
            return sid, "frontmatter"
    name = filename.lower()
    # 긴 prefix 먼저 매치 (web-aladin > web, b2b-store > blog)
    for prefix in sorted(SERVICE_PREFIX.keys(), key=len, reverse=True):
        if name.startswith(prefix + "-") or name == prefix + ".md":
            return SERVICE_PREFIX[prefix], f"prefix={prefix}"
    return None, "unmatched"


def strip_service_prefix(filename: str, service: str | None) -> str:
    """filename에서 서비스 prefix 제거. tobe-foo-bar.md → foo-bar.md"""
    if not service:
        return filename
    # 매핑 키 중 이 service로 가는 prefix 모두 시도, 긴 것부터
    candidates = [p for p, s in SERVICE_PREFIX.items() if s == service]
    candidates.sort(key=len, reverse=True)
    for p in candidates:
        lo = filename.lower()
        if lo.startswith(p + "-"):
            return filename[len(p) + 1:]
    return filename


def classify(rel_path: Path, fm: dict[str, str]) -> dict:
    """단일 파일 분류. dict row 반환."""
    parts = rel_path.parts
    if parts[0] != "wiki" or len(parts) < 2:
        return {
            "src": str(rel_path), "dst": None, "action": "review",
            "confidence": "low", "service": None, "category": None,
            "reason": f"unexpected path layout: {rel_path}",
        }
    top = parts[1]
    name = parts[-1]
    service, src_hint = detect_service(name, fm)
    stripped = strip_service_prefix(name, service)

    # _audit/ 자기 제외
    if top == "guides" and len(parts) > 2 and parts[2] == "_audit":
        return None

    # 자동 폐기
    if top in AUTO_DELETE_DIRS:
        return {
            "src": str(rel_path), "dst": None, "action": "delete",
            "confidence": "high", "service": service, "category": top,
            "reason": f"{top}/ 디렉터리 = Sub 4에서 자동 재생성 대상",
        }

    # processes 1:1
    process_map = {
        "daily": "processes/daily",
        "meetings": "processes/meetings",
        "okr": "processes/okr",
        "incidents": "processes/incidents",
        "capacity": "processes/capacity",
    }
    if top in process_map:
        dst_dir = process_map[top]
        # okr 이미 위치
        if top == "okr":
            return {
                "src": str(rel_path), "dst": str(rel_path),
                "action": "keep", "confidence": "high",
                "service": service, "category": "processes/okr",
                "reason": "okr/ 이미 새 위치 (Sub 0 이관 시점)",
            }
        return {
            "src": str(rel_path), "dst": f"wiki/{dst_dir}/{'/'.join(parts[2:])}",
            "action": "move", "confidence": "high",
            "service": service, "category": dst_dir,
            "reason": f"dir={top} → {dst_dir}",
        }

    # tickets
    if top == "tickets":
        # frontmatter의 ticket_status 또는 status 우선
        status = fm.get("ticket_status") or fm.get("status")
        if status not in {"auto-prep", "in-progress", "done", "backlog"}:
            status = "in-progress"  # 기본 (수동 검토 시 정정)
        return {
            "src": str(rel_path),
            "dst": f"wiki/processes/tickets/{status}/{name}",
            "action": "move", "confidence": "medium",
            "service": service, "category": f"processes/tickets/{status}",
            "reason": f"tickets/ + ticket_status={status} (없으면 기본 in-progress)",
        }

    # service 매핑 가능한 dir
    service_dirs = {
        "domains": "domains",
        "proposals": "proposals",
        "decisions": "decisions",
        "inventory": "analysis",     # 인벤토리는 해석 layer로 흡수
    }
    if top in service_dirs:
        if not service:
            return {
                "src": str(rel_path), "dst": None, "action": "review",
                "confidence": "low", "service": None, "category": top,
                "reason": f"{top}/ 디렉터리지만 service prefix 매치 안 됨",
            }
        cat = service_dirs[top]
        return {
            "src": str(rel_path),
            "dst": f"wiki/services/{service}/{cat}/{stripped}",
            "action": "move", "confidence": "high",
            "service": service, "category": f"services/{service}/{cat}",
            "reason": f"dir={top}, prefix={src_hint}",
        }

    # contracts (subdir: apis|stored-procedures|tables / svc / files)
    if top == "contracts":
        # contracts/{type}/{svc}/...
        if len(parts) >= 5:  # wiki/contracts/{type}/{svc}/{file}
            svc_hint = parts[3].lower()
            mapped = SERVICE_PREFIX.get(svc_hint)
            if mapped:
                return {
                    "src": str(rel_path),
                    "dst": f"wiki/services/{mapped}/analysis/{'/'.join(parts[4:])}",
                    "action": "review", "confidence": "medium",
                    "service": mapped, "category": f"services/{mapped}/analysis",
                    "reason": f"contracts/{parts[2]}/{svc_hint} — raw enumeration이면 delete 사람 판정",
                }
        return {
            "src": str(rel_path), "dst": None, "action": "review",
            "confidence": "low", "service": service, "category": "contracts",
            "reason": "contracts/ 구조 복잡, 사람 판정",
        }

    # services (단일 .md)
    if top == "services":
        if service and name.lower() == f"{service}.md":
            return {
                "src": str(rel_path),
                "dst": f"wiki/services/{service}/_index.md",
                "action": "merge", "confidence": "high",
                "service": service, "category": f"services/{service}",
                "reason": "단일 .md → 새 _index.md로 병합",
            }
        if len(parts) >= 3:
            inner = parts[2].lower()
            mapped = SERVICE_PREFIX.get(inner.replace(".md", ""))
            if mapped:
                return {
                    "src": str(rel_path),
                    "dst": f"wiki/services/{mapped}/_index.md",
                    "action": "merge", "confidence": "medium",
                    "service": mapped, "category": f"services/{mapped}",
                    "reason": "기존 services/ 산하 파일 → 새 _index.md 병합 검토",
                }
        return {
            "src": str(rel_path), "dst": None, "action": "review",
            "confidence": "low", "service": service, "category": "services",
            "reason": "기존 services/ 구조 — 사람 판정",
        }

    # guides — 메타 vs 서비스 prefix
    if top == "guides":
        # 잔류 메타
        if name in GUIDES_META_KEEP:
            return {
                "src": str(rel_path),
                "dst": str(rel_path),
                "action": "keep", "confidence": "high",
                "service": None, "category": "guides",
                "reason": "위키 운영 메타 가이드",
            }
        if service:
            return {
                "src": str(rel_path), "dst": None,
                "action": "review", "confidence": "medium",
                "service": service, "category": "guides",
                "reason": f"guides/+prefix={service} — domains/ vs processes/ 사람 판정",
            }
        return {
            "src": str(rel_path), "dst": None,
            "action": "review", "confidence": "low",
            "service": None, "category": "guides",
            "reason": "guides/ 메타 후보, prefix 매치 안 됨 — 사람 판정",
        }

    # glossary
    if top == "glossary":
        return {
            "src": str(rel_path),
            "dst": str(rel_path),
            "action": "keep", "confidence": "high",
            "service": None, "category": "glossary",
            "reason": "glossary/ 잔류",
        }

    # 사람 판정 dir
    if top in REVIEW_DIRS:
        return {
            "src": str(rel_path), "dst": None,
            "action": "review", "confidence": "low",
            "service": service, "category": top,
            "reason": f"{top}/ 디렉터리 — 사람 판정",
        }

    # fallback
    return {
        "src": str(rel_path), "dst": None,
        "action": "review", "confidence": "low",
        "service": service, "category": top,
        "reason": f"룰 매치 안 됨 (top={top})",
    }


def collect_files(vault: Path) -> list[Path]:
    """vault/wiki/**/*.md 수집 (자기 제외)."""
    wiki = vault / "wiki"
    out = []
    for p in wiki.rglob("*.md"):
        rel = p.relative_to(vault)
        # _audit 자기 제외
        if "_audit" in rel.parts:
            continue
        out.append(rel)
    return sorted(out)


def render_md(rows: list[dict]) -> str:
    """markdown 산출물 렌더."""
    # summary
    by_svc = defaultdict(Counter)
    for r in rows:
        by_svc[r.get("service") or "unknown"][r["action"]] += 1
    services = sorted(by_svc.keys())

    lines = [
        "---",
        "type: audit-report",
        "title: vault 마이그레이션 분류표",
        "canonical_id: audit:vault-migration-plan",
        "status: draft",
        "updated_at: 2026-05-27",
        "---",
        "",
        "# vault 마이그레이션 분류표",
        "",
        f"총 {len(rows)}개 파일. 도구: `harness/tools/audit_vault.py`. "
        "룰 기반 자동 분류 1차. `action=review` row는 사람 검토 후 확정.",
        "",
        "## 요약",
        "",
        "| service | total | move | merge | keep | delete | review |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for svc in services:
        c = by_svc[svc]
        total = sum(c.values())
        lines.append(
            f"| {svc} | {total} | {c['move']} | {c['merge']} | "
            f"{c['keep']} | {c['delete']} | {c['review']} |"
        )
    lines += ["", ""]

    # 서비스별 섹션
    action_order = ["delete", "review", "merge", "keep", "move"]
    by_svc_rows: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_svc_rows[r.get("service") or "unknown"].append(r)
    for svc in services:
        lines += [f"## {svc}", ""]
        lines += ["| 현 경로 | 제안 경로 | action | confidence | 메모 |",
                  "|---|---|---|---|---|"]
        svc_rows = by_svc_rows[svc]
        svc_rows.sort(key=lambda r: (action_order.index(r["action"]), r["src"]))
        for r in svc_rows:
            dst = r["dst"] or "(사람 판정 필요)"
            memo = r["reason"].replace("|", "\\|")
            lines.append(
                f"| {r['src']} | {dst} | {r['action']} | {r['confidence']} | {memo} |"
            )
        lines += [""]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--catalog", required=True, type=Path,
                    help="harness catalog/ 디렉터리 (현재는 미사용, 미래 확장용)")
    ap.add_argument("--output-md", required=True, type=Path)
    ap.add_argument("--output-json", required=True, type=Path)
    args = ap.parse_args()

    vault = args.vault.resolve()
    files = collect_files(vault)
    rows: list[dict] = []
    for rel in files:
        text = (vault / rel).read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        row = classify(rel, fm)
        if row is None:
            continue
        rows.append(row)

    # 출력 디렉터리 생성
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_md(rows), encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # stderr summary
    total = len(rows)
    actions = Counter(r["action"] for r in rows)
    print(f"total={total} actions={dict(actions)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 문법 점검**

```bash
python3 -m py_compile /Users/jm/Documents/workspace/team2/tools/audit_vault.py && echo "OK"
```

Expected: `OK`. 문법 오류 0.

- [ ] **Step 3: --help 동작 확인**

```bash
python3 /Users/jm/Documents/workspace/team2/tools/audit_vault.py --help
```

Expected: argparse usage 출력 (required: --vault, --catalog, --output-md, --output-json).

### Task 1.2: `tools/README.md` 작성

**Files:**
- Create: `REPO/tools/README.md`

- [ ] **Step 1: 작성**

```markdown
# harness tools

팀 하네스 보조 도구 모음. 일회성 또는 정기 실행용 스크립트.

## audit_vault.py — vault 분류 매트릭스 생성

vault 내 모든 md를 새 택소노미에 대응시킨 분류표 생성.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

python3 tools/audit_vault.py \
  --vault "$VAULT" \
  --catalog catalog/ \
  --output-md  "$VAULT/wiki/guides/_audit/migration-plan.md" \
  --output-json "$VAULT/wiki/guides/_audit/migration-plan.json"
```

### 출력

- `migration-plan.md` — 사람 검토용 (서비스별 섹션 + 정렬 + 요약)
- `migration-plan.json` — Sub 3 입력용

### 분류 룰

spec `docs/superpowers/specs/2026-05-27-vault-audit-migration-plan-design.md` 참조.

요약:
- service prefix(`tobe-`, `web-aladin-`, `max-`, `aasm-`, `shopping-`, `caravan-`, `naru-`, `bazaar-`, `storefront-`, `b2b-store-`, `blog-`, `bookple-`) → 해당 서비스 dir
- 디렉터리(`daily/`, `meetings/`, `okr/`, `incidents/`, `capacity/`) → `processes/{name}/`
- `domains/`, `proposals/`, `decisions/`, `inventory/` → `services/{svc}/{...}`
- `indexes/` → DELETE (Sub 4 재생성)
- `briefs/`, `execution/`, `archive/`, `exports/`, `patterns/`, `imports/`, `templates/`, `tasks/`, `usecases/`, `projects/`, `processes/`, `contracts/`, `services/` (기존) → 사람 판정 (`action=review`)
- guides/ 메타 잔류, guides/ 서비스 prefix 사람 판정

### 검토 절차

1. 도구 실행 (위)
2. `migration-plan.md` 열어 `action=review` row 확정 — `제안 경로` 셀 채우고 `action` 변경
3. 검토 끝나면 도구 재실행하지 말고 json을 수동 갱신 또는 Sub 3 입력으로 직접 사용

### 의존성

Python 3.10+ stdlib만 사용. 외부 패키지 불필요.
```

- [ ] **Step 2: 검증**

```bash
ls -la /Users/jm/Documents/workspace/team2/tools/README.md
wc -l /Users/jm/Documents/workspace/team2/tools/README.md
```

Expected: 존재, 약 40~50 라인.

---

## Phase 2: 도구 실행 + 산출물 생성

### Task 2.1: 작은 fixture 단위 테스트 (스모크)

**Files:** N/A (임시 테스트)

- [ ] **Step 1: 임시 vault fixture 생성**

```bash
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/wiki/domains" "$TMPDIR/wiki/daily" "$TMPDIR/wiki/guides" "$TMPDIR/wiki/indexes"
cat > "$TMPDIR/wiki/domains/tobe-content-note-pipeline.md" <<'EOF'
---
type: domain-index
title: 투비 콘텐츠 노트 파이프라인
---
본문.
EOF
cat > "$TMPDIR/wiki/daily/2026-05-27.md" <<'EOF'
---
type: daily
---
EOF
cat > "$TMPDIR/wiki/guides/taxonomy.md" <<'EOF'
---
type: guide
---
EOF
cat > "$TMPDIR/wiki/indexes/services.md" <<'EOF'
---
type: index
---
EOF
echo "$TMPDIR"
```

Expected: 임시 디렉터리 경로 출력. 4개 fixture 파일 생성.

- [ ] **Step 2: 도구 실행**

```bash
python3 /Users/jm/Documents/workspace/team2/tools/audit_vault.py \
  --vault "$TMPDIR" \
  --catalog /Users/jm/Documents/workspace/team2/catalog/ \
  --output-md  "$TMPDIR/wiki/guides/_audit/migration-plan.md" \
  --output-json "$TMPDIR/wiki/guides/_audit/migration-plan.json"
```

Expected: stderr에 `total=4 actions={'move': 2, 'keep': 1, 'delete': 1}` 비슷.

- [ ] **Step 3: json 점검**

```bash
python3 -c "
import json
rows = json.load(open('$TMPDIR/wiki/guides/_audit/migration-plan.json'))
for r in rows:
    print(r['src'], '->', r['dst'], r['action'], r['service'])
"
```

Expected (순서 무관):
```
wiki/daily/2026-05-27.md -> wiki/processes/daily/2026-05-27.md move None
wiki/domains/tobe-content-note-pipeline.md -> wiki/services/tobe/domains/content-note-pipeline.md move tobe
wiki/guides/taxonomy.md -> wiki/guides/taxonomy.md keep None
wiki/indexes/services.md -> None delete None
```

- [ ] **Step 4: cleanup**

```bash
rm -rf "$TMPDIR"
echo "cleaned"
```

### Task 2.2: 실 vault 실행

**Files:**
- Create: `VAULT/wiki/guides/_audit/migration-plan.md`
- Create: `VAULT/wiki/guides/_audit/migration-plan.json`

- [ ] **Step 1: 도구 실행**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 /Users/jm/Documents/workspace/team2/tools/audit_vault.py \
  --vault "$VAULT" \
  --catalog /Users/jm/Documents/workspace/team2/catalog/ \
  --output-md  "$VAULT/wiki/guides/_audit/migration-plan.md" \
  --output-json "$VAULT/wiki/guides/_audit/migration-plan.json"
```

Expected: stderr에 `total=607 actions={...}` 같은 요약. delete/review 카운트 surface.

- [ ] **Step 2: 산출물 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
wc -l "$VAULT/wiki/guides/_audit/migration-plan.md"
python3 -c "
import json
rows = json.load(open('$VAULT/wiki/guides/_audit/migration-plan.json'))
print('total:', len(rows))
from collections import Counter
print('by action:', Counter(r['action'] for r in rows))
print('by service:', Counter(r.get('service') or 'unknown' for r in rows))
"
```

Expected: md 약 700+ 라인 (요약 + 서비스별 표), json 록 약 607 row.

- [ ] **Step 3: 일관성 검증**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
md_count=$(find "$VAULT/wiki" -type f -name '*.md' | grep -v '_audit/' | wc -l | tr -d ' ')
json_count=$(python3 -c "import json; print(len(json.load(open('$VAULT/wiki/guides/_audit/migration-plan.json'))))")
echo "md files: $md_count, json rows: $json_count"
test "$md_count" = "$json_count" && echo "OK" || echo "MISMATCH"
```

Expected: `OK`. md 파일 수 == json row 수.

- [ ] **Step 4: action=move dst prefix 검증**

```bash
python3 -c "
import json
rows = json.load(open('$VAULT/wiki/guides/_audit/migration-plan.json'.replace('\$VAULT', '/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2')))
bad = [r for r in rows if r['action'] == 'move' and not (r['dst'] or '').startswith(('wiki/processes/', 'wiki/services/', 'wiki/projects/', 'wiki/guides/', 'wiki/glossary/'))]
print('bad move count:', len(bad))
for b in bad[:5]: print(b)
"
```

Expected: `bad move count: 0`. 모든 move dst가 새 택소노미 prefix.

---

## Phase 3: commit

### Task 3.1: harness commit (tools)

**Files:**
- `REPO/tools/audit_vault.py`
- `REPO/tools/README.md`
- `REPO/docs/superpowers/plans/2026-05-27-vault-audit-migration-plan.md` (본 plan 자체)

- [ ] **Step 1: status 확인**

```bash
cd /Users/jm/Documents/workspace/team2
git status --short | grep -E "tools/|docs/superpowers/plans/2026-05-27-vault-audit"
```

Expected: 3개 untracked.

- [ ] **Step 2: staging**

```bash
git add tools/audit_vault.py tools/README.md docs/superpowers/plans/2026-05-27-vault-audit-migration-plan.md
git status --short | head -10
```

Expected: 3개 A staged.

- [ ] **Step 3: commit (사용자 승인 후)**

```bash
git commit -m "tools/audit_vault: vault 분류 매트릭스 생성 도구 + Sub 2 plan

stdlib only Python 단일 파일. filename prefix + 디렉터리 기반 룰 매핑으로 vault 파일을 새 택소노미로 자동 분류, 사람 검토 게이트는 action=review surface로 분리."
```

- [ ] **Step 4: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo "BAD" || echo "OK"
```

Expected: `OK`.

### Task 3.2: vault commit (audit outputs)

**Files:**
- `VAULT/wiki/guides/_audit/migration-plan.md`
- `VAULT/wiki/guides/_audit/migration-plan.json`

- [ ] **Step 1: vault staging**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/guides/_audit/migration-plan.md wiki/guides/_audit/migration-plan.json
git status --short | grep _audit
```

Expected: 2개 A staged.

- [ ] **Step 2: commit (사용자 승인 후)**

```bash
git commit -m "wiki/guides/_audit: 마이그레이션 분류표 1차 (자동) 생성

harness tools/audit_vault.py 룰 기반 자동 분류. action=review row는 사람 검토 게이트. 실제 이관은 Sub 3."
```

- [ ] **Step 3: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo "BAD" || echo "OK"
```

Expected: `OK`.

---

## Phase 4: 사용자 검토 안내

### Task 4.1: 검토 안내 메시지

**Files:** N/A — 사용자 안내만

- [ ] **Step 1: 사용자에게 검토 절차 안내**

다음 내용 출력:

```
vault 분류표 생성 완료. 검토 방법:

1. Obsidian에서 `wiki/guides/_audit/migration-plan.md` 열기
2. 요약 표 확인 — 서비스별 action 분포 검토
3. 서비스별 섹션에서 action=review row 보기
4. 각 review row에 대해 dst 셀 채우고 action을 move/merge/keep/delete로 변경
5. 검토 완료된 row 만큼 별도 commit 가능 (점진적 확정)

Sub 3 이관은 검토 완료된 json을 입력으로 받음. 부분 검토 상태로 Sub 3 시작 가능 (검토 완료된 row만 이관).
```

---

## Self-Review

- **Spec 커버리지**:
  - Sub 2 산출물 4건: `tools/audit_vault.py` (Task 1.1), `tools/README.md` (Task 1.2), `migration-plan.md` + `.json` (Task 2.2) ✓
  - 분류 룰: Task 1.1의 SERVICE_PREFIX / GUIDES_META_KEEP / AUTO_DELETE_DIRS / REVIEW_DIRS / process_map / service_dirs ✓
  - 산출물 형식: markdown 표 + json (Task 1.1 render_md + main) ✓
  - 수동 검토 게이트: Task 4.1에서 절차 안내 ✓
  - 깨진 참조: Sub 3 비범위로 명시 ✓
- **Placeholder 없음**: 모든 step에 실 코드/명령.
- **타입 일관**:
  - `SERVICE_PREFIX`: dict[str, str] — prefix → service_id
  - `classify()` return dict 키 일관: `src`, `dst`, `action`, `confidence`, `service`, `category`, `reason`
  - action enum: `move`, `merge`, `keep`, `delete`, `review` 5종 일관
  - confidence: `high`, `medium`, `low` 3종
- 빠진 부분 없음.

## 검증 기준

- `tools/audit_vault.py --help` 동작
- 임시 fixture 4건 정확 분류 (Task 2.1)
- 실 vault 607건 분류, json row 수 == md 파일 수
- action=move dst가 모두 새 택소노미 prefix
- harness commit + vault commit 각 1건
- AI footer 0건
