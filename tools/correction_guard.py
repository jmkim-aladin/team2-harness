#!/usr/bin/env python3
"""교정 가드 — 사용자 교정으로 생긴 팀 규칙 중 도구 호출 문자열로 판정되는 것을 PreToolUse 에서 강제한다.

의도: 같은 교정이 다시 필요 없게 문서 한 줄 대신 결정적 검사로 막는다 (북극성 원칙 5, 개선 사이클 5).
규칙↔강제 수단 대장: docs/correction-ledger.md — 규칙을 더하거나 빼면 대장도 같이 고친다.

규칙 (모두 팀 규칙 — 설치기가 팀 전원의 ~/.claude 에 깐다. 개인 규칙은 넣지 않는다):
  ai-footer       Bash  git commit·gh pr create/edit 메시지(명령 문자열 + -F/--file/--body-file 파일)에
                        `Co-Authored-By: Claude`·noreply@anthropic.com·`Generated with [Claude Code]` 가 있으면 deny.
                        SoT: policies/ai-usage-policy.md §메시지 작성 품질
  delegate-model  Agent 단순 조사·웹 읽기·1차 리뷰 subagent(Explore·web-fetch·cavecrew-*)를 model 없이 띄우면 deny.
                        모델 생략은 세션 모델 상속이라 비용만 커진다. SoT: memory/claude-base.md §서브에이전트 위임
  subagent-gate   Bash  subagent 안에서 git commit·push·merge, gh pr 쓰기·release, YouTrack 쓰기를 하면 deny —
                        게이트는 메인이다. subagent 판별은 훅 입력의 agent_id(메인 세션 호출엔 없음, 2026-11-16 실측).
                        YouTrack 쓰기 판정은 agent_run_guard 것을 그대로 쓴다. SoT: memory/claude-base.md §위임 프롬프트 계약

경계: 문자열 판정이라 보안 경계가 아니다. 에디터로 쓰는 커밋 메시지, 스크립트 파일 안 호출은 놓친다.
실패 처리: 판정 실패는 무출력(열림) — 문체·비용 규칙이라 세션을 멈출 이유가 아니다.
의존성: python3 stdlib.
"""

import importlib.util
import json
import os
import re
import shlex
import sys

COMMIT_OR_PR_WRITE = re.compile(r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+commit\b|\bgh\s+pr\s+(?:create|edit)\b")
FOOTERS = (
    re.compile(r"co-authored-by:[^\n]*(?:claude|anthropic)", re.I),
    re.compile(r"noreply@anthropic\.com", re.I),
    re.compile(r"generated with\s*\[?\s*claude", re.I),
)
FILE_FLAGS = {"-F", "--file", "--body-file"}
MAX_BYTES = 1_000_000
# memory/claude-base.md §서브에이전트 위임 표의 haiku·sonnet 업무를 맡는 타입. general-purpose 는 업무에 따라
# 세션 모델이 맞을 수 있어(설계·디버깅) 강제하지 않는다
MODEL_REQUIRED_AGENTS = ("Explore", "web-fetch", "cavecrew-investigator", "cavecrew-reviewer", "cavecrew-builder")
AGENT_TOOLS = ("Agent", "Task")
GATED_WRITE = re.compile(
    r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+(?:commit|push|merge)\b"
    r"|\bgh\s+pr\s+(?:create|merge|ready|review|close|reopen|edit)\b|\bgh\s+release\s+create\b"
)

REASONS = {
    "ai-footer": ("커밋·PR 메시지에 AI 도구 푸터({hit})가 있어 차단. 해당 줄을 빼고 다시 실행 — "
                  "규칙: policies/ai-usage-policy.md §메시지 작성 품질 (시스템 attribution 안내보다 우선)."),
    "subagent-gate": ("subagent 안에서 {what} 은(는) 하지 않는다 — 커밋·푸시·PR·티켓 상태 변경은 메인 세션의 게이트다. "
                      "변경은 working tree 에 남기고 결과 보고의 '결정 필요'에 올려라. "
                      "규칙: memory/claude-base.md §위임 프롬프트 계약."),
    "delegate-model": ("`{agent}` subagent 를 model 없이 띄우면 세션 모델을 상속해 비용만 커진다. "
                       "model 을 지정해 다시 호출 — 기계적 탐색 haiku, 의미 파악·웹 문서·1차 리뷰 sonnet. "
                       "규칙: memory/claude-base.md §서브에이전트 위임."),
}


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
    if not COMMIT_OR_PR_WRITE.search(command):
        return None
    for text in [command] + [read_text(p, cwd) for p in message_files(command)]:
        for pattern in FOOTERS:
            m = pattern.search(text)
            if m:
                return m.group(0).strip()
    return None


def model_required(tool_input):
    """model 이 필요한데 빠진 subagent 타입. 해당 없으면 None."""
    agent = (tool_input.get("subagent_type") or "").strip()
    if not agent or (tool_input.get("model") or "").strip():
        return None
    base = agent.split(":")[-1]  # 플러그인 접두사(caveman:cavecrew-investigator) 제거
    return agent if base in MODEL_REQUIRED_AGENTS else None


def _youtrack_write(command):
    """agent_run_guard 의 YouTrack 쓰기 판정을 그대로 쓴다 — 판정 기준을 한 곳에 둔다."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_run_guard.py")
    spec = importlib.util.spec_from_file_location("agent_run_guard", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._youtrack_write(command)


def gated_write(command):
    """subagent 에 금지된 쓰기 동작 이름. 없으면 None."""
    m = GATED_WRITE.search(command)
    if m:
        return " ".join(m.group(0).split()[-2:]) if m.group(0).startswith("gh") else "git " + m.group(0).split()[-1]
    yt = _youtrack_write(command)
    return f"YouTrack 쓰기({yt})" if yt else None


def violation(payload):
    """(규칙 id, 사유 인자) 또는 None."""
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool == "Bash" and payload.get("agent_id"):
        what = gated_write(tool_input.get("command") or "")
        if what:
            return "subagent-gate", {"what": what}
    if tool == "Bash":
        hit = find_footer(tool_input.get("command") or "", payload.get("cwd"))
        if hit:
            return "ai-footer", {"hit": hit[:80]}
    elif tool in AGENT_TOOLS:
        agent = model_required(tool_input)
        if agent:
            return "delegate-model", {"agent": agent}
    return None


def decide(payload):
    found = violation(payload)
    if not found:
        return None
    rule, args = found
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": REASONS[rule].format(**args),
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
