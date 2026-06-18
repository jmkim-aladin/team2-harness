#!/usr/bin/env python3
"""Run the DEV2 Granola meeting sync cycle.

This deterministic runner is intended for Hermes cron. It imports recently
updated Granola notes into the vault, adds a conservative generated candidate
block to changed meeting notes, refreshes process indexes, lints the touched
files, and then refreshes the team2 knowledge projections.

It does not write to Granola, YouTrack, YouTrack KB, DBs, production systems, or
git. It also does not store transcripts or create daily notes unless explicitly
asked via flags.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_HARNESS = "/Users/jm/Documents/workspace/team2"
DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_STATUS_JSON = "wiki/projects/agentic-os/granola-sync-status.json"
DEFAULT_STATUS_MD = "wiki/projects/agentic-os/granola-sync-status.md"
DEFAULT_OVERLAP_MINUTES = 30
DEFAULT_INITIAL_LOOKBACK_DAYS = 7

FORBIDDEN_MUTATIONS = [
    "granola_mutation",
    "youtrack_mutation",
    "youtrack_kb_mutation",
    "db_write",
    "production_deploy",
    "git_commit_or_push",
    "canonical_promotion",
]

SERVICE_IDS = [
    "max",
    "tobe",
    "naru",
    "bazaar",
    "aasm",
    "storefront",
    "shopping",
    "blog",
    "caravan",
    "pod",
]

AI_BLOCK_RE = re.compile(
    r"<!-- generated:granola-ai-enrichment[^>]*-->.*?<!-- /generated:granola-ai-enrichment -->",
    re.DOTALL,
)
GRANOLA_BLOCK_RE = re.compile(
    r"<!-- generated:granola[^>]*-->.*?<!-- /generated -->",
    re.DOTALL,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_seconds(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def granola_timestamp(value: datetime) -> str:
    return isoformat_seconds(value).replace("+00:00", "Z")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def compute_updated_after(
    state: dict[str, Any],
    *,
    now: datetime,
    overlap_minutes: int,
    initial_lookback_days: int,
) -> str:
    finished_at = parse_datetime(str(state.get("finished_at") or ""))
    if state.get("status") == "ok" and finished_at:
        start = finished_at - timedelta(minutes=overlap_minutes)
    else:
        start = now.astimezone(timezone.utc) - timedelta(days=initial_lookback_days)
    return granola_timestamp(start)


def tail(text: str, *, max_lines: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def run_command(command: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def build_sync_command(
    harness: Path,
    vault: Path,
    *,
    updated_after: str,
    apply: bool,
    include_transcript: bool,
    create_daily: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(harness / "tools/sync_granola_meetings.py"),
        "--vault",
        str(vault),
        "--updated-after",
        updated_after,
    ]
    if include_transcript:
        command.append("--include-transcript")
    if create_daily:
        command.append("--create-daily")
    if apply:
        command.append("--apply")
    return command


def build_index_command(harness: Path, vault: Path, *, apply: bool) -> list[str]:
    command = [
        sys.executable,
        str(harness / "tools/generate_vault_indexes.py"),
        "--vault",
        str(vault),
        "--target",
        "processes",
    ]
    if apply:
        command.append("--apply")
    return command


def build_lint_command(harness: Path, vault: Path, files: list[str]) -> list[str]:
    return [
        sys.executable,
        str(harness / "tools/lint_vault.py"),
        "--vault",
        str(vault),
        "--files",
        *files,
    ]


def build_knowledge_cycle_command(harness: Path, vault: Path, *, apply: bool) -> list[str]:
    command = [
        sys.executable,
        str(harness / "tools/run_team2_knowledge_cycle.py"),
        "--harness",
        str(harness),
        "--vault",
        str(vault),
    ]
    if apply:
        command.append("--apply")
    return command


def changed_meetings_from_sync_stdout(stdout: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        match = re.match(r"^(?:wrote|would write)\s+(wiki/processes/meetings/[^\s;]+\.md)", line.strip())
        if not match:
            continue
        path = match.group(1)
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def lint_targets_for_meetings(vault: Path, meetings: list[str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()

    def add(rel: str) -> None:
        if rel not in seen:
            targets.append(rel)
            seen.add(rel)

    for rel in meetings:
        add(rel)
        stem = Path(rel).stem
        date = stem[:10]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            daily_rel = f"wiki/processes/daily/{date}.md"
            if (vault / daily_rel).exists():
                add(daily_rel)
    add("wiki/processes/meetings/meetings-index.md")
    return targets


def detect_tickets(text: str) -> list[str]:
    return sorted(
        {
            match.group(0).lower()
            for match in re.finditer(r"(?<![A-Za-z0-9])DEV2-\d+(?![A-Za-z0-9])", text, re.IGNORECASE)
        }
    )


def detect_services(text: str) -> list[str]:
    lowered = text.lower()
    services: list[str] = []
    for service in SERVICE_IDS:
        if re.search(rf"(?<![a-z0-9-]){re.escape(service)}(?![a-z0-9-])", lowered):
            services.append(service)
    return services


def render_enrichment_block(text: str, *, updated_at: str) -> str:
    tickets = detect_tickets(text)
    services = detect_services(text)
    ticket_text = ", ".join(f"[[{ticket}]]" for ticket in tickets) if tickets else "없음"
    service_text = ", ".join(f"[[{service}]]" for service in services) if services else "없음"
    return "\n".join(
        [
            f"<!-- generated:granola-ai-enrichment updated={updated_at} -->",
            "## AI 보강 후보",
            "",
            f"- 관련 티켓 후보: {ticket_text}",
            f"- 관련 서비스 후보: {service_text}",
            "- 확인 필요: 회의록의 결정, 후속 액션, 서비스 연결은 사람이 검토한 뒤 수동 섹션이나 관련 원장 노트에 반영한다.",
            "- 자동 처리 범위: 후보 추출과 검색 보조 정보 작성까지만 수행한다.",
            "<!-- /generated:granola-ai-enrichment -->",
        ]
    )


def insert_after_heading(text: str, block: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            before = "\n".join(lines[: index + 1]).rstrip()
            after = "\n".join(lines[index + 1 :]).lstrip("\n")
            return f"{before}\n\n{block}\n\n{after}".rstrip() + "\n"
    return text.rstrip() + f"\n\n{block}\n"


def upsert_enrichment_block(text: str, *, updated_at: str) -> str:
    text_without_old = AI_BLOCK_RE.sub("", text).rstrip() + "\n"
    block = render_enrichment_block(text_without_old, updated_at=updated_at)
    match = GRANOLA_BLOCK_RE.search(text_without_old)
    if match:
        return (
            text_without_old[: match.end()].rstrip()
            + "\n\n"
            + block
            + "\n\n"
            + text_without_old[match.end() :].lstrip("\n")
        ).rstrip() + "\n"
    return insert_after_heading(text_without_old, block)


def enrich_meeting_notes(vault: Path, meetings: list[str], *, apply: bool, updated_at: str) -> dict[str, Any]:
    enriched: list[str] = []
    missing: list[str] = []
    for rel in meetings:
        path = vault / rel
        if not path.exists():
            missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        next_text = upsert_enrichment_block(text, updated_at=updated_at)
        if next_text == text:
            continue
        enriched.append(rel)
        if apply:
            path.write_text(next_text, encoding="utf-8")
    return {
        "enriched": enriched,
        "missing": missing,
        "status": "ok",
    }


def result_from_process(name: str, command: Sequence[str], proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "name": name,
        "command": list(command),
        "returncode": proc.returncode,
        "status": "ok" if proc.returncode == 0 else "failed",
        "stdout_tail": tail(proc.stdout),
        "stderr_tail": tail(proc.stderr),
    }


def render_status_markdown(result: dict[str, Any]) -> str:
    review_state = "none" if result["status"] == "ok" else "needs-review"
    lines = [
        "---",
        "type: project",
        "status: draft",
        f"review_state: {review_state}",
        "decision_status: none",
        "canonical_id: project:agentic-os/granola-sync-status",
        f"updated_at: {result['finished_at']}",
        "---",
        "",
        "# Granola 회의록 동기화 상태",
        "",
        f"- 상태: {result['status']}",
        f"- 모드: {result['mode']}",
        f"- updated_after: {result['updated_after']}",
        f"- 변경 회의록: {len(result['changed_meetings'])}",
        f"- 보강 회의록: {len(result.get('enrichment', {}).get('enriched', []))}",
        "",
        "## 단계",
        "",
    ]
    for step in result["steps"]:
        lines.append(f"- {step['name']}: {step['status']} ({step.get('returncode', 0)})")
    if result["changed_meetings"]:
        lines.extend(["", "## 변경 회의록", ""])
        for rel in result["changed_meetings"]:
            lines.append(f"- `{rel}`")
    lines.extend(["", "## 자동 금지", ""])
    for item in result["forbidden_mutations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_status(vault: Path, result: dict[str, Any], *, apply: bool) -> dict[str, str]:
    json_rel = Path(DEFAULT_STATUS_JSON)
    md_rel = Path(DEFAULT_STATUS_MD)
    if not apply:
        return {
            "json": json_rel.as_posix(),
            "markdown": md_rel.as_posix(),
            "status": "dry-run",
        }
    json_path = vault / json_rel
    md_path = vault / md_rel
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_status_markdown(result), encoding="utf-8")
    return {
        "json": json_rel.as_posix(),
        "markdown": md_rel.as_posix(),
        "status": "written",
    }


def run_cycle(
    harness: Path,
    vault: Path,
    *,
    apply: bool,
    include_transcript: bool = False,
    create_daily: bool = False,
    overlap_minutes: int = DEFAULT_OVERLAP_MINUTES,
    initial_lookback_days: int = DEFAULT_INITIAL_LOOKBACK_DAYS,
    command_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
    now_fn: Callable[[], datetime] = now_utc,
) -> dict[str, Any]:
    runner = command_runner or (lambda command, cwd: run_command(command, cwd=cwd))
    started_at = isoformat_seconds(now_fn())
    state = read_json_optional(vault / DEFAULT_STATUS_JSON)
    updated_after = compute_updated_after(
        state,
        now=now_fn(),
        overlap_minutes=overlap_minutes,
        initial_lookback_days=initial_lookback_days,
    )
    result: dict[str, Any] = {
        "schema": "team2.granola_sync_cycle.v1",
        "mode": "apply" if apply else "dry-run",
        "started_at": started_at,
        "finished_at": started_at,
        "status": "running",
        "harness_path": str(harness),
        "vault_path": str(vault),
        "updated_after": updated_after,
        "include_transcript": include_transcript,
        "create_daily": create_daily,
        "changed_meetings": [],
        "forbidden_mutations": FORBIDDEN_MUTATIONS,
        "steps": [],
    }

    sync_command = build_sync_command(
        harness,
        vault,
        updated_after=updated_after,
        apply=apply,
        include_transcript=include_transcript,
        create_daily=create_daily,
    )
    sync_proc = runner(sync_command, harness)
    sync_step = result_from_process("sync_granola_meetings", sync_command, sync_proc)
    result["steps"].append(sync_step)
    if sync_proc.returncode != 0:
        result["status"] = "failed"
        result["finished_at"] = isoformat_seconds(now_fn())
        result["status_files"] = write_status(vault, result, apply=apply)
        return result

    meetings = changed_meetings_from_sync_stdout(sync_proc.stdout)
    result["changed_meetings"] = meetings
    if not meetings:
        result["status"] = "ok"
        result["finished_at"] = isoformat_seconds(now_fn())
        result["status_files"] = write_status(vault, result, apply=apply)
        return result

    enrichment = enrich_meeting_notes(vault, meetings, apply=apply, updated_at=isoformat_seconds(now_fn()))
    result["enrichment"] = enrichment
    result["steps"].append(
        {
            "name": "enrich_granola_meetings",
            "command": [],
            "returncode": 0,
            "status": enrichment["status"],
            "stdout_tail": f"enriched={len(enrichment['enriched'])} missing={len(enrichment['missing'])}",
            "stderr_tail": "",
        }
    )

    followups = [
        ("generate_vault_indexes", build_index_command(harness, vault, apply=apply)),
        ("lint_vault", build_lint_command(harness, vault, lint_targets_for_meetings(vault, meetings))),
        ("run_team2_knowledge_cycle", build_knowledge_cycle_command(harness, vault, apply=apply)),
    ]
    for name, command in followups:
        proc = runner(command, harness)
        step = result_from_process(name, command, proc)
        result["steps"].append(step)
        if proc.returncode != 0:
            result["status"] = "failed"
            break
    else:
        result["status"] = "ok"

    result["finished_at"] = isoformat_seconds(now_fn())
    result["status_files"] = write_status(vault, result, apply=apply)
    return result


def print_summary(result: dict[str, Any]) -> None:
    print(f"granola sync cycle: {result['status']}")
    print(f"mode: {result['mode']}")
    print(f"updated_after: {result['updated_after']}")
    print(f"changed_meetings: {len(result['changed_meetings'])}")
    enrichment = result.get("enrichment") or {}
    if enrichment:
        print(f"enriched: {len(enrichment.get('enriched', []))}")
    print("steps: " + ", ".join(f"{s['name']}={s['status']}" for s in result["steps"]))
    files = result.get("status_files") or {}
    if files:
        print(f"status: {files.get('status')} {files.get('markdown')}")
    failed = [s for s in result["steps"] if s["status"] != "ok"]
    for step in failed:
        print(f"failed_step: {step['name']}", file=sys.stderr)
        if step.get("stderr_tail"):
            print(step["stderr_tail"], file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", type=Path, default=Path(os.environ.get("TEAM2_HARNESS_PATH", DEFAULT_HARNESS)))
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-transcript", action="store_true")
    parser.add_argument("--create-daily", action="store_true")
    parser.add_argument("--overlap-minutes", type=int, default=DEFAULT_OVERLAP_MINUTES)
    parser.add_argument("--initial-lookback-days", type=int, default=DEFAULT_INITIAL_LOOKBACK_DAYS)
    args = parser.parse_args(argv)

    result = run_cycle(
        args.harness.resolve(),
        args.vault.resolve(),
        apply=args.apply,
        include_transcript=args.include_transcript,
        create_daily=args.create_daily,
        overlap_minutes=args.overlap_minutes,
        initial_lookback_days=args.initial_lookback_days,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
