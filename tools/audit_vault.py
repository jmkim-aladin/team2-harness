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
