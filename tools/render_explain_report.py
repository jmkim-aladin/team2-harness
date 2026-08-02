#!/usr/bin/env python3
"""Render a DEV2 explain note (/ad:explain) as a shareable HTML reader with mermaid support."""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
from pathlib import Path

from render_architecture_report import (  # noqa: E402  (sibling module, same directory)
    find_title,
    render_markdown,
    split_frontmatter,
)


MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"

# 각 항목은 "이 중 하나로 시작하는 H2가 있어야 한다"는 후보 묶음이다.
REQUIRED_SECTIONS: tuple[tuple[str, ...], ...] = (
    ("한 줄",),
    ("배경",),
    ("직관",),
    ("무엇이 바뀌었나", "무엇을 알아냈나"),
    ("남은 위험",),
    ("퀴즈",),
    ("정답과 해설",),
)

HEADING2 = re.compile(r"^##\s+(.+?)\s*$")
MERMAID_BLOCK = re.compile(
    r"<pre><code class=\"language-mermaid\">(.*?)</code></pre>",
    re.DOTALL,
)
ANSWER_SECTION = re.compile(
    r"(<section id=\"[^\"]+\" data-section-title=\"정답과 해설[^\"]*\">\s*<h2>.*?</h2>)(.*?)(</section>)",
    re.DOTALL,
)


def section_titles(body: str) -> list[str]:
    titles = []
    for line in body.splitlines():
        match = HEADING2.match(line)
        if match:
            titles.append(re.sub(r"[`*_]", "", match.group(1)).strip())
    return titles


def validate_required_sections(body: str) -> list[str]:
    titles = section_titles(body)
    missing = []
    for candidates in REQUIRED_SECTIONS:
        if not any(title.startswith(candidate) for title in titles for candidate in candidates):
            missing.append(" 또는 ".join(candidates))
    return missing


def promote_mermaid(content: str) -> tuple[str, int]:
    """```mermaid 코드블록을 mermaid.js가 읽는 <pre class="mermaid">로 바꾼다.

    본문은 escape된 상태로 둔다. 브라우저가 textContent로 되돌려 주므로 mermaid 파싱에 문제가 없고,
    escape를 풀면 XSS 경로가 열린다.
    """
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f'<div class="diagram"><pre class="mermaid">{match.group(1)}</pre></div>'

    return MERMAID_BLOCK.sub(replace, content), count


def collapse_answers(content: str) -> str:
    """정답과 해설 섹션을 접어 둔다. 퀴즈를 풀기 전에 답이 먼저 보이면 퀴즈가 아니다."""

    def replace(match: re.Match[str]) -> str:
        heading, inner, closing = match.groups()
        return (
            f"{heading}<details class=\"answers\">"
            "<summary>정답과 해설 보기</summary>"
            f"<div class=\"answers-body\">{inner}</div></details>{closing}"
        )

    return ANSWER_SECTION.sub(replace, content, count=1)


def render_chips(metadata: dict[str, str]) -> str:
    labels = (
        ("mode", metadata.get("mode", "")),
        ("subject", metadata.get("subject", "")),
        ("base", metadata.get("base", "")),
        ("updated", metadata.get("updated_at", "")),
    )
    return "".join(
        f'<span class="chip"><b>{html.escape(key)}</b>{html.escape(value)}</span>'
        for key, value in labels
        if value
    )


def build_html(source: str, source_name: str, mermaid: bool = True) -> str:
    metadata, body = split_frontmatter(source)
    missing = validate_required_sections(body)
    if missing:
        raise ValueError(f"필수 섹션 누락: {', '.join(missing)}")

    title = find_title(metadata, body, Path(source_name).stem)
    content, navigation = render_markdown(body)
    content, diagram_count = promote_mermaid(content) if mermaid else (content, 0)
    content = collapse_answers(content)

    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    nav = "".join(f'<a href="#{section_id}">{html.escape(label)}</a>' for section_id, label in navigation)
    chips = render_chips(metadata)
    escaped_title = html.escape(title, quote=True)
    subtitle = html.escape(metadata.get("summary", "배경과 직관부터 읽고, 마지막 퀴즈로 이해를 확인하는 설명서입니다."), quote=True)
    mermaid_script = (
        f"""
  <script type="module">
    import mermaid from "{MERMAID_CDN}";
    mermaid.initialize({{ startOnLoad: true, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default", securityLevel: "strict" }});
  </script>"""
        if mermaid and diagram_count
        else ""
    )
    offline_note = (
        " · 다이어그램 렌더링에 mermaid CDN이 필요합니다"
        if mermaid_script
        else ""
    )

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
      --line: #d8dee7; --accent: #5b4bb7; --accent-soft: #eeecfa;
      --shadow: 0 18px 48px rgba(20, 31, 45, .09); --radius: 14px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; color: var(--ink); background: var(--paper); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif; line-height: 1.68; }}
    a {{ color: #1261a0; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
    .hero {{ padding: 52px max(24px, calc((100vw - 1180px) / 2)); color: #fff; background: linear-gradient(135deg, #241d47, #5b4bb7 62%, #7e6ad6); }}
    .eyebrow {{ margin: 0 0 10px; color: #d6cffa; font-size: 13px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ max-width: 980px; margin: 0; font-size: clamp(34px, 5vw, 62px); line-height: 1.12; letter-spacing: -.035em; }}
    .subtitle {{ max-width: 760px; margin: 18px 0 0; color: #e2ddf7; font-size: 17px; }}
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
    pre {{ overflow: auto; margin: 18px 0; padding: 18px; border: 1px solid #2b3d48; border-radius: 10px; background: #14232d; color: #e6f1f5; white-space: pre; }} pre code {{ padding: 0; border: 0; background: transparent; color: inherit; white-space: pre; overflow-wrap: normal; }}
    .diagram {{ margin: 20px 0; padding: 18px; border: 1px solid var(--line); border-radius: 10px; background: #fbfcfd; text-align: center; overflow-x: auto; }}
    .diagram pre.mermaid {{ margin: 0; padding: 0; border: 0; background: transparent; color: inherit; text-align: center; }}
    .table-scroll {{ overflow-x: auto; margin: 18px 0; border: 1px solid var(--line); border-radius: 10px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--surface); font-size: 14px; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }} th {{ position: sticky; top: 0; background: #eef3f6; font-weight: 800; }} tr:last-child td {{ border-bottom: 0; }} tbody tr:hover {{ background: #f8fafb; }}
    details.answers {{ margin: 4px 0 0; padding: 14px 18px; border: 1px dashed var(--accent); border-radius: 10px; background: var(--accent-soft); }}
    details.answers summary {{ cursor: pointer; font-weight: 800; color: var(--accent); }}
    details.answers .answers-body {{ margin-top: 12px; }}
    hr {{ height: 1px; border: 0; background: var(--line); margin: 28px 0; }}
    .footer {{ max-width: 1180px; margin: -42px auto 40px; padding: 0 24px; color: var(--muted); font-size: 12px; }}
    @media (max-width: 860px) {{ .hero {{ padding: 38px 22px; }} .layout {{ grid-template-columns: 1fr; padding: 20px 14px 54px; }} .report-nav {{ position: static; display: flex; max-height: none; overflow-x: auto; }} .report-nav::before {{ display: none; }} .report-nav a {{ flex: 0 0 auto; border: 1px solid var(--line); }} section {{ padding: 22px 18px; }} }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --ink: #e5edf2; --muted: #aebdca; --paper: #0e171d; --surface: #15222a; --line: #30414c; --accent: #a99cf0; --accent-soft: #241f3d; --shadow: none; }}
      a {{ color: #83c8ff; }} code {{ border-color: #3a4e5a; background: #20313b; color: #e4edf1; }} th {{ background: #1c2c35; }} tbody tr:hover {{ background: #1b2b34; }} .diagram {{ background: #101c23; }}
    }}
    @media print {{
      :root {{ --paper: #fff; --surface: #fff; --ink: #111; --line: #bbb; --shadow: none; }}
      body {{ background: #fff; font-size: 11pt; }} .hero {{ padding: 20mm 14mm 10mm; color: #111; background: #fff; border-bottom: 2px solid #222; }} .eyebrow, .subtitle {{ color: #444; }} .chips {{ display: none; }}
      .layout {{ display: block; max-width: none; padding: 8mm 14mm; }} .report-nav {{ display: none; }} section {{ break-inside: avoid-page; margin-bottom: 8mm; padding: 0; border: 0; box-shadow: none; }} h2, h3 {{ break-after: avoid; }} a {{ color: inherit; text-decoration: none; }} details.answers[open] {{ break-inside: avoid-page; }} .footer {{ margin: 0; padding: 0 14mm 10mm; }}
    }}
  </style>
</head>
<body data-source-sha256="{source_hash}" data-diagrams="{diagram_count}">
  <header class="hero">
    <p class="eyebrow">DEV2 Explain</p>
    <h1>{escaped_title}</h1>
    <p class="subtitle">{subtitle}</p>
    <div class="chips">{chips}</div>
  </header>
  <div class="layout">
    <nav class="report-nav" aria-label="설명서 목차">{nav}</nav>
    <main>{content}</main>
  </div>
  <footer class="footer">Generated from {html.escape(source_name)} · SHA-256 {source_hash}{offline_note}</footer>{mermaid_script}
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="explain note Markdown path")
    parser.add_argument("output", type=Path, help="HTML output path")
    parser.add_argument(
        "--no-mermaid",
        action="store_true",
        help="mermaid 스크립트를 넣지 않는다 (오프라인 공유용, 다이어그램은 코드블록으로 남는다)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input.read_text(encoding="utf-8")
    try:
        rendered = build_html(source, args.input.name, mermaid=not args.no_mermaid)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
