#!/usr/bin/env python3
"""Render a DEV2 architecture analysis Markdown note as a self-contained HTML reader."""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
from pathlib import Path
from typing import Iterable


REQUIRED_SECTIONS = (
    "결론",
    "분석 기준",
    "아키텍처 맵",
    "설계 철학",
    "Clean·Hexagonal·DDD 평가",
    "우선순위 발견",
    "네이밍과 구조",
    "이어갈 원칙",
    "검증과 한계",
)

TABLE_SEPARATOR = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
LIST_ITEM = re.compile(r"^\s*[-*+]\s+(.+)$")
ORDERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(.+)$")
HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")


def split_frontmatter(source: str) -> tuple[dict[str, str], str]:
    lines = source.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, source

    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return {}, source

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata, "\n".join(lines[end + 1 :]).lstrip()


def heading_text(raw: str) -> str:
    return re.sub(r"[`*_]", "", raw).strip()


def find_title(metadata: dict[str, str], body: str, fallback: str) -> str:
    if metadata.get("title"):
        return metadata["title"]
    for line in body.splitlines():
        match = HEADING.match(line)
        if match and len(match.group(1)) == 1:
            return heading_text(match.group(2))
    return fallback


def validate_required_sections(body: str) -> list[str]:
    headings = {
        heading_text(match.group(2))
        for line in body.splitlines()
        if (match := HEADING.match(line)) and len(match.group(1)) == 2
    }
    return [section for section in REQUIRED_SECTIONS if section not in headings]


def safe_href(raw: str) -> str:
    value = raw.strip()
    lowered = value.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:")):
        return "#"
    return value


def render_inline(raw: str) -> str:
    tokens: list[str] = []

    def protect(value: str) -> str:
        tokens.append(value)
        return f"\x00{len(tokens) - 1}\x00"

    def code(match: re.Match[str]) -> str:
        return protect(f"<code>{html.escape(match.group(1), quote=True)}</code>")

    def link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1), quote=True)
        href = html.escape(safe_href(match.group(2)), quote=True)
        return protect(f'<a href="{href}">{label}</a>')

    value = re.sub(r"`([^`]+)`", code, raw)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, value)
    value = html.escape(value, quote=True)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
    for index, token in enumerate(tokens):
        value = value.replace(html.escape(f"\x00{index}\x00"), token)
    return value


def split_table_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip() for cell in value.split("|")]


def render_table(lines: list[str], start: int) -> tuple[str, int]:
    headers = split_table_row(lines[start])
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(split_table_row(lines[index]))
        index += 1

    output = ["<div class=\"table-scroll\"><table><thead><tr>"]
    output.extend(f"<th>{render_inline(cell)}</th>" for cell in headers)
    output.append("</tr></thead><tbody>")
    for row in rows:
        output.append("<tr>")
        for cell in row:
            priority = cell.upper() if cell.upper() in {"P0", "P1", "P2", "P3"} else None
            if priority:
                content = f'<span class="priority {priority.lower()}">{priority}</span>'
            else:
                content = render_inline(cell)
            output.append(f"<td>{content}</td>")
        output.append("</tr>")
    output.append("</tbody></table></div>")
    return "".join(output), index


def starts_special_block(lines: list[str], index: int) -> bool:
    line = lines[index]
    if not line.strip():
        return True
    if HEADING.match(line) or line.startswith("```") or line.lstrip().startswith(">"):
        return True
    if LIST_ITEM.match(line) or ORDERED_ITEM.match(line) or line.strip() in {"---", "***", "___"}:
        return True
    return index + 1 < len(lines) and "|" in line and TABLE_SEPARATOR.match(lines[index + 1]) is not None


def render_markdown(body: str) -> tuple[str, list[tuple[str, str]]]:
    lines = body.splitlines()
    output: list[str] = []
    navigation: list[tuple[str, str]] = []
    section_open = False
    section_number = 0
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        if line.startswith("```"):
            language = re.sub(r"[^a-zA-Z0-9_-]", "", line[3:].strip())
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1 if index < len(lines) else 0
            class_name = f' class="language-{language}"' if language else ""
            code_text = html.escape("\n".join(code_lines), quote=True)
            output.append(f"<pre><code{class_name}>{code_text}</code></pre>")
            continue

        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading_text(heading.group(2))
            if level == 1:
                index += 1
                continue
            if level == 2:
                if section_open:
                    output.append("</section>")
                section_number += 1
                section_id = f"section-{section_number}"
                navigation.append((section_id, title))
                output.append(f'<section id="{section_id}" data-section-title="{html.escape(title, quote=True)}">')
                output.append(f"<h2><span class=\"section-number\">{section_number:02d}</span>{render_inline(title)}</h2>")
                section_open = True
            else:
                output.append(f"<h{level}>{render_inline(title)}</h{level}>")
            index += 1
            continue

        if index + 1 < len(lines) and "|" in line and TABLE_SEPARATOR.match(lines[index + 1]):
            rendered, index = render_table(lines, index)
            output.append(rendered)
            continue

        unordered = LIST_ITEM.match(line)
        ordered = ORDERED_ITEM.match(line)
        if unordered or ordered:
            tag = "ul" if unordered else "ol"
            pattern = LIST_ITEM if unordered else ORDERED_ITEM
            items: list[str] = []
            while index < len(lines) and (match := pattern.match(lines[index])):
                items.append(f"<li>{render_inline(match.group(1))}</li>")
                index += 1
            output.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        if line.lstrip().startswith(">"):
            quotes: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quotes.append(lines[index].lstrip()[1:].lstrip())
                index += 1
            output.append(f"<blockquote><p>{render_inline(' '.join(quotes))}</p></blockquote>")
            continue

        if line.strip() in {"---", "***", "___"}:
            output.append("<hr>")
            index += 1
            continue

        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and not starts_special_block(lines, index):
            paragraph.append(lines[index].strip())
            index += 1
        output.append(f"<p>{render_inline(' '.join(paragraph))}</p>")

    if section_open:
        output.append("</section>")
    return "\n".join(output), navigation


def render_chips(metadata: dict[str, str]) -> str:
    labels: Iterable[tuple[str, str]] = (
        ("service", metadata.get("service_id", "")),
        ("updated", metadata.get("updated_at", "")),
        ("evidence", metadata.get("evidence_level", "")),
        ("review", metadata.get("review_state", "")),
    )
    return "".join(
        f'<span class="chip"><b>{html.escape(key)}</b>{html.escape(value)}</span>'
        for key, value in labels
        if value
    )


def build_html(source: str, source_name: str) -> str:
    metadata, body = split_frontmatter(source)
    missing = validate_required_sections(body)
    if missing:
        raise ValueError(f"필수 섹션 누락: {', '.join(missing)}")

    title = find_title(metadata, body, Path(source_name).stem)
    content, navigation = render_markdown(body)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    nav = "".join(f'<a href="#{section_id}">{html.escape(label)}</a>' for section_id, label in navigation)
    chips = render_chips(metadata)
    escaped_title = html.escape(title, quote=True)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{escaped_title}</title>
  <style>
    :root {{
      --ink: #17212b; --muted: #667085; --paper: #f4f6f8; --surface: #ffffff;
      --line: #d8dee7; --accent: #16697a; --accent-soft: #e8f4f5;
      --p0: #b42318; --p1: #b54708; --p2: #175cd3; --p3: #475467;
      --shadow: 0 18px 48px rgba(20, 31, 45, .09); --radius: 14px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; color: var(--ink); background: var(--paper); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif; line-height: 1.68; }}
    a {{ color: #1261a0; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
    .hero {{ padding: 52px max(24px, calc((100vw - 1180px) / 2)); color: #fff; background: linear-gradient(135deg, #102a36, #16697a 62%, #1c7c83); }}
    .eyebrow {{ margin: 0 0 10px; color: #bfe8e8; font-size: 13px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ max-width: 980px; margin: 0; font-size: clamp(34px, 5vw, 62px); line-height: 1.12; letter-spacing: -.035em; }}
    .subtitle {{ max-width: 760px; margin: 18px 0 0; color: #d8eeee; font-size: 17px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; }}
    .chip {{ display: inline-flex; gap: 7px; align-items: center; min-height: 32px; padding: 5px 11px; border: 1px solid rgba(255,255,255,.28); border-radius: 999px; background: rgba(255,255,255,.11); font-size: 13px; }}
    .layout {{ display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 34px; max-width: 1240px; margin: 0 auto; padding: 34px 24px 72px; }}
    .report-nav {{ position: sticky; top: 20px; align-self: start; display: grid; gap: 5px; max-height: calc(100vh - 40px); overflow: auto; padding: 14px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); box-shadow: var(--shadow); }}
    .report-nav::before {{ content: "목차"; padding: 6px 9px 10px; color: var(--muted); font-size: 12px; font-weight: 850; letter-spacing: .08em; }}
    .report-nav a {{ padding: 8px 10px; border-radius: 8px; color: var(--ink); font-size: 14px; }} .report-nav a:hover {{ background: var(--accent-soft); text-decoration: none; }}
    main {{ min-width: 0; }}
    section {{ margin: 0 0 24px; padding: clamp(22px, 4vw, 38px); border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); box-shadow: var(--shadow); scroll-margin-top: 18px; }}
    h2 {{ display: flex; gap: 13px; align-items: baseline; margin: 0 0 24px; font-size: clamp(24px, 3vw, 34px); line-height: 1.25; letter-spacing: -.025em; }}
    .section-number {{ color: var(--accent); font: 800 13px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    h3 {{ margin: 30px 0 12px; font-size: 20px; }} h4 {{ margin: 24px 0 10px; font-size: 17px; }}
    p {{ margin: 11px 0; }} ul, ol {{ padding-left: 24px; }} li + li {{ margin-top: 6px; }}
    blockquote {{ margin: 18px 0; padding: 16px 20px; border-left: 5px solid var(--accent); border-radius: 0 10px 10px 0; background: var(--accent-soft); font-size: 17px; }} blockquote p {{ margin: 0; }}
    code {{ padding: 2px 6px; border: 1px solid #d8e1e8; border-radius: 6px; background: #edf2f5; color: #243746; font: .9em ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; overflow-wrap: anywhere; }}
    pre {{ overflow: auto; margin: 18px 0; padding: 18px; border: 1px solid #2b3d48; border-radius: 10px; background: #14232d; color: #e6f1f5; }} pre code {{ padding: 0; border: 0; background: transparent; color: inherit; white-space: pre; overflow-wrap: normal; }}
    .table-scroll {{ overflow-x: auto; margin: 18px 0; border: 1px solid var(--line); border-radius: 10px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--surface); font-size: 14px; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }} th {{ position: sticky; top: 0; background: #eef3f6; font-weight: 800; }} tr:last-child td {{ border-bottom: 0; }} tbody tr:hover {{ background: #f8fafb; }}
    .priority {{ display: inline-flex; min-width: 38px; justify-content: center; padding: 3px 8px; border-radius: 999px; color: #fff; font-weight: 850; font-size: 12px; }} .p0 {{ background: var(--p0); }} .p1 {{ background: var(--p1); }} .p2 {{ background: var(--p2); }} .p3 {{ background: var(--p3); }}
    hr {{ height: 1px; border: 0; background: var(--line); margin: 28px 0; }}
    .footer {{ max-width: 1180px; margin: -42px auto 40px; padding: 0 24px; color: var(--muted); font-size: 12px; }}
    @media (max-width: 860px) {{ .hero {{ padding: 38px 22px; }} .layout {{ grid-template-columns: 1fr; padding: 20px 14px 54px; }} .report-nav {{ position: static; display: flex; max-height: none; overflow-x: auto; }} .report-nav::before {{ display: none; }} .report-nav a {{ flex: 0 0 auto; border: 1px solid var(--line); }} section {{ padding: 22px 18px; }} }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --ink: #e5edf2; --muted: #aebdca; --paper: #0e171d; --surface: #15222a; --line: #30414c; --accent: #69c3c5; --accent-soft: #17363d; --shadow: none; }}
      a {{ color: #83c8ff; }} code {{ border-color: #3a4e5a; background: #20313b; color: #e4edf1; }} th {{ background: #1c2c35; }} tbody tr:hover {{ background: #1b2b34; }}
    }}
    @media print {{
      :root {{ --paper: #fff; --surface: #fff; --ink: #111; --line: #bbb; --shadow: none; }}
      body {{ background: #fff; font-size: 11pt; }} .hero {{ padding: 20mm 14mm 10mm; color: #111; background: #fff; border-bottom: 2px solid #222; }} .eyebrow, .subtitle {{ color: #444; }} .chips {{ display: none; }}
      .layout {{ display: block; max-width: none; padding: 8mm 14mm; }} .report-nav {{ display: none; }} section {{ break-inside: avoid-page; margin-bottom: 8mm; padding: 0; border: 0; box-shadow: none; }} h2, h3 {{ break-after: avoid; }} a {{ color: inherit; text-decoration: none; }} .footer {{ margin: 0; padding: 0 14mm 10mm; }}
    }}
  </style>
</head>
<body data-source-sha256="{source_hash}">
  <header class="hero">
    <p class="eyebrow">DEV2 Repository Architecture Analysis</p>
    <h1>{escaped_title}</h1>
    <p class="subtitle">소스 구조와 실행 흐름을 근거로 설계 철학, 아키텍처 경계, 운영 위험과 이어갈 원칙을 함께 읽는 보고서입니다.</p>
    <div class="chips">{chips}</div>
  </header>
  <div class="layout">
    <nav class="report-nav" aria-label="보고서 목차">{nav}</nav>
    <main>{content}</main>
  </div>
  <footer class="footer">Generated from {html.escape(source_name)} · SHA-256 {source_hash}</footer>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="architecture analysis Markdown path")
    parser.add_argument("output", type=Path, help="self-contained HTML output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input.read_text(encoding="utf-8")
    try:
        rendered = build_html(source, args.input.name)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
