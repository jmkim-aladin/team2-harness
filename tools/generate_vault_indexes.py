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


def llm_hint_block(scope: str, examples: str = "") -> str:
    """LLM이 디렉터리 의도를 빠르게 파악하도록 hint 블록 삽입."""
    body = f"이 디렉터리는 {scope}."
    if examples:
        body += f" 예: {examples}"
    return f"<!-- llm-hint -->\n{body}\n<!-- /llm-hint -->"


def new_service_index(svc: str, block: str) -> str:
    today_s = today()
    hint = llm_hint_block(
        f"`{svc}` 서비스의 도메인·해석·결정·개선·운영 절차 산출물",
        "domains/, analysis/, decisions/, proposals/, processes/"
    )
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
        f"{hint}\n\n"
        f"{block}\n\n"
        f"<!-- generated:harness-link source=team2/catalog/{svc}.yaml updated=N/A -->\n"
        f"(Sub 5에서 채움)\n"
        f"<!-- /generated -->\n"
    )


def new_process_index(process_type: str, block: str) -> str:
    today_s = today()
    scope_map = {
        "daily": "팀 daily 노트 (YYYY-MM-DD.md). 그날 아젠다·진행·미해결 기록",
        "weekly": "주간업무 보고서 초안·확정본 (YYYY-MM-NW-{user}.md)",
        "meetings": "팀 회의록 (YYYY-MM-DD-topic.md). KB 아님",
        "tickets": "DEV2-* 티켓 산출물. flat 구조. 상태는 frontmatter ticket_status (auto-prep|in-progress|done|backlog|archive)",
        "okr": "분기/연간 OKR. 팀·개인",
        "incidents": "장애 사례·post-mortem",
        "capacity": "월별 가용 맨데이·velocity 스냅샷",
        "sprint": "스프린트 운영·마감·회고 산출물",
        "team": "팀 멤버 메타 (harness team-members.md 미러)",
    }
    hint = llm_hint_block(scope_map.get(process_type, f"{process_type} 프로세스 산출물"))
    return (
        f"---\n"
        f"type: process-index\n"
        f"title: {process_type}\n"
        f"canonical_id: process:{process_type}\n"
        f"status: canonical\n"
        f"updated_at: {today_s}\n"
        f"---\n\n"
        f"# {process_type}\n\n"
        f"{hint}\n\n"
        f"{block}\n"
    )


def new_hub_index(hub: str, block: str) -> str:
    today_s = today()
    title_map = {"services": "서비스", "processes": "프로세스"}
    title = title_map.get(hub, hub)
    hint_map = {
        "services": "서비스별 도메인·해석·결정 진입점. service_id = harness catalog/{name}.yaml의 service_id",
        "processes": "팀 업무 프로세스 진입점 (sprint·okr·weekly·daily·meetings·tickets·incidents·capacity·team)",
    }
    hint = llm_hint_block(hint_map.get(hub, f"{title} 인덱스"))
    return (
        f"---\n"
        f"type: index\n"
        f"title: {title}\n"
        f"canonical_id: index:{hub}\n"
        f"status: canonical\n"
        f"updated_at: {today_s}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{hint}\n\n"
        f"{block}\n"
    )


def ensure_llm_hint(text: str, hint: str) -> str:
    """llm-hint 블록이 없으면 H1 뒤에 삽입. 있으면 보전."""
    if "<!-- llm-hint -->" in text:
        return text
    # H1 다음 빈줄 뒤에 삽입
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inserted = False
    for i, line in enumerate(lines):
        out.append(line)
        if not inserted and line.startswith("# "):
            # 다음 빈 줄 한 개 통과 후 삽입
            out.append("\n")
            out.append(hint + "\n")
            out.append("\n")
            inserted = True
    if not inserted:
        # H1 없으면 끝에 append
        out.append("\n" + hint + "\n")
    return "".join(out)


def update_existing(text: str, block: str, file_kind: str,
                     llm_hint: str | None = None) -> tuple[str, str]:
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
        # llm-hint 부재 시 보강
        if llm_hint:
            new_text = ensure_llm_hint(new_text, llm_hint)
        return new_text, "replaced"
    # 본문이 거의 비어있으면 inserted
    if len(text.strip().splitlines()) <= 5:
        # frontmatter만 있는 수준 — block을 본문 끝에 추가
        new_text = text.rstrip() + "\n\n" + block + "\n"
        if llm_hint:
            new_text = ensure_llm_hint(new_text, llm_hint)
        return new_text, "inserted"
    # 본문이 있고 generated block 없으면 skip + surface
    return text, "skipped"


def process_service(vault: Path, svc: str, dry_run: bool) -> dict:
    idx_path = vault / "wiki/services" / svc / "_index.md"
    block = render_service_index_block(vault, svc)
    hint = llm_hint_block(
        f"`{svc}` 서비스의 도메인·해석·결정·개선·운영 절차 산출물",
        "domains/, analysis/, decisions/, proposals/, processes/"
    )
    if idx_path.exists():
        text = idx_path.read_text(encoding="utf-8")
        new_text, status = update_existing(text, block, "service", llm_hint=hint)
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
    scope_map = {
        "daily": "팀 daily 노트 (YYYY-MM-DD.md). 그날 아젠다·진행·미해결 기록",
        "weekly": "주간업무 보고서 초안·확정본",
        "meetings": "팀 회의록. KB 아님",
        "tickets": "DEV2-* 티켓 산출물. flat 구조. 상태는 frontmatter ticket_status (auto-prep|in-progress|done|backlog|archive)",
        "okr": "분기/연간 OKR. 팀·개인",
        "incidents": "장애 사례·post-mortem",
        "capacity": "월별 가용 맨데이·velocity 스냅샷",
        "sprint": "스프린트 운영·마감·회고",
        "team": "팀 멤버 메타 (harness team-members.md 미러)",
    }
    hint = llm_hint_block(scope_map.get(process_type, f"{process_type} 산출물"))
    if idx_path.exists():
        text = idx_path.read_text(encoding="utf-8")
        new_text, status = update_existing(text, block, "process", llm_hint=hint)
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
    hint_map = {
        "services": "서비스별 도메인·해석·결정 진입점. service_id = harness catalog/{name}.yaml의 service_id",
        "processes": "팀 업무 프로세스 진입점 (sprint·okr·weekly·daily·meetings·tickets·incidents·capacity·team)",
    }
    hint = llm_hint_block(hint_map.get(hub, f"{hub} 인덱스"))
    if idx_path.exists():
        text = idx_path.read_text(encoding="utf-8")
        new_text, status = update_existing(text, block, "hub", llm_hint=hint)
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
