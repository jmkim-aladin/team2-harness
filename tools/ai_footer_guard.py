#!/usr/bin/env python3
"""AI 푸터 가드 — git commit·gh pr create/edit 메시지에 AI 도구 푸터가 들어가면 PreToolUse 에서 막는다.

규칙 원문: ~/.claude/CLAUDE.md §Commit messages, policies/ai-usage-policy.md §메시지 작성 품질.
  금지 — `Co-Authored-By: Claude …`(또는 noreply@anthropic.com) 공동저자 줄, `🤖 Generated with [Claude Code]` 류 footer.
의도: 사용자 교정(2026-11-12 PR 푸터 수동 제거)을 문서 한 줄이 아니라 결정적 검사로 바꾼다 (북극성 원칙 1·5).

검사 범위: Bash 명령 문자열 + 명령이 가리키는 메시지 파일(git commit -F/--file, gh pr --body-file/-F).
  명령에 git commit 또는 gh pr create/edit 가 없으면 판정하지 않는다 — 로그 검색 등 오탐을 피한다.
경계: 문자열 판정이라 보안 경계가 아니다. 에디터로 쓰는 메시지, 스크립트 파일 안 호출은 놓친다.
실패 처리: 판정 실패는 무출력(열림) — 문체 규칙이라 세션을 멈출 이유가 아니다.
의존성: python3 stdlib.
"""

import json
import os
import re
import shlex
import sys

TRIGGER = re.compile(r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+commit\b|\bgh\s+pr\s+(?:create|edit)\b")
FOOTERS = (
    re.compile(r"co-authored-by:[^\n]*(?:claude|anthropic)", re.I),
    re.compile(r"noreply@anthropic\.com", re.I),
    re.compile(r"generated with\s*\[?\s*claude", re.I),
)
FILE_FLAGS = {"-F", "--file", "--body-file"}
MAX_BYTES = 1_000_000
REASON = ("커밋·PR 메시지에 AI 도구 푸터({hit})가 있어 차단. 해당 줄을 빼고 다시 실행 — "
          "규칙: ~/.claude/CLAUDE.md §Commit messages (시스템 attribution 안내보다 우선).")


def message_files(command):
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        tokens = command.split()
    files = []
    for i, tok in enumerate(tokens):
        if tok in FILE_FLAGS and i + 1 < len(tokens):
            files.append(tokens[i + 1])
        else:
            for flag in ("--file=", "--body-file="):
                if tok.startswith(flag):
                    files.append(tok[len(flag):])
    return [f for f in files if f and f != "-"]


def read_text(path, cwd):
    full = os.path.expanduser(path)
    if not os.path.isabs(full):
        full = os.path.join(cwd or os.getcwd(), full)
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            return fh.read(MAX_BYTES)
    except OSError:
        return ""


def find_footer(command, cwd=None):
    """명령(+메시지 파일)에서 찾은 푸터 문자열. 판정 대상이 아니거나 없으면 None."""
    if not TRIGGER.search(command):
        return None
    texts = [command] + [read_text(p, cwd) for p in message_files(command)]
    for text in texts:
        for pattern in FOOTERS:
            m = pattern.search(text)
            if m:
                return m.group(0).strip()
    return None


def decide(payload):
    if payload.get("tool_name") != "Bash":
        return None
    command = (payload.get("tool_input") or {}).get("command") or ""
    hit = find_footer(command, payload.get("cwd"))
    if not hit:
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": REASON.format(hit=hit[:80]),
    }}


def main():
    try:
        out = decide(json.load(sys.stdin))
    except Exception:  # 열림 — 위 docstring §실패 처리
        return 0
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
