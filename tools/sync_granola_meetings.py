#!/usr/bin/env python3
"""Sync Granola meeting notes into the team2 Obsidian vault.

Default behavior is conservative:
- read Granola through the official REST API
- write meeting notes under wiki/processes/meetings/
- update an existing daily note's "## 회의" section
- do not create daily notes unless --create-daily is passed
- do not include transcripts unless --include-transcript is passed
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://public-api.granola.ai/v1"
DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
GRANOLA_BLOCK_RE = re.compile(
    r"<!-- generated:granola[^>]*-->.*?<!-- /generated -->",
    re.DOTALL,
)
DEFAULT_KEYCHAIN_SERVICE = "team2-granola-api-key"


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_date(note: dict[str, Any]) -> str:
    scheduled = (note.get("calendar_event") or {}).get("scheduled_start_time")
    raw = scheduled or note.get("created_at") or note.get("updated_at")
    if not raw:
        return dt.date.today().isoformat()
    return raw[:10]


def attendee_label(attendee: dict[str, Any]) -> str:
    name = (attendee.get("name") or "").strip()
    email = (attendee.get("email") or "").strip()
    if name and email:
        return f"{name} <{email}>"
    return name or email or "unknown"


def render_transcript(transcript: list[dict[str, Any]]) -> str:
    lines = ["## Transcript", ""]
    for item in transcript:
        speaker = item.get("speaker") or {}
        label = speaker.get("diarization_label") or speaker.get("source") or "speaker"
        text = (item.get("text") or "").strip()
        if text:
            lines.append(f"- **{label}**: {text}")
    return "\n".join(lines).rstrip() + "\n"


def render_granola_block(note: dict[str, Any], include_transcript: bool = False) -> str:
    summary = (note.get("summary_markdown") or note.get("summary_text") or "").strip()
    if not summary:
        summary = "- Granola 요약 없음"

    lines = [
        f"<!-- generated:granola note_id={note['id']} updated={note.get('updated_at') or ''} -->",
        "## 요약",
        "",
        summary,
        "",
    ]
    if include_transcript and note.get("transcript"):
        lines.append(render_transcript(note["transcript"]).rstrip())
        lines.append("")
    lines.append("<!-- /generated -->")
    return "\n".join(lines)


def render_meeting_note(
    note: dict[str, Any],
    include_transcript: bool = False,
    title_override: str | None = None,
) -> tuple[str, str]:
    granola_id = str(note["id"])
    source_title = (note.get("title") or "Granola meeting").strip()
    display_title = (title_override or source_title).strip()
    date = parse_date(note)
    slug = slugify(source_title, f"granola-{granola_id[-6:].lower()}")
    stem = f"{date}-{slug}"
    rel_path = f"wiki/processes/meetings/{stem}.md"

    attendees = [attendee_label(a) for a in note.get("attendees") or []]
    updated_at = (note.get("updated_at") or dt.datetime.now(dt.timezone.utc).isoformat())[:10]
    web_url = note.get("web_url") or ""

    lines: list[str] = [
        "---",
        "type: meeting",
        f"title: {yaml_string(f'{date} {display_title}')}",
        f"canonical_id: meeting:{stem}",
        "status: canonical",
        f"updated_at: {updated_at}",
        f"date: {date}",
        "participants:",
    ]
    if attendees:
        for attendee in attendees:
            lines.append(f"  - {yaml_string(attendee)}")
    else:
        lines.append("  - jmkim")
    lines.extend(
        [
            "related_tickets: []",
            "related_services: []",
            "source: granola",
            f"granola_id: {granola_id}",
            f"granola_url: {yaml_string(web_url)}",
            f"granola_updated_at: {yaml_string(note.get('updated_at') or '')}",
            "---",
            "",
            "<!-- llm-hint -->",
            "Granola에서 동기화한 회의록. 원문/전문 확인은 granola_url을 우선 사용하고, 위키에는 결정·후속 액션 중심으로 정리한다.",
            "<!-- /llm-hint -->",
            "",
            f"# {date} {display_title}",
            "",
            "## 참가자",
            "",
        ]
    )
    for attendee in attendees:
        lines.append(f"- {attendee}")
    if not attendees:
        lines.append("- jmkim")
    lines.extend(
        [
            "",
            "## 아젠다",
            "",
            "- ",
            "",
            render_granola_block(note, include_transcript=include_transcript),
            "",
            "## 결정",
            "",
            "- ",
            "",
            "## 후속 액션",
            "",
            "- [ ] ",
            "",
            "## 관련 자료",
            "",
            f"- Granola: {web_url}" if web_url else "- Granola: ",
            "- 티켓: ",
            "- 도메인: ",
            "- 이전 회의: ",
            "",
        ]
    )
    return rel_path, "\n".join(lines)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_existing_meeting_by_granola_id(vault: Path, granola_id: str) -> str | None:
    meetings_dir = vault / "wiki/processes/meetings"
    if not meetings_dir.exists():
        return None
    needle = f"granola_id: {granola_id}"
    for path in sorted(meetings_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if needle in text:
            return path.relative_to(vault).as_posix()
    return None


def extract_display_title(markdown: str) -> str | None:
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if not title_match:
        return None
    title = title_match.group(1).strip()
    date_prefix = re.match(r"^\d{4}-\d{2}-\d{2}\s+(.+)$", title)
    return date_prefix.group(1).strip() if date_prefix else title


def load_title_map(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for note_id, value in data.items():
        if isinstance(value, str):
            out[str(note_id)] = value
        elif isinstance(value, dict) and isinstance(value.get("title"), str):
            out[str(note_id)] = value["title"]
    return out


def insert_after_title(text: str, block: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            before = "\n".join(lines[: index + 1]).rstrip()
            after = "\n".join(lines[index + 1 :]).lstrip("\n")
            return f"{before}\n\n{block}\n\n{after}".rstrip() + "\n"
    return text.rstrip() + f"\n\n{block}\n"


def update_display_title(text: str, date: str, display_title: str) -> str:
    full_title = f"{date} {display_title}"
    if re.search(r"^title:\s+.*$", text, re.MULTILINE):
        text = re.sub(
            r"^title:\s+.*$",
            f"title: {yaml_string(full_title)}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if re.search(r"^#\s+.+$", text, re.MULTILINE):
        text = re.sub(
            r"^#\s+.+$",
            f"# {full_title}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def upsert_meeting_note(
    vault: Path,
    rel_path: str,
    rendered_markdown: str,
    note: dict[str, Any],
    display_title: str | None = None,
) -> None:
    path = vault / rel_path
    if not path.exists():
        write_text(path, rendered_markdown)
        return

    text = read_text(path)
    block = render_granola_block(note, include_transcript=bool(note.get("transcript")))
    if GRANOLA_BLOCK_RE.search(text):
        text = GRANOLA_BLOCK_RE.sub(block, text, count=1)
    else:
        text = insert_after_title(text, block)
    if display_title:
        text = update_display_title(text, parse_date(note), display_title)
    write_text(path, text)


def upsert_daily_meeting_link(
    vault: Path,
    date: str,
    meeting_stem: str,
    title: str,
    *,
    create_daily: bool,
) -> bool:
    daily = vault / "wiki/processes/daily" / f"{date}.md"
    if not daily.exists():
        if not create_daily:
            return False
        write_text(
            daily,
            "\n".join(
                [
                    "---",
                    "type: daily",
                    f"title: {date}",
                    f"canonical_id: daily:{date}",
                    "status: canonical",
                    f"updated_at: {date}",
                    f"date: {date}",
                    "---",
                    "",
                    f"# {date}",
                    "",
                    "## 오늘의 아젠다",
                    "",
                    "- [ ] ",
                    "",
                    "## 진행",
                    "",
                    "-",
                    "",
                    "## 블로커 / 미해결",
                    "",
                    "-",
                    "",
                    "## 회의",
                    "",
                    "-",
                    "",
                    "## 메모",
                    "",
                    "-",
                    "",
                    "## 내일 이월",
                    "",
                    "-",
                    "",
                ]
            ),
        )

    text = read_text(daily)
    link = f"[[{meeting_stem}|{title}]]"
    if link in text:
        return False

    existing_link_re = re.compile(rf"\[\[{re.escape(meeting_stem)}(?:\|[^\]]*)?\]\]")
    if existing_link_re.search(text):
        text = existing_link_re.sub(link, text)
        write_text(daily, text)
        return True

    entry = f"- {link}"
    marker = "## 회의"
    if marker not in text:
        text = text.rstrip() + f"\n\n{marker}\n\n{entry}\n"
        write_text(daily, text)
        return True

    start = text.index(marker)
    next_match = re.search(r"\n## ", text[start + len(marker) :])
    if next_match:
        end = start + len(marker) + next_match.start()
        section = text[start:end]
        rest = text[end:]
    else:
        section = text[start:]
        rest = ""

    section_lines = section.rstrip().splitlines()
    while section_lines and section_lines[-1].strip() in {"", "-"}:
        section_lines.pop()
    new_section = "\n".join(section_lines).rstrip() + f"\n\n{entry}\n"
    text = text[:start] + new_section + rest
    write_text(daily, text)
    return True


class GranolaClient:
    def __init__(self, token: str, base_url: str = API_BASE) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")

    def request_json(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        request = urllib.request.Request(
            f"{self.base_url}{path}{query}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_notes(
        self,
        *,
        created_after: str | None,
        created_before: str | None,
        updated_after: str | None,
        updated_before: str | None,
        page_size: int,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {"page_size": str(page_size)}
        if created_after:
            params["created_after"] = created_after
        if created_before:
            params["created_before"] = created_before
        if updated_after:
            params["updated_after"] = updated_after
        if updated_before:
            params["updated_before"] = updated_before

        notes: list[dict[str, Any]] = []
        while True:
            page = self.request_json("/notes", params)
            notes.extend(page.get("notes") or [])
            cursor = page.get("cursor")
            if not page.get("hasMore") or not cursor:
                break
            params["cursor"] = cursor
        return notes

    def get_note(self, note_id: str, *, include_transcript: bool) -> dict[str, Any]:
        params = {"include": "transcript"} if include_transcript else None
        return self.request_json(f"/notes/{note_id}", params)


def read_api_key_from_keychain() -> str | None:
    service = os.environ.get("GRANOLA_KEYCHAIN_SERVICE", DEFAULT_KEYCHAIN_SERVICE)
    account = os.environ.get("GRANOLA_KEYCHAIN_ACCOUNT", os.environ.get("USER", ""))
    command = ["security", "find-generic-password", "-s", service, "-w"]
    if account:
        command.extend(["-a", account])
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    token = result.stdout.strip()
    return token or None


def resolve_api_key(
    env: dict[str, str] | os._Environ[str] = os.environ,
    keychain_reader=read_api_key_from_keychain,
) -> str | None:
    return env.get("GRANOLA_API_KEY") or keychain_reader()


def sync_notes(
    notes: list[dict[str, Any]],
    vault: Path,
    *,
    include_transcript: bool,
    create_daily: bool,
    apply: bool,
    title_map: dict[str, str] | None = None,
) -> list[str]:
    messages: list[str] = []
    title_map = title_map or {}
    for note in notes:
        granola_id = str(note["id"])
        rel_path, markdown = render_meeting_note(
            note,
            include_transcript=include_transcript,
            title_override=title_map.get(granola_id),
        )
        existing_rel_path = find_existing_meeting_by_granola_id(vault, granola_id)
        if existing_rel_path:
            rel_path = existing_rel_path
        date = parse_date(note)
        stem = Path(rel_path).stem
        existing_path = vault / rel_path
        existing_text = read_text(existing_path) if existing_path.exists() else ""
        title = (
            title_map.get(granola_id)
            or extract_display_title(existing_text)
            or (note.get("title") or "Granola meeting").strip()
        )

        if apply:
            upsert_meeting_note(
                vault,
                rel_path,
                markdown,
                note,
                display_title=title_map.get(granola_id),
            )
            daily_changed = upsert_daily_meeting_link(
                vault, date, stem, title, create_daily=create_daily
            )
            messages.append(
                f"wrote {rel_path}" + ("; linked daily" if daily_changed else "")
            )
        else:
            messages.append(f"would write {rel_path}")
    return messages


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=DEFAULT_VAULT)
    parser.add_argument("--created-after")
    parser.add_argument("--created-before")
    parser.add_argument("--updated-after")
    parser.add_argument("--updated-before")
    parser.add_argument("--page-size", type=int, default=30)
    parser.add_argument("--include-transcript", action="store_true")
    parser.add_argument("--create-daily", action="store_true")
    parser.add_argument("--title-map", help="JSON mapping: Granola note id -> Korean display title")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--api-base", default=API_BASE)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    token = resolve_api_key()
    if not token:
        print(
            "GRANOLA_API_KEY 환경변수 또는 Keychain service "
            f"`{DEFAULT_KEYCHAIN_SERVICE}` 항목이 필요합니다.",
            file=sys.stderr,
        )
        return 2

    page_size = max(1, min(args.page_size, 30))
    client = GranolaClient(token, args.api_base)
    summaries = client.list_notes(
        created_after=args.created_after,
        created_before=args.created_before,
        updated_after=args.updated_after,
        updated_before=args.updated_before,
        page_size=page_size,
    )
    notes = [
        client.get_note(str(summary["id"]), include_transcript=args.include_transcript)
        for summary in summaries
    ]
    messages = sync_notes(
        notes,
        Path(args.vault),
        include_transcript=args.include_transcript,
        create_daily=args.create_daily,
        apply=args.apply,
        title_map=load_title_map(args.title_map),
    )
    for message in messages:
        print(message)
    if not args.apply:
        print("dry-run only. 실제 저장은 --apply를 붙이세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
