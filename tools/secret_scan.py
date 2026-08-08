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
    ("접속문자열 암호", re.compile(r"(?i)(password|pwd)\s*=\s*[^\s;'\"<{$][^\s;'\"]{7,}")),
    ("Bearer 실값", re.compile(r"Bearer\s+[A-Za-z0-9+/=._-]{30,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

SKIP_DIRS = {".git", "node_modules", "obj", "bin", ".next", "__pycache__", ".gstack", ".playwright-mcp", ".obsidian"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".xlsx", ".zip", ".dll", ".pglite", ".db", ".bundle", ".woff", ".woff2"}
# 환경변수 참조($VAR)·placeholder는 오탐 — 라인 단위 예외
FALSE_POSITIVE = re.compile(r"\$\{?[A-Z_]+|<[^>]+>|\{[^}]+\}|XXXX|퍼미션|예시|example", re.I)
# 스캔 명령 자기 자신(rg/grep의 패턴 인자)과 정규식 문자클래스는 시크릿이 아니다
SCAN_COMMAND_LINE = re.compile(r"\brg\b|\bgrep\b|\[\^|re\.compile")


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
