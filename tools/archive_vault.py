#!/usr/bin/env python3
"""hot/cold archive — frontmatter `updated_at`이 N일 전 이상이면 archive/YYYY/로 이동.

archive 대상:
- processes/tickets/done/* (스프린트 마감 후 archive)
- processes/daily/* (180일+ 옛 daily)
- processes/meetings/* (180일+ 옛 회의록)
- processes/weekly/* (180일+ 옛 주간보고)

비대상:
- processes/{okr,incidents,capacity}: 영구 보관 가치
- services/*, projects/*, guides/*, glossary/*: 정형 콘텐츠

Usage:
    python3 tools/archive_vault.py --vault VAULT [--days 180] [--dry-run | --apply]
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ARCHIVE_TARGETS = [
    "wiki/processes/tickets/done",
    "wiki/processes/daily",
    "wiki/processes/meetings",
    "wiki/processes/weekly",
]


def parse_frontmatter_date(text: str) -> datetime | None:
    """frontmatter updated_at 또는 date 필드 → datetime."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    for line in text[4:end].splitlines():
        m = re.match(r'^(updated_at|date):\s*(\d{4}-\d{2}-\d{2})', line.strip())
        if m:
            try:
                return datetime.strptime(m.group(2), "%Y-%m-%d")
            except ValueError:
                return None
    return None


def archive_path(vault: Path, src: Path) -> Path:
    """archive 위치 — wiki/processes/{type}/archive/YYYY/{name}.md."""
    rel = src.relative_to(vault / "wiki/processes")
    # rel = "daily/2025-06-12.md" 같은 형태
    parts = rel.parts
    process_type = parts[0]
    name = parts[-1]
    # 파일 frontmatter date의 year 추출
    text = src.read_text(encoding="utf-8", errors="replace")
    d = parse_frontmatter_date(text)
    year = str(d.year) if d else "unknown"
    return vault / "wiki/processes" / process_type / "archive" / year / name


def git_mv_safe(vault: Path, src_rel: str, dst_rel: str) -> str:
    src = vault / src_rel
    dst = vault / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["git", "mv", src_rel, dst_rel], cwd=vault, check=True,
                       capture_output=True, text=True)
        return "git mv"
    except subprocess.CalledProcessError:
        shutil.move(str(src), str(dst))
        subprocess.run(["git", "add", dst_rel], cwd=vault, check=False)
        return "mv+add"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--days", type=int, default=180,
                    help="cold 판정 기준 일수 (기본 180)")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    vault = args.vault.resolve()
    dry_run = not args.apply
    cutoff = datetime.now() - timedelta(days=args.days)

    moved: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []

    for target in ARCHIVE_TARGETS:
        target_dir = vault / target
        if not target_dir.exists():
            continue
        for md in sorted(target_dir.rglob("*.md")):
            # archive/ 안 파일 자기 제외
            if "archive" in md.relative_to(target_dir).parts:
                continue
            if md.name == "_index.md":
                continue
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            d = parse_frontmatter_date(text)
            if d is None:
                skipped.append((str(md.relative_to(vault)), "date 없음"))
                continue
            if d >= cutoff:
                continue  # 아직 hot
            dst = archive_path(vault, md)
            src_rel = str(md.relative_to(vault))
            dst_rel = str(dst.relative_to(vault))
            if not dry_run:
                result = git_mv_safe(vault, src_rel, dst_rel)
                moved.append((src_rel, dst_rel + f" ({result})"))
            else:
                moved.append((src_rel, dst_rel + " (dry-run)"))

    print(f"mode: {'dry-run' if dry_run else 'apply'}", file=sys.stderr)
    print(f"cutoff: {cutoff.strftime('%Y-%m-%d')} (days={args.days})",
          file=sys.stderr)
    print(f"moved: {len(moved)}", file=sys.stderr)
    for src, dst in moved:
        print(f"  {src} → {dst}", file=sys.stderr)
    if skipped:
        print(f"skipped (date 없음): {len(skipped)}", file=sys.stderr)
        for src, reason in skipped[:5]:
            print(f"  {src}: {reason}", file=sys.stderr)


if __name__ == "__main__":
    main()
