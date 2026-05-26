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


def build_rename_map(plan: list[dict]) -> dict[str, str | None]:
    """plan에서 옛 stem → 새 stem 매핑.

    충돌 None 마킹:
    - same-source 충돌: 같은 old가 여러 new로 (보통 없지만 안전)
    - same-target 충돌: 여러 old가 같은 new로 (예: 여러 services/{svc}.md가 _index로 → 어느 서비스로
      되돌아갈지 결정 불가, wikilink 재작성 시 ambiguous)
    """
    pairs: list[tuple[str, str]] = []
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
        pairs.append((old, new))

    # same-target 충돌: 같은 new에 여러 old가 매핑되면 그 new는 ambiguous
    new_to_olds: dict[str, set[str]] = {}
    for old, new in pairs:
        new_to_olds.setdefault(new, set()).add(old)
    ambiguous_new = {n for n, olds in new_to_olds.items() if len(olds) > 1}

    rename: dict[str, str | None] = {}
    for old, new in pairs:
        if new in ambiguous_new:
            rename[old] = None
            continue
        if old in rename:
            if rename[old] != new:
                rename[old] = None
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
        # path_prefix는 옛 dir을 가리키므로 새 dst dir과 불일치할 가능성 큼.
        # Obsidian은 basename 유일하면 자동 resolve하므로 path_prefix를 떨군다.
        return f"[[{new_name}{ext or ''}{section or ''}{display or ''}]]"

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
        # 도구가 직접 수정한 파일만 staging. 사용자 pre-existing M 보존.
        run_git(["add", "--"] + changed_files, cwd=vault, check=False)

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
