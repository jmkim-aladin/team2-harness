#!/usr/bin/env python3
"""시크릿 유출 스캔 — repo와 vault에서 자격증명 패턴을 찾는다.

"문서에 절대 남기지 않는다"를 규칙이 아니라 스캐너가 지키게 하는 장치 (북극성 5 — 게이트 기계화).
`/ad:harness-optimize 스택` 모드가 호출한다. pre-commit 훅으로도 쓸 수 있다.

사용법:
    python3 tools/secret_scan.py                     # repo + vault 전체
    python3 tools/secret_scan.py --staged            # git staged 파일만 (pre-commit 용)
    python3 tools/secret_scan.py <path...>           # 지정 경로만

발견 시 exit 1. 값은 마스킹해서 위치만 보고한다.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.environ.get("LOCAL_WIKI_PATH",
                       os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"))

# 패턴: 실값만 매칭하도록 길이 하한을 둔다 — 문서의 placeholder(perm-XXXX 등)는 통과
PATTERNS = [
    ("YouTrack 토큰", re.compile(r"perm-[A-Za-z0-9+/=.]{20,}")),
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
    ("GitHub 토큰", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    # 값 6자 하한 — `abc123` 길이의 짧은 실값도 잡는다. 2026-10-21 repo+vault 실측: 8→6 하향으로 repo 오탐 0건, vault 실값 후보 1건 추가 검출
    ("접속문자열 암호", re.compile(r"(?i)(password|pwd)\s*=\s*[^\s;'\"<{$][^\s;'\"]{5,}")),
    ("Bearer 실값", re.compile(r"Bearer\s+[A-Za-z0-9+/=._-]{30,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

SKIP_DIRS = {".git", "node_modules", "obj", "bin", ".next", "__pycache__", ".gstack", ".playwright-mcp", ".obsidian"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".xlsx", ".zip", ".dll", ".pglite", ".db", ".bundle", ".woff", ".woff2"}
# 환경변수 참조($VAR)·placeholder는 오탐 — 라인 단위 예외
FALSE_POSITIVE = re.compile(r"\$\{?[A-Z_]+|<[^>]+>|\{[^}]+\}|XXXX|퍼미션|예시|example", re.I)
# 스캔 명령 자기 자신(rg/grep의 패턴 인자)과 정규식 문자클래스는 시크릿이 아니다
SCAN_COMMAND_LINE = re.compile(r"\brg\b|\bgrep\b|\[\^|re\.compile")
# `password = request.unlockPassword,`·`password=self._get(...)` 같은 코드 식 — 식별자 체인 뒤에 호출·첨자·인자 구분자가 온다.
# 실값(`;` 구분 접속문자열, .env 값)은 뒤따르는 구두점이 없어 계속 잡힌다 — tests/test_secret_scan.py
CODE_EXPRESSION = re.compile(r"=\s*[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*[(\[),]")
# `UPDATE … SET PWD=@Password WHERE …` 처럼 값이 SQL 변수(@이름)인 문장 — 비밀번호가 아니라 SP 파라미터다.
# 접속문자열(`Server=…;Pwd=@…;`)은 SQL 문맥이 아니므로 계속 잡는다 — 2026-10-21 vault SP 분석 노트 오탐 1건
SQL_VARIABLE = re.compile(r"=\s*@[A-Za-z_]\w*[`),]*$")
SQL_CONTEXT = re.compile(r"\b(UPDATE|SET|DECLARE|INSERT|VALUES|WHERE|SELECT|EXEC|PROCEDURE)\b", re.I)
CONNECTION_STRING = re.compile(r"\b(server|data source|user id|uid|initial catalog)\s*=", re.I)


def is_sql_variable(value, line):
    return bool(SQL_VARIABLE.search(value) and SQL_CONTEXT.search(line)
                and not CONNECTION_STRING.search(line))


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if os.path.splitext(f)[1].lower() in SKIP_EXT:
                    continue
                yield os.path.join(base, f)


def staged_files():
    r = subprocess.run(["git", "-C", REPO, "diff", "--cached", "--name-only"],
                       capture_output=True, text=True)
    return [os.path.join(REPO, f) for f in r.stdout.split() if os.path.isfile(os.path.join(REPO, f))]


def scan(files):
    hits = 0
    for path in files:
        try:
            with open(path, errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if len(line) > 2000:
                        continue
                    if SCAN_COMMAND_LINE.search(line):
                        continue
                    for name, pat in PATTERNS:
                        m = pat.search(line)
                        if not m:
                            continue
                        if FALSE_POSITIVE.search(m.group(0)) or FALSE_POSITIVE.search(line[:m.start()][-30:]):
                            continue
                        if CODE_EXPRESSION.search(m.group(0)) or is_sql_variable(m.group(0), line):
                            continue
                        masked = m.group(0)[:8] + "…(마스킹)"
                        print(f"  [유출 의심] {path}:{i}  {name}  {masked}")
                        hits += 1
        except OSError:
            continue
    return hits


def main():
    args = sys.argv[1:]
    if args and args[0] == "--staged":
        files = staged_files()
        label = f"staged {len(files)}개 파일"
    elif args:
        files = list(iter_files(args))
        label = f"{len(files)}개 파일"
    else:
        roots = [REPO] + ([VAULT] if os.path.isdir(VAULT) else [])
        files = list(iter_files(roots))
        label = f"repo+vault {len(files)}개 파일"

    hits = scan(files)
    if hits:
        print(f"\nsecret_scan: {label} 중 {hits}건 발견 — 즉시 제거하고 해당 자격증명을 재발급하라")
        sys.exit(1)
    print(f"secret_scan: OK — {label}, 발견 0")


if __name__ == "__main__":
    main()
