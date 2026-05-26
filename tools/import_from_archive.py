#!/usr/bin/env python3
"""옛 vault (team2-archive) → 신규 vault (team2) selective import.

기본 = dry-run. --apply 명시 시 실 복사.
import 대상은 명시 (basename, frontmatter type 또는 prefix). lint 통과 못 하면 surface.

Usage:
    # archive 안 단일 파일 찾아서 import
    python3 tools/import_from_archive.py --archive ARCHIVE --vault VAULT --find dev2-5749
    # → archive 안 dev2-5749 매치되는 모든 파일 listing

    python3 tools/import_from_archive.py --archive ARCHIVE --vault VAULT --file wiki/tickets/dev2-5749.md
    # → 해당 파일을 vault의 새 위치 (type 추정)으로 dry-run 복사 보고

    python3 tools/import_from_archive.py --archive ARCHIVE --vault VAULT --file ... --apply
    # → 실 복사

기능 제한:
- 단일 파일 단위 (bulk import는 의도적으로 X — clean slate 원칙)
- frontmatter 누락 시 surface, 사람 보강 후 재시도
- 위치는 lint_vault.py 룰 기준으로 추정
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# lint_vault와 동일한 mapping (import 위치 결정용)
TYPE_LOCATION: dict[str, str] = {
    "ticket": "wiki/processes/tickets/{ticket_status}/",
    "weekly-report": "wiki/processes/weekly/",
    "daily": "wiki/processes/daily/",
    "meeting": "wiki/processes/meetings/",
    "okr": "wiki/processes/okr/",
    "incident": "wiki/processes/incidents/",
    "capacity-plan": "wiki/processes/capacity/",
    "service-index": "wiki/services/{service_id}/",
    "domain-index": "wiki/services/{service_id}/domains/{domain}/",
    "process-index": "wiki/processes/{name}/",
    "analysis": "wiki/services/{service_id}/analysis/",
    "decision": "wiki/services/{service_id}/decisions/",
    "proposal": "wiki/services/{service_id}/proposals/",
    "guide": "wiki/guides/",
    "glossary": "wiki/glossary/",
    "project": "wiki/projects/",
}


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        line = line.rstrip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip().strip('"').strip("'")
        if v:
            fm[k.strip()] = v
    return fm


def find_files(archive: Path, query: str) -> list[Path]:
    """archive 안 query 매치 파일 listing."""
    q = query.lower()
    out = []
    for p in archive.rglob("*.md"):
        if q in p.name.lower():
            out.append(p)
    return sorted(out)


def determine_destination(vault: Path, src_text: str, src_name: str) -> tuple[Path | None, str]:
    """type + frontmatter 기준으로 vault 안 dst 결정. (dst, reason)."""
    fm = parse_frontmatter(src_text)
    if fm is None:
        return None, "frontmatter 없음 — 사람이 type·필드 채워 재시도"
    t = fm.get("type")
    if not t:
        return None, "type 필드 누락 — 사람이 type 명시"
    tpl = TYPE_LOCATION.get(t)
    if not tpl:
        return None, f"알 수 없는 type=`{t}`"
    # 템플릿 채움
    try:
        rendered = tpl.format(
            ticket_status=fm.get("ticket_status", "in-progress"),
            service_id=fm.get("service_id") or fm.get("service", "unknown"),
            domain=fm.get("domain", "unknown"),
            name=fm.get("name", "unknown"),
        )
    except KeyError as e:
        return None, f"템플릿 필드 누락: {e}"
    dst_dir = vault / rendered
    # filename 서비스 prefix 제거
    new_name = src_name
    for p in ("tobe-", "max-", "naru-", "bazaar-", "aasm-", "shopping-",
              "caravan-", "blog-", "storefront-", "web-aladin-"):
        if new_name.lower().startswith(p):
            new_name = new_name[len(p):]
            break
    return dst_dir / new_name, f"type=`{t}`, dir={rendered}, name={new_name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True, type=Path,
                    help="옛 vault 경로 (예: team2-archive)")
    ap.add_argument("--vault", required=True, type=Path,
                    help="신규 vault 경로 (예: team2)")
    ap.add_argument("--find", help="archive 안 query 매치 파일 listing")
    ap.add_argument("--file", help="archive root 기준 상대 경로 (예: wiki/tickets/dev2-5749.md)")
    ap.add_argument("--apply", action="store_true",
                    help="실 복사 (기본 dry-run)")
    args = ap.parse_args()

    archive = args.archive.resolve()
    vault = args.vault.resolve()

    if args.find:
        matches = find_files(archive, args.find)
        if not matches:
            print(f"매치 없음: {args.find}", file=sys.stderr)
            return 1
        for m in matches:
            rel = m.relative_to(archive)
            print(f"  {rel}")
        return 0

    if not args.file:
        ap.error("--find 또는 --file 필요")

    src = archive / args.file
    if not src.exists():
        print(f"파일 없음: {src}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8")
    dst, reason = determine_destination(vault, text, src.name)

    print(f"src:    {src.relative_to(archive)}")
    print(f"reason: {reason}")
    if dst is None:
        return 1
    rel_dst = dst.relative_to(vault)
    print(f"dst:    {rel_dst}")

    if dst.exists():
        print(f"WARN: dst 이미 존재 — overwrite", file=sys.stderr)

    if args.apply:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"copied: {rel_dst}")
        print("다음 단계: vault에서 `git add` + commit (pre-commit lint 통과해야 함)")
    else:
        print("[dry-run] --apply 추가 시 실 복사")
    return 0


if __name__ == "__main__":
    sys.exit(main())
