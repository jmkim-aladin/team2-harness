#!/usr/bin/env python3
"""Enrich team2 vault notes with LLM-wiki relation frontmatter.

The tool only performs deterministic backfill:
- DEV2 ids in text become related_tickets
- service/service_id fields become related_services
- daily meeting wikilinks become related_meetings
- ticket services are propagated to notes that reference those tickets

Default is dry-run. Pass --apply to write files.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
RELATION_FIELDS = [
    "related_services",
    "related_tickets",
    "related_okrs",
    "related_meetings",
    "related_domains",
    "related_projects",
]

ENRICH_TYPES = {
    "ticket",
    "worksheet",
    "meeting",
    "okr",
    "daily",
    "weekly-report",
    "sprint",
    "analysis",
    "decision",
    "proposal",
    "project",
    "incident",
}

DEFAULT_SERVICE_KEYWORDS: dict[str, list[str]] = {
    "max": ["max", "만권당", "max-api"],
    "tobe": ["tobe", "투비", "애드몹", "광고보고"],
    "shopping": ["shopping", "알라딘 쇼핑", "멀티캠퍼스", "삼성ds", "b2b솔루션"],
    "blog": ["blog", "블로그", "북플", "bookple"],
    "storefront": ["storefront", "스토어프론트", "전용몰", "테넌트", "멀티 테넌시"],
    "bazaar": ["bazaar", "바자"],
    "naru": ["naru", "나루", "sso", "oidc"],
    "aasm": ["aasm", "asset manager"],
    "caravan": ["caravan", "대기열", "virtual waiting room"],
}


class EnrichResult:
    def __init__(self, text: str, changed: bool, added_fields: set[str]) -> None:
        self.text = text
        self.changed = changed
        self.added_fields = added_fields


def split_frontmatter(text: str) -> tuple[list[str], str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm = text[4:end].splitlines()
    body = text[end + 5 :]
    if body.startswith("\n"):
        body = body[1:]
    return fm, body


def join_frontmatter(lines: list[str], body: str) -> str:
    return "---\n" + "\n".join(lines).rstrip() + "\n---\n\n" + body.lstrip("\n")


def frontmatter_value(lines: list[str], field: str) -> str | None:
    prefix = f"{field}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def get_frontmatter_values(text: str, field: str) -> list[str]:
    split = split_frontmatter(text)
    if not split:
        return []
    lines, _ = split
    return get_field_values(lines, field)


def get_field_values(lines: list[str], field: str) -> list[str]:
    prefix = f"{field}:"
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        raw = line[len(prefix) :].strip()
        if raw == "[]":
            return []
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner:
                return []
            return [clean_value(v) for v in inner.split(",") if clean_value(v)]
        if raw:
            return [clean_value(raw)]
        values: list[str] = []
        for child in lines[index + 1 :]:
            if re.match(r"^[A-Za-z0-9_-]+:", child):
                break
            match = re.match(r"^\s*-\s+(.+)$", child)
            if match:
                values.append(clean_value(match.group(1)))
        return values
    return []


def clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def set_field_values(lines: list[str], field: str, values: list[str]) -> tuple[list[str], bool]:
    rendered = render_field(field, values)
    prefix = f"{field}:"
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        end = index + 1
        while end < len(lines) and (lines[end].startswith(" ") or lines[end].startswith("\t")):
            end += 1
        current = lines[index:end]
        if current == rendered:
            return lines, False
        return lines[:index] + rendered + lines[end:], True
    return lines + rendered, True


def set_scalar_field(lines: list[str], field: str, value: str) -> tuple[list[str], bool]:
    rendered = f"{field}: {value}"
    prefix = f"{field}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            if line == rendered:
                return lines, False
            return lines[:index] + [rendered] + lines[index + 1 :], True
    return lines + [rendered], True


def render_field(field: str, values: list[str]) -> list[str]:
    if not values:
        return [f"{field}: []"]
    return [f"{field}:"] + [f"  - \"{value}\"" for value in values]


def merge_sorted(existing: list[str], additions: set[str]) -> list[str]:
    merged = {v for v in existing if v}
    merged.update(additions)
    return sorted(merged, key=lambda v: v.lower())


def normalize_service(value: str) -> str | None:
    match = re.search(r"\[\[([a-z0-9-]+)(?:\|[^\]]+)?\]\]", value, re.IGNORECASE)
    raw = match.group(1) if match else value
    raw = raw.strip().lower()
    if raw in DEFAULT_SERVICE_KEYWORDS:
        return f"[[{raw}]]"
    return None


def normalize_ticket(ticket_id: str) -> str:
    match = re.search(r"DEV2-\d+", ticket_id, re.IGNORECASE)
    if not match:
        cleaned = ticket_id.strip().lower()
    else:
        cleaned = match.group(0).lower()
    return f"[[{cleaned}]]"


def extract_ticket_ids(text: str) -> set[str]:
    return {m.group(0).upper() for m in re.finditer(r"\bDEV2-\d+\b", text, re.IGNORECASE)}


def extract_wikilinks(text: str) -> set[str]:
    links = set()
    for match in re.finditer(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", text):
        links.add(match.group(1).strip())
    return links


def infer_services_from_keywords(text: str, service_keywords: dict[str, list[str]]) -> set[str]:
    lowered = text.lower()
    out = set()
    for service, keywords in service_keywords.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            out.add(f"[[{service}]]")
    return out


def own_ticket_id(lines: list[str]) -> str | None:
    raw = frontmatter_value(lines, "ticket_id")
    if not raw:
        return None
    match = re.search(r"DEV2-\d+", raw, re.IGNORECASE)
    return match.group(0).upper() if match else None


def enrich_markdown(
    text: str,
    rel_path: str,
    *,
    ticket_services: dict[str, set[str]],
    meeting_services: dict[str, set[str]],
    service_keywords: dict[str, list[str]],
) -> EnrichResult:
    split = split_frontmatter(text)
    if not split:
        return EnrichResult(text=text, changed=False, added_fields=set())

    lines, body = split
    full_text = "\n".join(lines) + "\n" + body
    note_type = clean_value(frontmatter_value(lines, "type") or "")
    if note_type not in ENRICH_TYPES:
        return EnrichResult(text=text, changed=False, added_fields=set())
    added_fields: set[str] = set()
    changed = False

    services: set[str] = set()
    tickets: set[str] = set()
    meetings: set[str] = set()
    relation_sources: set[str] = set(get_field_values(lines, "relation_sources"))

    for field in ("service", "service_id"):
        for value in get_field_values(lines, field):
            service = normalize_service(value)
            if service:
                services.add(service)
                relation_sources.add("frontmatter")

    ticket_ids = extract_ticket_ids(full_text)
    own_ticket = own_ticket_id(lines)
    for ticket_id in ticket_ids:
        if ticket_id == own_ticket:
            continue
        tickets.add(normalize_ticket(ticket_id))
        relation_sources.add("body-dev2")
        services.update(ticket_services.get(ticket_id, set()))

    if note_type in {"meeting", "project", "analysis", "decision", "proposal"}:
        inferred_services = infer_services_from_keywords(full_text, service_keywords)
        if inferred_services:
            services.update(inferred_services)
            relation_sources.add("service-keyword")

    if note_type == "daily":
        for link in extract_wikilinks(body):
            if re.match(r"^\d{4}-\d{2}-\d{2}-.+", link):
                meetings.add(f"[[{link}]]")
                relation_sources.add("daily-links")
                services.update(meeting_services.get(link, set()))

    field_additions = {
        "related_services": services,
        "related_tickets": tickets,
        "related_meetings": meetings,
    }
    for field, additions in field_additions.items():
        if not additions:
            continue
        existing = get_field_values(lines, field)
        new_values = merge_sorted(existing, additions)
        if new_values != existing:
            lines, did_change = set_field_values(lines, field, new_values)
            changed = changed or did_change
            added_fields.add(field)

    if added_fields:
        if not frontmatter_value(lines, "relation_status"):
            lines, did_change = set_scalar_field(lines, "relation_status", "inferred")
            changed = changed or did_change
            added_fields.add("relation_status")
        relation_sources.add("auto-backfill")
        existing_sources = get_field_values(lines, "relation_sources")
        lines, did_change = set_field_values(lines, "relation_sources", merge_sorted(existing_sources, relation_sources))
        changed = changed or did_change
        added_fields.add("relation_sources")

    return EnrichResult(text=join_frontmatter(lines, body), changed=changed, added_fields=added_fields)


def collect_markdown_files(vault: Path, files: list[str] | None = None) -> list[Path]:
    if files:
        out = []
        for item in files:
            path = Path(item)
            if not path.is_absolute():
                path = vault / item
            if path.exists() and path.suffix == ".md":
                out.append(path)
        return out
    return [
        path for path in sorted((vault / "wiki").rglob("*.md"))
        if path.name != "_index.md" and not path.name.endswith("-index.md")
    ]


def build_ticket_service_map(vault: Path, paths: list[Path]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        split = split_frontmatter(text)
        if not split:
            continue
        lines, _ = split
        if clean_value(frontmatter_value(lines, "type") or "") != "ticket":
            continue
        ticket_id = own_ticket_id(lines)
        if not ticket_id:
            continue
        services = set()
        for field in ("service", "service_id", "related_services"):
            for value in get_field_values(lines, field):
                service = normalize_service(value)
                if service:
                    services.add(service)
        if services:
            out[ticket_id] = services
    return out


def build_meeting_service_map(vault: Path, paths: list[Path]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        split = split_frontmatter(text)
        if not split:
            continue
        lines, _ = split
        if clean_value(frontmatter_value(lines, "type") or "") != "meeting":
            continue
        services = set()
        for value in get_field_values(lines, "related_services"):
            service = normalize_service(value)
            if service:
                services.add(service)
        if services:
            out[path.stem] = services
    return out


def enrich_vault(vault: Path, *, apply: bool = False, files: list[str] | None = None) -> list[str]:
    paths = collect_markdown_files(vault, files)
    ticket_services = build_ticket_service_map(vault, paths)
    meeting_services = build_meeting_service_map(vault, paths)
    messages: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.relative_to(vault).as_posix()
        result = enrich_markdown(
            text,
            rel,
            ticket_services=ticket_services,
            meeting_services=meeting_services,
            service_keywords=DEFAULT_SERVICE_KEYWORDS,
        )
        if not result.changed:
            continue
        if apply:
            path.write_text(result.text, encoding="utf-8")
            messages.append(f"updated {rel}")
        else:
            fields = ", ".join(sorted(result.added_fields))
            messages.append(f"would update {rel} ({fields})")
    return messages


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=DEFAULT_VAULT)
    parser.add_argument("--files", nargs="*")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    messages = enrich_vault(Path(args.vault), apply=args.apply, files=args.files)
    for message in messages:
        print(message)
    if not args.apply:
        print("dry-run only. 실제 저장은 --apply를 붙이세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
