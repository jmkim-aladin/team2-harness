#!/usr/bin/env python3
"""완화 신호 스캔 — diff에서 검증 기준을 낮추는 변경을 찾아 리뷰 미리보기용 markdown으로 낸다.

빨간 검사를 만나면 사람도 에이전트도 가장 싼 초록 경로(임계값 하향·테스트 skip·체커 침묵)를 고른다.
기준 강화는 조용히, 완화는 드러낸다 — `/ad:code-review` 1단계 사전 스캔이 부른다.
판정이 아니라 신호다: 사유가 있으면 리뷰어가 넘긴다.

범주:
  임계값 하향  검사 설정 파일의 커버리지·예산·경고 수치가 느슨해짐, lint 심각도 하향(ESLint 숫자 2→1/0 포함),
               경고→오류 해제(TreatWarningsAsErrors 등)·실패 무시 켜기(continue-on-error 등), 검사 설정 파일 삭제
  테스트 약화  @Disabled·@Ignore·[Ignore]·[Explicit]·[Fact(Skip=)]·TestNG enabled=false·.skip·xit·.only·-x test,
               테스트 파일 삭제,
               남은 테스트 파일의 assert/verify 줄 순감
  체커 침묵    @Suppress·ktlint-disable·#pragma warning disable·eslint-disable·@ts-ignore·nosemgrep·gitleaks:allow 등
  미완성       TODO(·NotImplementedError·NotImplementedException·빈 catch/except
  예외 추가    baseline·allowlist·suppression·*ignore 파일에 추가된 항목

사용법:
    python3 tools/gate_loosening_scan.py origin/develop...HEAD             # 현재 repo git diff (... = merge-base 기준)
    python3 tools/gate_loosening_scan.py main..feature/x -C ~/work/svc      # 다른 repo
    python3 tools/gate_loosening_scan.py --diff /path/pr123.diff            # 저장해 둔 PR diff
    gh pr diff 123 --repo o/r | python3 tools/gate_loosening_scan.py        # stdin

종료 코드: 0 스캔 완료(발견 유무 무관) / 2 입력 오류(빈 diff·git 실패·diff 형식 아님).
발견을 exit 코드로 막지 않는다 — 게이트가 아니라 리뷰어에게 보이는 신호다.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

CATEGORIES = [
    ("threshold", "임계값 하향"),
    ("test", "테스트 약화"),
    ("silence", "체커 침묵"),
    ("unfinished", "미완성"),
    ("exception", "예외 추가"),
]

# --- 파일 분류 -----------------------------------------------------------------

DOC_EXT = (".md", ".markdown", ".txt", ".rst", ".adoc")
SOURCE_EXT = (".kt", ".kts", ".java", ".cs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".scala", ".groovy")

# 파일명 접미(*Test.kt)는 대문자 IT/Test만 — 대소문자 무시면 Unit.kt·Submit.kt가 테스트로 잡힌다
TEST_PATH = re.compile(
    r"(^|/)(src/(test|integrationTest|testFixtures|androidTest)|[Tt]ests?|__tests__|[Ss]pecs?)/"
    r"|(^|/)[^/]*(Tests?|IT)\.(kt|kts|java|cs|scala|groovy)$"
    r"|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|(^|/)test_[^/]*\.py$|_test\.(py|go)$"
    r"|(^|/)[^/]*\.(Tests?|UnitTests|IntegrationTests)/"
)

# 임계값 하향은 '검사를 설정하는 파일'에서만 본다 — application.yml의 풀 크기·타임아웃은 게이트가 아니다
GATE_CONFIG = re.compile(
    r"(^|/)("
    r"build\.gradle(\.kts)?|settings\.gradle(\.kts)?|gradle\.properties|pom\.xml"
    r"|[^/]*\.(csproj|props|targets|ruleset|globalconfig)|\.editorconfig"
    r"|[^/]*detekt[^/]*\.ya?ml|\.?ktlint[^/]*|lint\.xml"
    r"|\.eslintrc[^/]*|eslint\.config\.[cm]?[jt]s|\.stylelintrc[^/]*|tsconfig[^/]*\.json"
    r"|(jest|vitest|karma|playwright)\.conf(ig)?\.[cm]?[jt]s|\.nycrc[^/]*|\.c8rc[^/]*|\.?codecov\.ya?ml|\.coveragerc"
    r"|sonar-project\.properties|lighthouserc[^/]*|budgets?[^/]*\.json|angular\.json|package\.json"
    r"|pyproject\.toml|setup\.cfg|tox\.ini|pytest\.ini|\.flake8|mypy\.ini|ruff\.toml|\.?semgrep[^/]*\.ya?ml"
    r"|Jenkinsfile|\.gitlab-ci\.ya?ml|azure-pipelines[^/]*\.ya?ml|buildspec[^/]*\.ya?ml|k6[^/]*\.[jt]s"
    r"|[^/]*(jacoco|kover)[^/]*\.(gradle(\.kts)?|ya?ml|xml|properties)"
    r")$"
    r"|(^|/)\.github/workflows/[^/]+\.ya?ml$"
)
# 통째로 지우면 그 검사가 사라지는 파일 — 수치 비교 없이 삭제 자체가 신호다.
# build.gradle·package.json 삭제는 모듈 제거일 때가 많아 넣지 않는다
CHECK_CONFIG = re.compile(
    r"(^|/)("
    r"\.editorconfig|[^/]*detekt[^/]*\.ya?ml|\.?ktlint[^/]*|lint\.xml|[^/]*\.(ruleset|globalconfig)"
    r"|\.eslintrc[^/]*|eslint\.config\.[cm]?[jt]s|\.stylelintrc[^/]*"
    r"|(jest|vitest|karma)\.conf(ig)?\.[cm]?[jt]s|\.nycrc[^/]*|\.c8rc[^/]*|\.?codecov\.ya?ml|\.coveragerc"
    r"|[^/]*(jacoco|kover)[^/]*\.(gradle(\.kts)?|ya?ml|xml|properties)"
    r"|Jenkinsfile|\.gitlab-ci\.ya?ml|azure-pipelines[^/]*\.ya?ml|buildspec[^/]*\.ya?ml"
    r")$"
    r"|(^|/)\.github/workflows/[^/]+\.ya?ml$"
)
# ESLint 규칙 값 자리('no-console': 2 / [2, {...}])의 숫자는 심각도다 — 2=error·1=warn·0=off
ESLINT_FILE = re.compile(r"(^|/)(\.eslintrc[^/]*|eslint\.config\.[cm]?[jt]s)$")
ESLINT_SEVERITY_SLOT = re.compile(r":\s*\[?\s*$")
# jest coverageThreshold의 branches/lines… 처럼 키 이름만으로는 방향이 안 보이는 커버리지 설정
COVERAGE_FILE = re.compile(r"(^|/)((jest|vitest|karma)\.conf(ig)?\.[cm]?[jt]s|\.nycrc[^/]*|\.c8rc[^/]*|\.?codecov\.ya?ml|\.coveragerc|package\.json)$")

EXCEPTION_FILE = re.compile(
    r"(?i)(^|/)("
    r"[^/]*(baseline|allowlist|whitelist|suppressions?|exclusions?)[^/]*"
    r"|\.gitleaksignore|\.semgrepignore|\.eslintignore|\.stylelintignore|\.trivyignore|\.snyk|\.secrets\.baseline"
    r")$"
)


def is_doc(path: str) -> bool:
    return path.lower().endswith(DOC_EXT)


def is_test(path: str) -> bool:
    return bool(TEST_PATH.search(path))


def is_gate_config(path: str) -> bool:
    return bool(GATE_CONFIG.search(path))


def is_check_config(path: str) -> bool:
    return bool(CHECK_CONFIG.search(path))


def is_exception_file(path: str) -> bool:
    if path.endswith("GlobalSuppressions.cs"):
        return True
    # BaselineCalculator.kt 같은 도메인 소스는 예외 목록이 아니다
    return bool(EXCEPTION_FILE.search(path)) and not path.lower().endswith(SOURCE_EXT)


# --- 줄 패턴 -------------------------------------------------------------------

# FQN(@org.junit.jupiter.api.Disabled)도 잡는다. @DisabledOnOs 같은 조건부는 \b에서 빠진다
TEST_SKIP = re.compile(
    r"@(?:[\w.]+\.)?(?:Disabled|Ignore)\b|\[\s*(?:[\w.]+(?:\([^)]*\))?\s*,\s*)*(?:Ignore|Explicit)\b"
    r"|@(?:[\w.]+\.)?Test\s*\([^)]*\benabled\s*=\s*false"
    r"|\[\s*(?:Fact|Theory|Test|TestCase|TestMethod)\s*\([^)]*\bSkip\s*="
    r"|\b(?:it|describe|test|context|suite)\.(?:skip|only|todo)\b"
    r"|(?<![.\w])(?:xit|xdescribe|xtest|xcontext|fit|fdescribe|xshould|xgiven|xwhen|xthen)\s*\("
    r"|@pytest\.mark\.(?:skip|xfail)|@unittest\.skip|\bpytest\.skip\("
    r"|\.config\([^)]*\benabled\s*=\s*false"
    r"|-DskipTests\b|-Dmaven\.test\.skip=true|\s-x\s+:?[\w:-]*[Tt]est\b"
)
ASSERTION = re.compile(
    r"\bassert\w*(?:\s*<[^>]*>)?\s*[(\s!{]|\bassert\.\w+\s*\(|\bexpect\s*\(|\bverify\s*[({]|\bcoVerify\s*\{"
    r"|\bconfirmVerified\s*\("
    r"|\bshould(?:Be|NotBe|Throw|Contain|Have|Equal|Match|Exist|Not)\w*|\.Should\(\)|\.Verify\("
    r"|\bAssert\.\w+\s*(?:<[^>]*>)?\s*\("   # 제네릭 Assert.Throws<Foo>( 포함
    r"|\bAssertions\.\w+|\bself\.assert\w*\s*\("
)
# 테스트 함수 선언(fun shouldReturnX())은 assert가 아니다
DECLARATION = re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:fun|def|void|public|private|protected|internal|override|async)\b")
COMMENT_ONLY = re.compile(r"^\s*(?://|#|/\*|\*|<!--|--)")

SILENCE = re.compile(
    r"@(?:file:|get:|set:|field:|param:)?Suppress(?:Warnings|Lint)?\s*\(|ktlint-disable|ktlint:disable"
    r"|#pragma\s+warning\s+disable|\[(?:assembly:\s*|module:\s*)?SuppressMessage\s*\(|ReSharper\s+disable|<NoWarn>"
    r"|eslint-disable|stylelint-disable|@ts-ignore|@ts-nocheck|@ts-expect-error|tslint:disable"
    r"|nosemgrep|gitleaks:allow|NOSONAR|#\s*noqa\b|#\s*type:\s*ignore|pylint:\s*disable|//\s*nolint\b"
    r"|istanbul\s+ignore|c8\s+ignore|v8\s+ignore|Stryker\s+disable"
)

UNFINISHED = re.compile(r"\bTODO\s*\(|\bNotImplementedError\b|\bNotImplementedException\b")
EMPTY_CATCH_INLINE = re.compile(
    r"\bcatch\b\s*(?:\([^)]*\))?\s*\{\s*(?://.*|/\*.*?\*/)?\s*\}"
    r"|^\s*except\b[^:]*:\s*(?:pass|\.\.\.)\s*(?:#.*)?$"
    r"|\.catch\(\s*(?:\([^)]*\)|\w+)?\s*=>\s*(?:\{\s*\}|null|undefined)\s*\)"
)
CATCH_OPEN = re.compile(r"\bcatch\b\s*(?:\([^)]*\))?\s*\{\s*(?://.*)?$")
EXCEPT_OPEN = re.compile(r"^\s*except\b[^:]*:\s*(?:#.*)?$")
BLOCK_CLOSE = re.compile(r"^\s*\}")
PY_EMPTY_BODY = re.compile(r"^\s*(?:pass|\.\.\.)\s*(?:#.*)?$")
BLANK_OR_COMMENT = re.compile(r"^\s*(?://.*|/\*.*\*/|\*.*|#.*)?$")

# 임계값 비교 — 숫자는 식별자 일부(CA1062의 1062)가 아닐 때만
NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
SEVERITY_RANK = {"error": 3, "warning": 2, "warn": 2, "info": 1, "suggestion": 1, "hint": 1,
                 "off": 0, "none": 0, "silent": 0, "ignore": 0}
SEVERITY = re.compile(r"(?<![\w-])(error|warning|warn|info|suggestion|hint|off|none|silent|ignore)(?![\w-])", re.I)
BOOL = re.compile(r"(?<![\w-])(true|false|enable|disable)(?![\w-])", re.I)
# (키워드, 느슨해지는 방향) — 위에서부터 첫 일치. 커버리지류가 threshold보다 먼저다(coverageThreshold는 하한)
POLARITY = [
    ("failunder", "down"), ("minbound", "down"), ("minvalue", "down"), ("minscore", "down"), ("minimum", "down"),
    ("coverage", "down"), ("covered", "down"), ("warninglevel", "down"),
    ("maxissues", "up"), ("maxwarnings", "up"), ("maxerrors", "up"),
    ("maximumwarning", "up"), ("maximumerror", "up"), ("maxvalue", "up"), ("budget", "up"),
    ("threshold", "up"), ("tolerance", "up"), ("allowed", "up"),
]
COVERAGE_KEYS = ("branches", "lines", "functions", "statements", "target")
# true→false가 완화인 키 / false→true가 완화인 키 (compact 부분 일치)
STRICT_KEYS = ("warningsaserrors", "failonwarning", "failonviolation", "failonerror", "abortonerror",
               "werror", "strict", "noimplicit", "nullable")
STRICT_WORDS = ("active",)  # detekt 규칙 on/off — 부분 일치면 interactive·isActive까지 잡힌다
LENIENT_KEYS = ("ignorefailures", "continueonerror", "allowfailure", "skiptests", "testfailureignore",
                "ignoreerrors", "ignorewarnings", "maventestskip")
ON = {"true", "enable"}
OFF = {"false", "disable"}


# --- diff 파싱 -----------------------------------------------------------------

@dataclass
class Line:
    kind: str          # '+', '-', ' '
    old_no: int | None
    new_no: int | None
    text: str


@dataclass
class FileDiff:
    path: str = ""
    old_path: str = ""
    deleted: bool = False
    added_file: bool = False
    minus_seen: bool = False
    hunks: list[list[Line]] = field(default_factory=list)


@dataclass
class Hit:
    category: str
    path: str
    line: int | None   # None = 파일 단위
    text: str
    note: str = ""


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
GIT_HEADER = re.compile(r'^diff --git "?a/(.*?)"? "?b/(.*?)"?$')


def _strip_path(raw: str) -> str | None:
    p = raw.split("\t")[0].strip()
    if p.startswith('"') and p.endswith('"'):
        p = p[1:-1]
    if p == "/dev/null":
        return None
    return p[2:] if p[:2] in ("a/", "b/") else p


def parse_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    hunk: list[Line] = []
    old_left = new_left = old_no = new_no = 0
    # splitlines()는 \x0c·\x1c·\x85·\u2028 등에서도 끊어 hunk 줄 수가 어긋난다 — diff 줄 경계는 \n뿐이다
    for raw in text.split("\n"):
        if raw.endswith("\r"):
            raw = raw[:-1]
        if old_left > 0 or new_left > 0:   # hunk 본문 — '+++'로 시작하는 내용 줄도 헤더로 오인하지 않는다
            if raw.startswith("\\"):
                continue
            tag, body = raw[:1], raw[1:]
            if tag == "+":
                hunk.append(Line("+", None, new_no, body))
                new_no += 1
                new_left -= 1
            elif tag == "-":
                hunk.append(Line("-", old_no, None, body))
                old_no += 1
                old_left -= 1
            else:
                hunk.append(Line(" ", old_no, new_no, body))
                old_no += 1
                new_no += 1
                old_left -= 1
                new_left -= 1
            continue
        m = GIT_HEADER.match(raw)
        if m:
            cur = FileDiff(path=m.group(2), old_path=m.group(1))
            files.append(cur)
            continue
        if raw.startswith("--- "):
            if cur is None or cur.minus_seen:
                cur = FileDiff()
                files.append(cur)
            cur.minus_seen = True
            old = _strip_path(raw[4:])
            if old is None:
                cur.added_file = True
            else:
                cur.old_path = old
                cur.path = cur.path or old
            continue
        if cur is None:
            continue
        if raw.startswith("+++ "):
            new = _strip_path(raw[4:])
            if new is None:
                cur.deleted = True
                cur.path = cur.old_path or cur.path
            else:
                cur.path = new
        elif raw.startswith("deleted file mode"):
            cur.deleted = True
        elif raw.startswith("new file mode"):
            cur.added_file = True
        elif raw.startswith("rename to "):
            cur.path = raw[len("rename to "):]
        else:
            h = HUNK_RE.match(raw)
            if h:
                old_no, new_no = int(h.group(1)), int(h.group(3))
                old_left = int(h.group(2)) if h.group(2) is not None else 1
                new_left = int(h.group(4)) if h.group(4) is not None else 1
                hunk = []
                cur.hunks.append(hunk)
    return files


def change_blocks(hunk: list[Line]) -> list[tuple[list[Line], list[Line]]]:
    """연속한 -/+ 줄 묶음 — 수정 전후 짝을 같은 묶음 안에서만 찾는다."""
    blocks, removed, added = [], [], []
    for ln in hunk + [Line(" ", None, None, "")]:
        if ln.kind == "-":
            removed.append(ln)
        elif ln.kind == "+":
            added.append(ln)
        else:
            if removed or added:
                blocks.append((removed, added))
            removed, added = [], []
    return blocks


# --- 범주별 스캔 ---------------------------------------------------------------

def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", text)}


def _key(text: str) -> str:
    text = NUM.sub("#", text)
    text = SEVERITY.sub("<sev>", text)
    text = BOOL.sub("<bool>", text)
    return re.sub(r"\s+", " ", text).strip()


def _polarity(text: str, span_start: int, path: str) -> str | None:
    if (ESLINT_FILE.search(path) and ESLINT_SEVERITY_SLOT.search(text[:span_start])
            and NUM.match(text, span_start).group() in ("0", "1", "2")):
        return "down"
    compact = _compact(text)
    for word, direction in POLARITY:
        if word in compact:
            return direction
    if COVERAGE_FILE.search(path) and any(k in compact for k in COVERAGE_KEYS):
        return "down"
    if path.endswith((".xml", ".csproj", ".props", ".targets")):
        return None   # XML 태그의 '>'를 비교 연산자로 읽지 않는다
    before = text[:span_start].rstrip(" '\"")
    if before.endswith("<") or before.endswith("<="):
        return "up"     # k6 'p(95)<500' — 상한이 오르면 느슨
    if before.endswith(">") or before.endswith(">="):
        return "down"   # 'rate>0.99' — 하한이 내리면 느슨
    return None


def _threshold_change(old: str, new: str, path: str) -> str | None:
    old_nums, new_nums = list(NUM.finditer(old)), list(NUM.finditer(new))
    if len(old_nums) == len(new_nums):
        for o, n in zip(old_nums, new_nums):
            if o.group() == n.group():
                continue
            direction = _polarity(new, n.start(), path)
            ov, nv = float(o.group()), float(n.group())
            if (direction == "down" and nv < ov) or (direction == "up" and nv > ov):
                return f"{o.group()} → {n.group()}"
            break
    old_sev, new_sev = SEVERITY.findall(old), SEVERITY.findall(new)
    for o, n in zip(old_sev, new_sev):
        if o.lower() != n.lower():
            if SEVERITY_RANK[n.lower()] < SEVERITY_RANK[o.lower()]:
                return f"{o} → {n}"
            break
    old_b, new_b = BOOL.findall(old), BOOL.findall(new)
    compact, words = _compact(new), _words(new)
    for o, n in zip(old_b, new_b):
        o, n = o.lower(), n.lower()
        if o == n:
            continue
        strict = any(k in compact for k in STRICT_KEYS) or any(w in words for w in STRICT_WORDS)
        lenient = any(k in compact for k in LENIENT_KEYS)
        if (strict and o in ON and n in OFF) or (lenient and o in OFF and n in ON):
            return f"{o} → {n}"
        break
    return None


def _bool_value(text: str) -> str | None:
    found = BOOL.findall(text)
    return found[-1].lower() if found else None


def scan_threshold(fd: FileDiff) -> list[Hit]:
    hits = []
    for hunk in fd.hunks:
        for removed, added in change_blocks(hunk):
            paired: set[int] = set()
            for a in added:
                match = None
                for i, r in enumerate(removed):
                    if i in paired or r.text.strip() == a.text.strip():
                        continue
                    if _key(r.text) == _key(a.text):
                        match = i
                        break
                if match is not None:
                    paired.add(match)
                    note = _threshold_change(removed[match].text, a.text, fd.path)
                    if note:
                        hits.append(Hit("threshold", fd.path, a.new_no, a.text, note))
                    continue
                # 새로 추가된 '실패 무시' 스위치 (continue-on-error: true 등)
                if any(k in _compact(a.text) for k in LENIENT_KEYS) and _bool_value(a.text) in ON:
                    hits.append(Hit("threshold", fd.path, a.new_no, a.text, "실패 무시 추가"))
            for i, r in enumerate(removed):
                if i in paired:
                    continue
                # 통째로 지운 엄격 스위치 (allWarningsAsErrors = true 삭제 등)
                if any(k in _compact(r.text) for k in STRICT_KEYS) and _bool_value(r.text) in ON:
                    hits.append(Hit("threshold", fd.path, r.old_no, r.text, "엄격 설정 삭제"))
    return hits


def scan_test(fd: FileDiff) -> list[Hit]:
    if fd.deleted:
        return [Hit("test", fd.path, None, "", "테스트 파일 삭제")] if is_test(fd.path) else []
    hits = []
    removed_asserts: list[Line] = []
    added_asserts = 0
    for hunk in fd.hunks:
        for ln in hunk:
            if ln.kind == "+" and TEST_SKIP.search(ln.text):
                hits.append(Hit("test", fd.path, ln.new_no, ln.text))
            if is_test(fd.path) and ln.kind != " " and _is_assertion(ln.text):
                if ln.kind == "-":
                    removed_asserts.append(ln)
                else:
                    added_asserts += 1
    if len(removed_asserts) > added_asserts:
        first = removed_asserts[0]
        hits.append(Hit("test", fd.path, first.old_no, first.text,
                        f"assert/verify 순감 {len(removed_asserts) - added_asserts}줄 "
                        f"(삭제 {len(removed_asserts)} · 추가 {added_asserts}, 줄 번호는 변경 전)"))
    return hits


def _is_assertion(text: str) -> bool:
    return bool(ASSERTION.search(text)) and not DECLARATION.match(text) and not COMMENT_ONLY.match(text)


def scan_added_patterns(fd: FileDiff) -> list[Hit]:
    hits = []
    for hunk in fd.hunks:
        for idx, ln in enumerate(hunk):
            if ln.kind != "+":
                continue
            if SILENCE.search(ln.text):
                hits.append(Hit("silence", fd.path, ln.new_no, ln.text))
            if UNFINISHED.search(ln.text):
                hits.append(Hit("unfinished", fd.path, ln.new_no, ln.text))
            elif EMPTY_CATCH_INLINE.search(ln.text):
                hits.append(Hit("unfinished", fd.path, ln.new_no, ln.text, "빈 catch"))
            elif _opens_empty_block(hunk, idx):
                hits.append(Hit("unfinished", fd.path, ln.new_no, ln.text, "빈 catch"))
    return hits


def _opens_empty_block(hunk: list[Line], idx: int) -> bool:
    """추가된 catch {/except: 다음 추가 줄이 곧바로 닫히면 빈 블록. 문맥 줄이 끼면 기존 본문이 있으므로 아니다."""
    text = hunk[idx].text
    close = BLOCK_CLOSE if CATCH_OPEN.search(text) else PY_EMPTY_BODY if EXCEPT_OPEN.match(text) else None
    if close is None:
        return False
    for ln in hunk[idx + 1:]:
        if ln.kind != "+":
            return False
        if close.match(ln.text):
            return True
        if not BLANK_OR_COMMENT.match(ln.text):
            return False
    return False


def scan_exception(fd: FileDiff) -> list[Hit]:
    added = [ln for hunk in fd.hunks for ln in hunk
             if ln.kind == "+" and ln.text.strip() and not COMMENT_ONLY.match(ln.text)]
    if not added:
        return []
    note = "새 예외 파일" if fd.added_file else ""
    if len(added) > 1:
        note = f"{note + ' · ' if note else ''}추가 {len(added)}줄"
    return [Hit("exception", fd.path, added[0].new_no, added[0].text, note)]


def scan(files: list[FileDiff]) -> list[Hit]:
    hits: list[Hit] = []
    for fd in files:
        if not fd.path or is_doc(fd.path):
            continue
        hits += scan_test(fd)
        if fd.deleted:
            if is_check_config(fd.path):
                hits.append(Hit("threshold", fd.path, None, "", "검사 설정 파일 삭제"))
            continue
        if is_exception_file(fd.path):
            hits += scan_exception(fd)
            continue
        if is_gate_config(fd.path):
            hits += scan_threshold(fd)
        hits += scan_added_patterns(fd)
    order = {key: i for i, (key, _) in enumerate(CATEGORIES)}
    return sorted(hits, key=lambda h: order[h.category])   # 범주 안에서는 diff 순서를 유지한다


# --- 출력 ----------------------------------------------------------------------

def _clip(text: str, width: int = 100) -> str:
    text = text.strip().replace("`", "'")
    return text if len(text) <= width else text[:width - 1] + "…"


def render(hits: list[Hit], max_per_category: int = 10) -> str:
    if not hits:
        return "완화 신호: 0건 — 임계값 하향·테스트 약화·체커 침묵·미완성·예외 추가 해당 없음"
    out = [f"**완화 신호 {len(hits)}건** — 판정 아님. 사유(diff·PR 본문·티켓)가 있으면 넘긴다"]
    for key, label in CATEGORIES:
        group = [h for h in hits if h.category == key]
        if not group:
            continue
        out.append(f"- {label} {len(group)}")
        for h in group[:max_per_category]:
            loc = f"{h.path}:{h.line}" if h.line else h.path
            body = f" `{_clip(h.text)}`" if h.text.strip() else ""
            note = f" — {h.note}" if h.note else ""
            out.append(f"  - `{loc}`{body}{note}")
        if len(group) > max_per_category:
            out.append(f"  - … 외 {len(group) - max_per_category}건")
    return "\n".join(out)


# --- CLI -----------------------------------------------------------------------

class InputError(Exception):
    pass


def load_diff(rev_range: str | None, diff_path: str | None, repo: str) -> str:
    if rev_range:
        r = subprocess.run(["git", "-C", repo, "diff", "--no-color", "--no-ext-diff", "-M", rev_range],
                           capture_output=True)
        if r.returncode != 0:
            raise InputError(f"git diff 실패 — {r.stderr.decode('utf-8', 'replace').strip()}")
        return r.stdout.decode("utf-8", "replace")
    if diff_path and diff_path != "-":
        try:
            with open(diff_path, "rb") as fh:
                return fh.read().decode("utf-8", "replace")
        except OSError as e:
            raise InputError(f"diff 파일을 읽지 못함 — {e}") from e
    if sys.stdin.isatty():
        raise InputError("입력 없음 — 리비전 범위, --diff 파일, stdin 중 하나를 준다")
    return sys.stdin.buffer.read().decode("utf-8", "replace")   # 레거시 CP949 줄이 섞여도 멈추지 않게


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="diff에서 완화 신호(임계값 하향·테스트 약화·체커 침묵·미완성·예외 추가)를 찾아 markdown으로 출력한다.")
    ap.add_argument("rev_range", nargs="?", help="git 리비전 범위 (예: origin/develop...HEAD). 없으면 --diff 또는 stdin")
    ap.add_argument("--diff", metavar="FILE", help="unified diff 파일 ('-'는 stdin)")
    ap.add_argument("-C", "--repo", default=".", help="rev_range를 돌릴 git 저장소 (기본: 현재 디렉토리)")
    ap.add_argument("--max-per-category", type=int, default=10, metavar="N", help="범주당 표시 상한 (기본 10)")
    args = ap.parse_args(argv)
    if args.rev_range and args.diff:
        ap.error("리비전 범위와 --diff는 함께 쓰지 않는다")

    try:
        text = load_diff(args.rev_range, args.diff, args.repo)
    except InputError as e:
        print(f"gate_loosening_scan: {e}", file=sys.stderr)
        return 2
    if not text.strip():
        print("gate_loosening_scan: 입력 diff가 비어 있다 — 받은 경로(rtk 필터·리비전 범위)를 확인한다", file=sys.stderr)
        return 2
    files = parse_diff(text)
    if not files:
        print("gate_loosening_scan: unified diff 형식이 아니다", file=sys.stderr)
        return 2
    print(render(scan(files), args.max_per_category))
    return 0


if __name__ == "__main__":
    sys.exit(main())
