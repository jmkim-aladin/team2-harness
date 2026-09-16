#!/usr/bin/env python3
"""하네스 지시문 표기 규약 린트 — 규약을 문장이 아니라 검사로 지킨다.

`policies/instruction-precedence-policy.md` §표기 규약의 준수를 기계로 판정한다.
누적 위반은 베이스라인으로 허용하되 신규 유입은 차단하고(ratchet), 해결된 항목은 자동 하향한다.

사용법:
    python3 tools/lint_harness_rules.py                       # 전체 발견 + 규칙별 요약
    python3 tools/lint_harness_rules.py --summary             # 규칙별 카운트 (베이스라인 대비 추이)
    python3 tools/lint_harness_rules.py --json                # 발견 목록 JSON
    python3 tools/lint_harness_rules.py --check               # 신규 위반·회귀만 판정 (CI·pre-commit)
    python3 tools/lint_harness_rules.py --update-baseline [--accept-new "사유"]
    python3 tools/lint_harness_rules.py --sync-generated      # generated 블록을 canonical 본문으로 갱신
    python3 tools/lint_harness_rules.py <path...>             # 대상 경로 지정 (기본 대상 override)

--check 에서 신규 block 위반·R1b 회귀·R7 드리프트가 있으면 exit 1.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_REL = "docs/harness-rule-baseline.json"
SCHEMA_VERSION = 2
MATCHER_VERSION = 8

# 기본 대상 — 하네스 지시문이 사는 곳만. 서술 문서(docs/ 일반)는 규약 대상이 아니다
MD_PATTERNS = [
    "CLAUDE.md", "AGENTS.md", "memory/*.md", "policies/**/*.md",
    ".claude/commands/ad/*.md", ".codex/skills/**/*.md",
    "templates/**/*.md", "docs/sprint/*.md", "docs/agents/*.md",
]
YAML_PATTERNS = ["catalog/*.yaml"]
EXCLUDE_PARTS = {"vendor", ".planning", "node_modules"}

RULES = {
    "R1a": ("rule-intensity-unclassified", "block"),
    "R1b": ("rule-lost-reason", "block"),
    "R2": ("model-overlap", "block"),
    "R3": ("emphasis-inflation", "block"),
    "R4": ("fixed-sequence", "warn"),
    "R5": ("oversized-doc", "warn"),
    "R6": ("missing-verification-loop", "block"),
    "R7": ("generated-block-drift", "block"),
}
RULE_ORDER = ["R1a", "R1b", "R2", "R3", "R4", "R5", "R6", "R7"]
# 베이스라인으로 유예하는 규칙 — R1b(회귀)·R7(드리프트)은 항상 실패해야 의미가 있다
BASELINED = ["R1a", "R2", "R3", "R4", "R5", "R6"]

HARD_TOKEN = re.compile(r"반드시|필수|금지|하지 않는다|하지 마|절대(?!\s*[/／]?\s*(경로|상대|URL|일자|값|좌표|주소|시간))|무조건")
# 규칙이 아닌 '라벨·명사구' 용법 — 표 셀의 필수/선택, [분할 필수], 목록 도입 라벨("확인 필수 항목:"), 규칙을 가리키는 명사구("금지 사항", "SP 직접 호출 금지" 등록부 행).
# 이걸 지운 뒤에도 하드 토큰이 남아야 규칙이다 (2026-09-16 전수 손판정: 237건 중 36건이 이 용법)
LABEL_USE = re.compile(
    r"\[분할 필수\]|\[필수\]|\(필수\)|\*\*필수\*\*|\|\s*필수\s*(?=\|)|선택\s*\|\s*필수"
    r"|필수 (항목|필드|요소|조치|테스트|커스텀|규칙|섹션|status)|금지 (사항|정보|어휘|규칙|포함|영역)"
    r"|(호출|푸시|배포|사용|반영) 금지(?=[\s*|)\]]|$)|필수(?=\s*(\)|\]|\*\*|$))"
    r"|\|\s*[^|]{0,10}필수\s*(?=\|)"          # 짧은 표 셀 'SP 3 필수'
)
BOLD_LABEL_LINE = re.compile(r"^\*\*[^*]{1,20}\*\*:?$")   # '**필수 작성 요소**' 처럼 소제목 역할의 bold 한 줄
INTRO_LABEL = re.compile(r":\s*\**\s*$")   # "확인 필수 항목:" 처럼 목록을 여는 라벨 — 규칙은 그 아래 항목들이다
# item 본문·하위 불릿에서는 서술형 근거도 인정한다
# 한국어 인과 어미(~이므로/~라서/~니까)는 "왜"를 담는 가장 흔한 형태 — 빠지면 잘 쓴 규칙이 부채로 집계된다 (2026-09-16 code-review.md 파일럿: 15건 중 3건이 이 어미만 있었음)
# 결과·목적 서술("~하면 깨진다", "~하기 위함", "되돌릴 수 없다")도 '왜'다 — 인과 접속사만 세면 설명형 규칙이 부채로 잡힌다
LOCAL_REASON_CUE = re.compile(r"근거:|때문|위해|위함|않으면|없으면|이유|왜 |므로|라서|니까|실패한|깨진|낡는|어긋나|되돌릴 수 없|비가역|보안상|운영상|정책상|기본:|조정 가능|단,|—\s*\S")
# 조상 preamble 은 명시 표지만 인정한다 — 서술형까지 허용하면 절 하나가 하위 하드룰 전부를 면책한다
ANCESTOR_REASON_CUE = re.compile(r"근거:|의도:|이유:")
EXAMPLE_ITEM = re.compile(r"나쁨:|좋음:|예:|예시")
MODEL_OVERLAP = re.compile(
    r"다시 확인(하|해)|재확인하|스스로 검증|자기 검증|꼼꼼히|차근차근"
    r"|단계별로 (생각|추론)|step[- ]by[- ]step|think step|explain your reasoning"
    r"|추론 과정을 설명|적극(적으로)? 위임|\d+번마다 (요약|보고)", re.I)
NEGATED = re.compile(r"재지시|넣지 않|삭제|잔재|안티패턴|나쁨:|하지 않는다")
EMPHASIS = [
    re.compile(r"\b(IMPORTANT|CRITICAL|MUST|NEVER|ALWAYS|MANDATORY)\b"),
    re.compile(r"!!+"),
    re.compile(r"\*\*반드시\*\*"),
]
STEP_HEADING = re.compile(r"Step ?\d|\d+단계")
FLEX_CUE = re.compile(r"기본[:：]|기본 순서|이탈|조정 가능|조정할 수|순서.*바꿀|바꿔도|상황에 맞게|판단 경계|기본 접근|권장 순서")
# R4의 번호 목록 트리거는 에이전트 절차 문서에만 — 가이드·템플릿의 "N. 제목" 절 번호는 구조이지 고정 시퀀스가 아니다
R4_PROCEDURE_SCOPE = (".claude/commands/ad/", ".codex/skills/", "memory/", "CLAUDE.md", "AGENTS.md")

# 추정 토큰 한도 — 한글 1자≈1tok, 그 외 4자≈1tok. 바이트는 한국어(3B/자)를 3배로 세어 쓰지 않는다
LIMITS = {".claude/commands/ad": 6000, "policies": 4000, "default": 8000}


def approx_tokens(text):
    ko = sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")
    return ko + (len(text) - ko) // 4

LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|.-]+\|?\s*$")
INLINE_CODE = re.compile(r"`[^`]*`")

CANONICAL_OPEN = re.compile(r"^<!--\s*canonical:([A-Za-z0-9_-]+)(?:\s+targets=(\S+))?\s*-->$")
CANONICAL_CLOSE = re.compile(r"^<!--\s*/canonical:([A-Za-z0-9_-]+)\s*-->$")
GENERATED_OPEN = re.compile(r"^<!--\s*generated:([A-Za-z0-9_-]+)\s+source=(\S+)\s*-->$")
GENERATED_CLOSE = re.compile(r"^<!--\s*/generated:([A-Za-z0-9_-]+)\s*-->$")


# --- 대상 수집 ----------------------------------------------------------------

def _excluded(relpath):
    return any(part in EXCLUDE_PARTS for part in relpath.split(os.sep))


def collect_targets(root, paths):
    """(md 파일, yaml 파일) 절대경로 목록. paths 가 있으면 기본 대상을 대체한다."""
    md, yaml_files = [], []
    if paths:
        for p in paths:
            ap = os.path.abspath(p)
            if os.path.isfile(ap):
                found = [ap]
            else:
                found = []
                for base, dirs, files in os.walk(ap):
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_PARTS and d != ".git"]
                    found += [os.path.join(base, f) for f in files]
            for f in found:
                ext = os.path.splitext(f)[1].lower()
                if ext == ".md":
                    md.append(f)
                elif ext in (".yaml", ".yml"):
                    yaml_files.append(f)
    else:
        for pat in MD_PATTERNS:
            md += glob.glob(os.path.join(root, pat), recursive=True)
        for pat in YAML_PATTERNS:
            yaml_files += glob.glob(os.path.join(root, pat), recursive=True)
    keep = lambda fs: sorted({f for f in fs
                              if os.path.isfile(f) and not _excluded(os.path.relpath(f, root))})
    return keep(md), keep(yaml_files)


# --- Markdown 파싱 ------------------------------------------------------------

class Item:
    def __init__(self, kind, line_no):
        self.kind = kind
        self.ordered = False  # 번호 목록 항목인지 — R4 고정 시퀀스 판정에 쓴다
        self.line_no = line_no
        self.lines = []
        self.extra = []       # 들여쓴 하위 불릿 = 인접 설명

    @property
    def text(self):
        return " ".join(l.strip() for l in self.lines).strip()

    @property
    def context(self):
        return " ".join(l.strip() for l in self.lines + self.extra).strip()


class Heading:
    def __init__(self, level, title, start):
        self.level = level
        self.title = title
        self.start = start        # heading 행 인덱스 (루트는 -1)
        self.end = start + 1      # subtree 끝 (exclusive)
        self.body_end = start + 1  # 첫 자식 heading 이전 (preamble 끝)
        self.children = []
        self.parent = None
        self.items = []

    @property
    def path(self):
        names, node = [], self
        while node is not None and node.parent is not None:
            names.append(node.title)
            node = node.parent
        return " > ".join(reversed(names))


def strip_frontmatter_and_fences(lines):
    """스캔 대상 라인만 남긴 복사본 — 제거 대상은 빈 문자열로 치환해 행 번호를 보존한다."""
    out = list(lines)
    i = 0
    if out and out[0].strip() == "---":
        for j in range(1, len(out)):
            if out[j].strip() == "---":
                for k in range(0, j + 1):
                    out[k] = ""
                i = j + 1
                break
    fence = None
    while i < len(out):
        m = FENCE_RE.match(out[i])
        if fence is None:
            if m:
                fence = m.group(1)
                out[i] = ""
        else:
            if m and out[i].strip().startswith(fence):
                fence = None
            out[i] = ""
        i += 1
    return out


def split_items(lines, offset):
    """heading body 를 item(list item / 문단 / 표 데이터 행) 단위로 분해한다."""
    items = []
    cur_para = None
    cur_list = None
    prev_blank = True
    i = 0

    def flush_para():
        nonlocal cur_para
        if cur_para is not None:
            items.append(cur_para)
            cur_para = None

    def flush_list():
        nonlocal cur_list
        if cur_list is not None:
            items.append(cur_list)
            cur_list = None

    while i < len(lines):
        line = lines[i]
        no = offset + i + 1
        if not line.strip():
            flush_para()
            prev_blank = True
            i += 1
            continue
        if line.lstrip().startswith("|"):
            flush_para()
            flush_list()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append((offset + i + 1, lines[i]))
                i += 1
            for idx, (row_no, row) in enumerate(rows):
                if idx == 0 or TABLE_SEP_RE.match(row):
                    continue
                it = Item("table", row_no)
                it.lines.append(row)
                items.append(it)
            prev_blank = False
            continue
        m = LIST_RE.match(line)
        if m:
            flush_para()
            indent = len(m.group(1).expandtabs(4))
            if indent == 0 or cur_list is None:
                flush_list()
                cur_list = Item("list", no)
                cur_list.ordered = m.group(2)[0].isdigit()
                cur_list.lines.append(m.group(3))
            else:
                cur_list.extra.append(m.group(3))
        elif cur_list is not None and not prev_blank:
            cur_list.lines.append(line)
        elif cur_list is not None and line[:1].isspace():
            cur_list.extra.append(line)
        else:
            flush_list()
            if cur_para is None:
                cur_para = Item("para", no)
            cur_para.lines.append(line)
        prev_blank = False
        i += 1
    flush_para()
    flush_list()
    return items


def parse_markdown(text):
    """(라인 목록, 루트 Heading, 전체 노드) — 루트는 문서 선두 preamble 을 items 로 갖는다."""
    raw = text.split("\n")
    lines = strip_frontmatter_and_fences(raw)
    root = Heading(0, "", -1)
    nodes, stack = [], [root]
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if not m:
            continue
        node = Heading(len(m.group(1)), m.group(2).strip(), i)
        while stack and stack[-1].level >= node.level:
            stack.pop()
        parent = stack[-1] if stack else root
        node.parent = parent
        parent.children.append(node)
        nodes.append(node)
        stack.append(node)

    ordered = [root] + nodes
    for node in ordered:
        if node is root:
            node.end = len(lines)
        else:
            node.end = len(lines)
            for other in nodes:
                if other.start > node.start and other.level <= node.level:
                    node.end = other.start
                    break
        node.body_end = node.children[0].start if node.children else node.end
        body_start = node.start + 1
        node.items = split_items(lines[body_start:node.body_end], body_start)
    return lines, root, ordered


def preamble_text(node, lines):
    return "\n".join(lines[node.start + 1:node.body_end])


def ancestor_preamble(node, lines):
    chunks, cur = [], node.parent
    while cur is not None:
        chunks.append(preamble_text(cur, lines))
        cur = cur.parent
    return "\n".join(chunks)


def subtree_text(node, lines):
    return "\n".join(lines[max(node.start, 0):node.end])


def no_code(text):
    return INLINE_CODE.sub(" ", text)


# --- 발견 --------------------------------------------------------------------

def normalize(text):
    text = re.sub(r"[*_`]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def fingerprint(rule, relpath, heading, normalized):
    return hashlib.sha1(f"{rule}|{relpath}|{heading}|{normalized}".encode()).hexdigest()[:16]


def finding(rule, relpath, line, heading, excerpt, normalized=""):
    return {
        "rule": rule,
        "name": RULES[rule][0],
        "severity": RULES[rule][1],
        "path": relpath,
        "line": line,
        "heading": heading,
        "excerpt": excerpt[:80],
        "fp": fingerprint(rule, relpath, heading, normalized),
    }


def _longest_ordered_run(items):
    """연속한 번호 목록 항목의 최대 길이 — 문단·불릿으로 끊긴 목록은 합산하지 않는다 (한 절의 흩어진 번호는 시퀀스가 아니다)."""
    best = run = 0
    for it in items:
        if it.kind == "list" and it.ordered:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def scan_markdown_rules(relpath, lines, root, nodes):
    found = []
    for node in nodes:
        heading = node.path
        anc = ancestor_preamble(node, lines)
        anc_reasoned = bool(ANCESTOR_REASON_CUE.search(anc))
        # 같은 절의 설명 문단과 절 제목은 그 절 규칙들의 '왜'다 — 형제 규칙 항목(list·table)은 아니다
        own_prose = ((node.title or '') + ' ' + ' '.join(' '.join(it.lines) for it in node.items if it.kind == 'para'))
        own_reasoned = bool(LOCAL_REASON_CUE.search(own_prose))
        for item in node.items:
            text, ctx = item.text, item.context
            if not text:
                continue
            norm = normalize(text)
            # R1a — 하드룰인데 근거 단서가 없다
            rule_text = LABEL_USE.sub("", text)
            if HARD_TOKEN.search(rule_text) and not EXAMPLE_ITEM.search(ctx) \
                    and not INTRO_LABEL.search(text.strip()) and not BOLD_LABEL_LINE.match(text.strip()):
                if not (LOCAL_REASON_CUE.search(ctx) or own_reasoned or anc_reasoned):
                    found.append(finding("R1a", relpath, item.line_no, heading, text, norm))
            bare = no_code(text)
            negated = NEGATED.search(ctx)
            # R2 — 모델 내장 행동 재지시
            if not negated and MODEL_OVERLAP.search(bare):
                found.append(finding("R2", relpath, item.line_no, heading, text, norm))
            # R3 — 강조 인플레이션
            if not negated:
                hit = any(p.search(bare) for p in EMPHASIS) or len(re.findall("반드시", bare)) >= 2
                if hit:
                    found.append(finding("R3", relpath, item.line_no, heading, text, norm))

    # R4 — 고정 시퀀스에 이탈 여지가 없다
    root_pre = preamble_text(root, lines)
    groups = {}
    for node in nodes:
        if STEP_HEADING.search(node.title):
            owner = node.parent if node.parent is not None else root
            groups.setdefault(id(owner), owner)
        elif relpath.startswith(R4_PROCEDURE_SCOPE) and _longest_ordered_run(node.items) >= 4:
            groups.setdefault(id(node), node)
    for owner in groups.values():
        scope = subtree_text(owner, lines) + "\n" + ancestor_preamble(owner, lines) + "\n" + root_pre
        if not FLEX_CUE.search(scope):
            found.append(finding("R4", relpath, max(owner.start + 1, 1), owner.path,
                                 owner.title or relpath))
    return found


def scan_size(relpath, text):
    limit = LIMITS["default"]
    for prefix, value in LIMITS.items():
        if prefix != "default" and relpath.startswith(prefix):
            limit = value
            break
    tokens = approx_tokens(text)
    if tokens > limit:
        return [finding("R5", relpath, 1, "", f"≈{tokens}tok > 한도 {limit}tok ({len(text.encode())}바이트)")]
    return []


def scan_yaml(relpath, text):
    lines = text.split("\n")
    has_service = any(re.match(r"^service_id\s*:", l) for l in lines)
    has_verify = any(re.match(r"^verification\s*:", l) for l in lines)
    if has_service and not has_verify:
        return [finding("R6", relpath, 1, "", "service_id 가 있으나 최상위 verification: 없음")]
    return []


# --- R7 canonical ↔ generated -------------------------------------------------

def collect_blocks(lines, open_re, close_re):
    """(완결 블록 [(name, attr, body_start, body_end)], 미완결 [(name, line_no)])."""
    blocks, unclosed, i = [], [], 0
    while i < len(lines):
        m = open_re.match(lines[i].strip())
        if not m:
            i += 1
            continue
        name = m.group(1)
        attr = m.group(2) if (m.lastindex or 0) >= 2 else None
        body_start = i + 1
        j = body_start
        while j < len(lines):
            c = close_re.match(lines[j].strip())
            if c and c.group(1) == name:
                break
            j += 1
        if j < len(lines):
            blocks.append((name, attr, body_start, j))
            i = j + 1
        else:
            unclosed.append((name, i + 1))
            i = body_start
    return blocks, unclosed


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def rel_of(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def canonical_index(root, md_files):
    """((rel, name) -> 본문, [(rel, name, [target...])], [미완결 finding])."""
    index, declared, broken = {}, [], []
    owners = {}       # name -> [rel...] — 같은 이름의 canonical 이 둘이면 어느 쪽이 원본인지 정할 수 없다
    for path in md_files:
        rel = rel_of(root, path)
        lines = read_text(path).split("\n")
        blocks, unclosed = collect_blocks(lines, CANONICAL_OPEN, CANONICAL_CLOSE)
        for name, targets, s, e in blocks:
            index[(rel, name)] = "\n".join(lines[s:e])
            owners.setdefault(name, []).append((rel, s))
            if targets:
                declared.append((rel, name, [t.strip() for t in targets.split(",") if t.strip()]))
        for name, line in unclosed:
            broken.append(finding("R7", rel, line, "", f"canonical:{name} 닫기 마커 없음"))
    for name, rels in owners.items():
        if len(rels) > 1:
            for rel, s in rels:
                broken.append(finding("R7", rel, s, "",
                                      f"canonical:{name} 이 {len(rels)}개 파일에 중복 — 원본은 하나여야 한다"))
    return index, declared, broken


def scan_generated(root, md_files, canon_info):
    canon, declared, found = canon_info[0], canon_info[1], list(canon_info[2])
    opens = {}        # (rel, name) -> 열기 마커 수 (미완결 포함)
    by_src = {}       # (rel, name, source) -> 완결 블록 수 — targets 검사는 선언한 canonical 을 가리키는 블록만 인정
    dup_reported = set()
    unclosed_reported = set()   # 닫기 누락은 그 자체로 1건 — targets 카운트로 중복 보고하지 않는다
    for path in md_files:
        rel = rel_of(root, path)
        lines = read_text(path).split("\n")
        blocks, unclosed = collect_blocks(lines, GENERATED_OPEN, GENERATED_CLOSE)
        for name, _src, _s, _e in blocks:
            opens[(rel, name)] = opens.get((rel, name), 0) + 1
            key = (rel, name, (_src or "").replace(os.sep, "/"))
            by_src[key] = by_src.get(key, 0) + 1
        for name, line in unclosed:
            opens[(rel, name)] = opens.get((rel, name), 0) + 1
            unclosed_reported.add((rel, name))
            found.append(finding("R7", rel, line, "", f"generated:{name} 닫기 마커 없음"))
        seen = set()
        for name, source, s, e in blocks:
            if opens[(rel, name)] > 1:
                if (rel, name) not in dup_reported:
                    dup_reported.add((rel, name))
                    found.append(finding("R7", rel, s, "",
                                         f"generated:{name} 블록이 한 파일에 {opens[(rel, name)]}개"))
                continue
            if name in seen:
                continue
            seen.add(name)
            src = (source or "").replace(os.sep, "/")
            if (src, name) not in canon:
                found.append(finding("R7", rel, s, "", f"source={src} 에 canonical:{name} 블록 없음"))
                continue
            if "\n".join(lines[s:e]).encode() != canon[(src, name)].encode():
                found.append(finding("R7", rel, s, "",
                                     f"generated:{name} 본문이 {src} canonical 과 다름"))
    # canonical 이 targets 를 선언했으면 각 target 에 그 블록이 정확히 1개 있어야 한다
    for rel_c, name, targets in declared:
        for target in targets:
            if (target, name) in dup_reported or (target, name) in unclosed_reported:
                continue
            n = by_src.get((target, name, rel_c), 0)
            if n != 1:
                other = opens.get((target, name), 0) - n
                hint = f", 다른 source 를 가리키는 블록 {other}개" if other > 0 else ""
                found.append(finding("R7", rel_c, 1, "",
                                     f"targets={target} 에 source={rel_c} 인 generated:{name} 블록이 {n}개 (1개여야 한다){hint}"))
    return found


def sync_generated(root, md_files, canon_info):
    canon = canon_info[0]
    changed = []
    for path in md_files:
        rel = rel_of(root, path)
        lines = read_text(path).split("\n")
        blocks, _unclosed = collect_blocks(lines, GENERATED_OPEN, GENERATED_CLOSE)
        dirty = False
        for name, source, s, e in reversed(blocks):
            src = (source or "").replace(os.sep, "/")
            if (src, name) not in canon:
                continue
            want = canon[(src, name)].split("\n")
            if lines[s:e] != want:
                lines[s:e] = want
                dirty = True
        if dirty:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            changed.append(rel)
    return changed


# --- 스캔 오케스트레이션 ---------------------------------------------------------

def reasoned_headings(root, md_files):
    """subtree 에 하드룰과 `근거:` 가 함께 있는 heading — R1b 회귀 기준점."""
    out = {}
    for path in md_files:
        rel = rel_of(root, path)
        lines, _r, nodes = parse_markdown(read_text(path))
        for node in nodes:
            if node.parent is None:
                continue
            body = subtree_text(node, lines)
            if HARD_TOKEN.search(body) and "근거:" in body:
                out[f"{rel}::{node.path}"] = True
    return out


def scan_r1b(root, md_files, baseline):
    keys = (baseline or {}).get("reasoned_headings", {})
    if not keys:
        return []
    found, cache = [], {}
    for key in sorted(keys):
        rel, _, heading = key.partition("::")
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        if rel not in cache:
            lines, _r, nodes = parse_markdown(read_text(path))
            cache[rel] = (lines, nodes)
        lines, nodes = cache[rel]
        for node in nodes:
            if node.parent is not None and node.path == heading:
                body = subtree_text(node, lines)
                if HARD_TOKEN.search(body) and "근거:" not in body:
                    found.append(finding("R1b", rel, node.start + 1, heading,
                                         "`근거:` 표기가 사라졌다 (베이스라인 회귀)"))
                break
    return found


def scan(root, md_files, yaml_files, baseline=None):
    found = []
    for path in md_files:
        rel = rel_of(root, path)
        lines, node_root, nodes = parse_markdown(read_text(path))
        found += scan_markdown_rules(rel, lines, node_root, nodes)
        found += scan_size(rel, read_text(path))
    for path in yaml_files:
        rel = rel_of(root, path)
        found += scan_size(rel, read_text(path))
        found += scan_yaml(rel, read_text(path))
    found += scan_generated(root, md_files, canonical_index(root, md_files))
    found += scan_r1b(root, md_files, baseline)
    found.sort(key=lambda f: (RULE_ORDER.index(f["rule"]), f["path"], f["line"]))
    return found


def counts(found):
    out = {r: 0 for r in RULE_ORDER}
    for f in found:
        out[f["rule"]] += 1
    return out


def aggregate(found):
    """fingerprint -> 엔트리(count 포함). 같은 heading 안 동일 문장 반복도 세어야 ratchet 이 샌다."""
    agg = {}
    for f in found:
        entry = agg.get(f["fp"])
        if entry is None:
            agg[f["fp"]] = {"rule": f["rule"], "severity": f["severity"], "path": f["path"],
                            "line": f["line"], "heading": f["heading"],
                            "excerpt": f["excerpt"], "count": 1}
        else:
            entry["count"] += 1
    return agg


# --- 베이스라인 ----------------------------------------------------------------

def load_baseline(path):
    """(데이터, 오류 메시지). 스키마·matcher 가 코드와 다르면 오류를 돌려준다."""
    if not os.path.isfile(path):
        return None, None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    got = (data.get("schema_version"), data.get("matcher_version"))
    if got != (SCHEMA_VERSION, MATCHER_VERSION):
        return data, (f"베이스라인 스키마/matcher 불일치 — 파일 {got[0]}/{got[1]}, "
                      f"코드 {SCHEMA_VERSION}/{MATCHER_VERSION}")
    return data, None


def save_baseline(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True, ensure_ascii=False, indent=2)
        fh.write("\n")


def excess_block(found, baseline):
    """[(fp, 엔트리, 베이스라인 count)] — block 규칙에서 건수가 늘어난 것만."""
    base = (baseline or {}).get("findings", {})
    out = []
    for fp, entry in aggregate(found).items():
        if entry["rule"] not in BASELINED or entry["severity"] != "block":
            continue
        prev = base.get(fp, {}).get("count", 0)
        if entry["count"] > prev:
            out.append((fp, entry, prev))
    return sorted(out, key=lambda t: (t[1]["path"], t[1]["line"]))


def next_acceptance_id(baseline, today):
    used = set((baseline or {}).get("acceptance_batches", {}))
    n = 1
    while f"{today}-{n}" in used:
        n += 1
    return f"{today}-{n}"


# --- 출력 ---------------------------------------------------------------------

def render(f):
    head = f["heading"] or "(문서 루트)"
    return f"  [{f['rule']}] {f['path']}:{f['line']}  {head}  {f['excerpt']}"


def render_excess(entry, prev):
    head = entry["heading"] or "(문서 루트)"
    return (f"  [{entry['rule']}] {entry['path']}:{entry['line']}  {head}  {entry['excerpt']}"
            f"  ({prev}→{entry['count']}건)")


def print_summary(found, baseline):
    cur = counts(found)
    old = (baseline or {}).get("summary", {})
    print("규칙별 요약")
    for rule in RULE_ORDER:
        name, sev = RULES[rule]
        line = f"  {rule:<4} {name:<28} {sev:<5} {cur[rule]}"
        if rule in old:
            delta = cur[rule] - old[rule]
            line += f"  (베이스라인 {old[rule]} → {cur[rule]}, {delta:+d})" if delta else "  (동일)"
        print(line)


def trend_line(found, baseline):
    cur, old = counts(found), (baseline or {}).get("summary", {})
    parts = [f"{r} {old[r]} → {cur[r]} ({cur[r] - old[r]:+d})"
             for r in RULE_ORDER if r in old and old[r] != cur[r]]
    return ", ".join(parts) if parts else "베이스라인 대비 변동 없음"


# --- 명령 ---------------------------------------------------------------------

def cmd_check(found, baseline, baseline_path):
    if baseline is None:
        print(f"베이스라인 없음 ({baseline_path})")
        print('  python3 tools/lint_harness_rules.py --update-baseline --accept-new "<사유>" 로 생성하라')
        print("lint_harness_rules: FAIL — 베이스라인 없음")
        return 1
    news = excess_block(found, baseline)
    regressions = [f for f in found if f["rule"] in ("R1b", "R7")]
    if news or regressions:
        if news:
            print(f"신규·증가 위반 {len(news)}건 — 베이스라인보다 늘어난 block 규칙 발견")
            for _fp, entry, prev in news:
                print(render_excess(entry, prev))
        if regressions:
            print(f"회귀·드리프트 {len(regressions)}건")
            for f in regressions:
                print(render(f))
        print(f"lint_harness_rules: FAIL — 신규 {len(news)}건, 회귀 {len(regressions)}건")
        return 1
    print(f"추이: {trend_line(found, baseline)}")
    print(f"lint_harness_rules: OK — 신규 위반 0, 회귀 0 (누적 {len(found)}건 유예 중)")
    return 0


def cmd_update_baseline(root, md_files, found, baseline, baseline_path, accept_new):
    if baseline is None and not accept_new:
        print(f"베이스라인이 없다 ({baseline_path}) — 초기 생성에는 --accept-new \"<사유>\" 가 필요하다")
        print("lint_harness_rules: FAIL — 초기 베이스라인 사유 없음")
        return 1
    news = excess_block(found, baseline)
    if news and not accept_new:
        print(f"신규·증가 block 위반 {len(news)}건 — 고치거나 --accept-new \"<사유>\" 로 사유를 남겨라")
        for _fp, entry, prev in news:
            print(render_excess(entry, prev))
        print(f"lint_harness_rules: FAIL — 신규 {len(news)}건 미승인")
        return 1

    today = datetime.date.today().isoformat()
    old_findings = (baseline or {}).get("findings", {})
    batches = dict((baseline or {}).get("acceptance_batches", {}))
    batch_id = None
    keep = {}
    for fp, entry in sorted(aggregate(found).items()):
        if entry["rule"] not in BASELINED:
            continue
        prev = old_findings.get(fp)
        if prev and entry["count"] <= prev.get("count", 0):
            acceptance_id = prev.get("acceptance_id", f"{prev.get('accepted', today)}-1")
        else:
            if batch_id is None:
                batch_id = next_acceptance_id(baseline, today)
                batches[batch_id] = {"accepted": today,
                                     "reason": accept_new or "베이스라인 갱신 (자동 하향·warn 편입)"}
            acceptance_id = batch_id
        keep[fp] = {"rule": entry["rule"], "path": entry["path"], "heading": entry["heading"],
                    "excerpt": entry["excerpt"], "count": entry["count"],
                    "acceptance_id": acceptance_id}
    batches = {bid: meta for bid, meta in batches.items()
               if any(v["acceptance_id"] == bid for v in keep.values())}
    removed = sum(1 for fp in old_findings if fp not in keep)
    save_baseline(baseline_path, {
        "schema_version": SCHEMA_VERSION,
        "matcher_version": MATCHER_VERSION,
        "updated": today,
        "summary": {r: counts(found)[r] for r in RULE_ORDER if r != "R7"},
        "reasoned_headings": reasoned_headings(root, md_files),
        "acceptance_batches": batches,
        "findings": keep,
    })
    print(f"베이스라인 갱신: {baseline_path}")
    print(f"  유예 {len(keep)}건 (신규·증가 승인 {len(news)}건, 해결 하향 {removed}건)")
    print(f"lint_harness_rules: OK — 베이스라인 {len(keep)}건")
    return 0


def main():
    ap = argparse.ArgumentParser(description="하네스 지시문 표기 규약 린트 (ratchet)")
    ap.add_argument("paths", nargs="*", help="대상 경로 (생략 시 하네스 기본 대상)")
    ap.add_argument("--baseline", help=f"베이스라인 경로 (기본 {BASELINE_REL})")
    ap.add_argument("--summary", action="store_true", help="규칙별 카운트만 출력")
    ap.add_argument("--json", action="store_true", help="발견 목록 JSON 출력")
    ap.add_argument("--check", action="store_true", help="신규 위반·회귀만 판정, 있으면 exit 1")
    ap.add_argument("--update-baseline", action="store_true", help="베이스라인 갱신 (해결분 자동 하향)")
    ap.add_argument("--accept-new", metavar="사유", help="신규·증가 block 위반을 사유와 함께 편입")
    ap.add_argument("--sync-generated", action="store_true", help="generated 블록을 canonical 본문으로 갱신")
    args = ap.parse_args()

    root = REPO
    if args.paths:
        dirs = [p if os.path.isdir(p) else os.path.dirname(p) or "."
                for p in (os.path.abspath(x) for x in args.paths)]
        root = os.path.commonpath(dirs) if dirs else REPO
    baseline_path = args.baseline or os.path.join(root, BASELINE_REL)
    md_files, yaml_files = collect_targets(root, args.paths)

    if args.sync_generated:
        changed = sync_generated(root, md_files, canonical_index(root, md_files))
        for rel in changed:
            print(f"  갱신: {rel}")
        print(f"lint_harness_rules: OK — {'변경 없음' if not changed else f'{len(changed)}개 파일 갱신'}")
        return 0

    baseline, berr = load_baseline(baseline_path)
    if berr:
        if args.check or (args.update_baseline and not args.accept_new):
            print(berr)
            print('  python3 tools/lint_harness_rules.py --update-baseline --accept-new "<사유>" 로 재생성하라')
            print("lint_harness_rules: FAIL — 베이스라인 재생성 필요")
            return 1
        baseline = None
    found = scan(root, md_files, yaml_files, baseline)

    if args.check:
        return cmd_check(found, baseline, baseline_path)
    if args.update_baseline:
        return cmd_update_baseline(root, md_files, found, baseline, baseline_path, args.accept_new)
    if args.json:
        print(json.dumps(found, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.summary:
        print_summary(found, baseline)
        if baseline is not None:
            print(f"추이: {trend_line(found, baseline)}")
        print(f"lint_harness_rules: OK — {len(md_files)}개 문서, {len(yaml_files)}개 카탈로그, 발견 {len(found)}건")
        return 0

    for rule in RULE_ORDER:
        hits = [f for f in found if f["rule"] == rule]
        if not hits:
            continue
        print(f"[{rule}] {RULES[rule][0]} — {len(hits)}건")
        for f in hits:
            print(render(f))
        print()
    print_summary(found, baseline)
    print(f"lint_harness_rules: OK — {len(md_files)}개 문서, {len(yaml_files)}개 카탈로그, 발견 {len(found)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
