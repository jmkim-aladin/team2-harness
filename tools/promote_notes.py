#!/usr/bin/env python3
"""promote 마커 → 별도 도메인/분석/결정/제안/용어 노트 자동 분리.

ticket note 본문 안에 다음 마커 작성:

    <!-- promote:{type}/{svc?}/{slug} title="제목" [domain="..."] -->
    {본문 markdown}
    <!-- /promote -->

지원 type:
    domain   → services/{svc}/domains/{slug}.md            (svc 필수)
    analysis → services/{svc}/analysis/{slug}.md           (svc 필수)
    decision → services/{svc}/decisions/{slug}.md          (svc 필수)
    proposal → services/{svc}/proposals/{slug}.md          (svc 필수)
    glossary → glossary/{slug}.md                          (svc 무시)

Usage:
    # 단일 파일 promote 마커 처리
    python3 tools/promote_notes.py --vault VAULT --file wiki/processes/tickets/dev2-XXXX.md

    # vault 전체 scan
    python3 tools/promote_notes.py --vault VAULT --all

    # 실 실행
    python3 tools/promote_notes.py ... --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

PROMOTE_RE = re.compile(
    r'<!-- promote:([a-z]+)(?:/([a-z0-9-]+))?/([a-z0-9-]+)\s+'
    r'title="([^"]+)"'
    r'(?:\s+domain="([a-z0-9-]+)")?\s*-->\n'
    r'(.*?)\n'
    r'<!-- /promote -->',
    re.DOTALL,
)

TYPE_LOCATION = {
    "domain":   "wiki/services/{svc}/domains/{slug}.md",
    "analysis": "wiki/services/{svc}/analysis/{slug}.md",
    "decision": "wiki/services/{svc}/decisions/{slug}.md",
    "proposal": "wiki/services/{svc}/proposals/{slug}.md",
    "glossary": "wiki/glossary/{slug}.md",
}

TYPE_REQUIRES_SVC = {"domain", "analysis", "decision", "proposal"}


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def render_frontmatter(promote_type: str, svc: str | None, slug: str,
                       title: str, domain: str | None) -> str:
    """promote type에 맞는 frontmatter 생성."""
    today_s = today()
    if promote_type == "domain":
        if domain:
            # domain 폴더 구조용
            canonical = f"domain:{svc}/{domain}"
            return (
                f"---\n"
                f"type: domain-index\n"
                f"title: {title}\n"
                f"canonical_id: {canonical}\n"
                f"status: canonical\n"
                f"updated_at: {today_s}\n"
                f"service_id: {svc}\n"
                f"domain: {domain}\n"
                f"---\n"
            )
        # 단일 파일 domain note (간단). type=analysis fallback or note in domains/ dir
        return (
            f"---\n"
            f"type: analysis\n"  # domain 단일 파일은 analysis 타입 사용 (lint 호환)
            f"title: {title}\n"
            f"canonical_id: analysis:{svc}/{slug}\n"
            f"status: canonical\n"
            f"updated_at: {today_s}\n"
            f"service_id: {svc}\n"
            f"---\n"
        )
    if promote_type == "analysis":
        return (
            f"---\n"
            f"type: analysis\n"
            f"title: {title}\n"
            f"canonical_id: analysis:{svc}/{slug}\n"
            f"status: canonical\n"
            f"updated_at: {today_s}\n"
            f"service_id: {svc}\n"
            f"---\n"
        )
    if promote_type == "decision":
        return (
            f"---\n"
            f"type: decision\n"
            f"title: {title}\n"
            f"canonical_id: decision:{svc}/{slug}\n"
            f"status: canonical\n"
            f"updated_at: {today_s}\n"
            f"service_id: {svc}\n"
            f"---\n"
        )
    if promote_type == "proposal":
        return (
            f"---\n"
            f"type: proposal\n"
            f"title: {title}\n"
            f"canonical_id: proposal:{svc}/{slug}\n"
            f"status: draft\n"
            f"updated_at: {today_s}\n"
            f"service_id: {svc}\n"
            f"---\n"
        )
    if promote_type == "glossary":
        return (
            f"---\n"
            f"type: glossary\n"
            f"title: {title}\n"
            f"canonical_id: glossary:{slug}\n"
            f"status: canonical\n"
            f"updated_at: {today_s}\n"
            f"---\n"
        )
    raise ValueError(f"unknown promote type: {promote_type}")


def determine_dst(vault: Path, promote_type: str, svc: str | None,
                   slug: str, domain: str | None) -> Path | None:
    if promote_type in TYPE_REQUIRES_SVC and not svc:
        return None
    if promote_type == "domain" and domain:
        # 폴더 구조 domains/{domain}/_index.md 또는 그 안 sub 파일
        # 단순화: domains/{domain}/{slug}.md
        return vault / f"wiki/services/{svc}/domains/{domain}/{slug}.md"
    tpl = TYPE_LOCATION[promote_type]
    return vault / tpl.format(svc=svc or "", slug=slug)


def compute_wikilink(src_file: Path, dst_file: Path, title: str) -> str:
    """src → dst 상대 wikilink (Obsidian 친화)."""
    # Obsidian basename resolve 우선 — 단순 [[stem|title]] 형식
    return f"[[{dst_file.stem}|{title}]]"


def process_file(vault: Path, src_file: Path, dry_run: bool) -> dict:
    text = src_file.read_text(encoding="utf-8")
    matches = list(PROMOTE_RE.finditer(text))
    if not matches:
        return {"file": str(src_file.relative_to(vault)), "promoted": 0}

    new_text = text
    created: list[str] = []
    errors: list[str] = []
    # 역순으로 치환 (offset 안 깨지게)
    for m in reversed(matches):
        promote_type, svc, slug, title, domain, body = m.groups()
        dst = determine_dst(vault, promote_type, svc, slug, domain)
        if dst is None:
            errors.append(
                f"type={promote_type} 에 service 필요 (slug={slug})"
            )
            continue
        if dst.exists():
            errors.append(f"dst 이미 존재: {dst.relative_to(vault)}")
            continue
        # 생성할 노트 content
        fm = render_frontmatter(promote_type, svc, slug, title, domain)
        content = fm + "\n" + body.strip() + "\n"
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")
        created.append(str(dst.relative_to(vault)))
        # 원 파일에서 마커 치환
        link = compute_wikilink(src_file, dst, title)
        new_text = new_text[:m.start()] + link + new_text[m.end():]

    if not dry_run and created:
        src_file.write_text(new_text, encoding="utf-8")

    return {
        "file": str(src_file.relative_to(vault)),
        "promoted": len(created),
        "created": created,
        "errors": errors,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--file", help="단일 파일 (vault root 기준 상대 또는 절대)")
    ap.add_argument("--all", action="store_true",
                    help="vault 전체 wiki/ scan (promote 마커 있는 모든 파일)")
    ap.add_argument("--apply", action="store_true",
                    help="실 실행 (기본 dry-run)")
    args = ap.parse_args()

    vault = args.vault.resolve()
    dry_run = not args.apply

    targets: list[Path] = []
    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = vault / args.file
        targets.append(p)
    elif args.all:
        # promote 마커 있는 파일만 (grep)
        for p in (vault / "wiki").rglob("*.md"):
            if "<!-- promote:" in p.read_text(encoding="utf-8", errors="replace"):
                targets.append(p)
    else:
        ap.error("--file 또는 --all 필요")

    total_promoted = 0
    total_errors = 0
    for src in targets:
        result = process_file(vault, src, dry_run)
        total_promoted += result["promoted"]
        total_errors += len(result.get("errors", []))
        print(
            f"{result['file']}: promoted={result['promoted']}",
            file=sys.stderr,
        )
        for c in result.get("created", []):
            print(f"  → {c}", file=sys.stderr)
        for e in result.get("errors", []):
            print(f"  ERR: {e}", file=sys.stderr)

    print(
        f"\nmode: {'dry-run' if dry_run else 'apply'}, "
        f"total promoted={total_promoted}, errors={total_errors}",
        file=sys.stderr,
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
