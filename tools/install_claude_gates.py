#!/usr/bin/env python3
"""사용자 레벨 Claude Code 하드 게이트 설치 — ~/.claude/settings.json 에 훅·ask 규칙을 멱등 병합한다.

설치 대상 (모든 repo·worktree·Paperclip 실행에 적용):
  PreToolUse 훅  sqlcmd-readonly(Bash) · block-db-mcp(mcp__.*) · agent-run-guard(Bash·MCP)
  permissions.ask  gh pr merge (+ rtk 훅이 재작성한 형태) — 사람 세션은 확인, 에이전트 실행은 거부라 둘 다 의도와 맞다
git push·gh pr create 는 정적 ask 에 두지 않고 agent-run-guard 가 판정한다. 훅 allow 는 ask 규칙을 넘지 못해
승인된 에이전트 push 까지 막히기 때문이다. 이전에 설치한 해당 ask 규칙은 제거해 수렴시킨다.
훅 명령은 하네스 절대 경로다 — 사용자 레벨에서 $CLAUDE_PROJECT_DIR 는 하네스가 아니기 때문이다.
보존: 다른 훅·env·permissions 항목은 건드리지 않는다. 관리 항목은 훅 스크립트 파일명으로 식별한다.

    python3 tools/install_claude_gates.py                       # ~/.claude/settings.json 에 설치
    python3 tools/install_claude_gates.py --check               # 보고만 (설치 필요 시 exit 1)
    python3 tools/install_claude_gates.py --settings PATH --harness DIR
    python3 tools/install_claude_gates.py --uninstall           # 관리 훅·ask 규칙만 제거 (--check 와 함께면 미리보기)
제거 후 setup.sh·setup_harness.py 를 다시 돌리면 게이트가 재설치된다.
의존성: python3 stdlib.
"""

import argparse
import copy
import json
import os
import shlex
import shutil
import sys
import tempfile
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = (
    ("sqlcmd-readonly", "Bash"),
    ("block-db-mcp", "mcp__.*"),
    ("agent-run-guard", "Bash|mcp__.*"),
)
# rtk PreToolUse 훅이 `gh pr merge` 를 `rtk gh pr merge` 로 바꾼 뒤 권한을 판정한다
ASK_RULES = ("Bash(gh pr merge:*)", "Bash(rtk gh pr merge:*)")
RETIRED_ASK_RULES = ("Bash(git push:*)", "Bash(gh pr create:*)", "Bash(rtk git push:*)", "Bash(rtk gh pr create:*)")


def hook_command(harness, name):
    return "bash " + shlex.quote(os.path.join(harness, ".claude", "hooks", name + ".sh"))


def _managed(command, name):
    return isinstance(command, str) and f"/.claude/hooks/{name}.sh" in command.replace("\\", "/")


def merge_settings(settings, harness):
    """(새 settings, 변경 목록). 입력은 바꾸지 않는다. 형식이 예상과 다르면 ValueError."""
    if not isinstance(settings, dict):
        raise ValueError("settings.json 최상위가 객체가 아님")
    s = copy.deepcopy(settings)
    hooks = s.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings.json hooks 가 객체가 아님")
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list) or not all(isinstance(g, dict) for g in pre):
        raise ValueError("settings.json hooks.PreToolUse 가 목록이 아님")
    changes = []
    for name, matcher in HOOKS:
        want = hook_command(harness, name)
        kept_exact, removed, groups = False, 0, []
        for group in pre:
            entries = group.get("hooks")
            if not isinstance(entries, list) or not entries:
                groups.append(group)
                continue
            keep = []
            for h in entries:
                if isinstance(h, dict) and _managed(h.get("command"), name):
                    if not kept_exact and group.get("matcher") == matcher and h.get("command") == want:
                        kept_exact = True
                        keep.append(h)
                    else:
                        removed += 1  # 경로가 바뀐 옛 항목·중복
                        continue
                else:
                    keep.append(h)
            if keep:
                group["hooks"] = keep
                groups.append(group)
        pre[:] = groups
        if not kept_exact:
            pre.append({"matcher": matcher, "hooks": [{"type": "command", "command": want}]})
            changes.append(f"PreToolUse 훅 {'갱신' if removed else '추가'} — {name} [{matcher}]")
        elif removed:
            changes.append(f"PreToolUse 훅 중복 제거 — {name} ({removed}건)")
    perms = s.setdefault("permissions", {})
    if not isinstance(perms, dict):
        raise ValueError("settings.json permissions 가 객체가 아님")
    ask = perms.setdefault("ask", [])
    if not isinstance(ask, list):
        raise ValueError("settings.json permissions.ask 가 목록이 아님")
    for rule in RETIRED_ASK_RULES:
        if rule in ask:
            ask[:] = [r for r in ask if r != rule]
            changes.append(f"permissions.ask 제거 — {rule} (훅 판정으로 이관)")
    for rule in ASK_RULES:
        if rule not in ask:
            ask.append(rule)
            changes.append(f"permissions.ask 추가 — {rule}")
    return s, changes


def remove_settings(settings):
    """(새 settings, 변경 목록). 관리 훅(경로 무관)과 관리 ask 규칙만 뺀다. 다른 항목은 그대로 둔다."""
    if not isinstance(settings, dict):
        raise ValueError("settings.json 최상위가 객체가 아님")
    s = copy.deepcopy(settings)
    changes = []
    hooks = s.get("hooks")
    pre = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    if isinstance(pre, list):
        groups = []
        for group in pre:
            entries = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(entries, list):
                groups.append(group)
                continue
            keep = []
            for h in entries:
                name = next((n for n, _ in HOOKS if isinstance(h, dict) and _managed(h.get("command"), n)), None)
                if name:
                    changes.append(f"PreToolUse 훅 제거 — {name} [{group.get('matcher')}]")
                else:
                    keep.append(h)
            if keep or not entries:
                group["hooks"] = keep
                groups.append(group)
        pre[:] = groups
        if not pre:
            del hooks["PreToolUse"]
    perms = s.get("permissions")
    ask = perms.get("ask") if isinstance(perms, dict) else None
    if isinstance(ask, list):
        for rule in ASK_RULES + RETIRED_ASK_RULES:
            if rule in ask:
                ask[:] = [r for r in ask if r != rule]
                changes.append(f"permissions.ask 제거 — {rule}")
        if not ask:
            del perms["ask"]
    return s, changes


def read_settings(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_settings(settings, path):
    """원자적 쓰기. 심볼릭 링크면 대상 파일을 갱신하고, 기존 파일은 .bak-<ts> 로 남긴다."""
    real = os.path.realpath(path)
    os.makedirs(os.path.dirname(real), exist_ok=True)
    backup = None
    if os.path.exists(real):
        backup = f"{real}.bak-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(real, backup)
    fd, tmp = tempfile.mkstemp(prefix=".settings-", dir=os.path.dirname(real))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write("\n")
        if backup:
            shutil.copymode(backup, tmp)
        os.replace(tmp, real)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return backup


def main(argv=None):
    ap = argparse.ArgumentParser(description="사용자 레벨 Claude Code 하드 게이트 설치 (멱등)")
    ap.add_argument("--settings", default=os.path.join(os.path.expanduser("~"), ".claude", "settings.json"))
    ap.add_argument("--harness", default=REPO, help="훅 스크립트가 있는 하네스 절대 경로")
    ap.add_argument("--check", action="store_true", help="보고만, 변경 없음 (설치 필요 시 exit 1)")
    ap.add_argument("--uninstall", action="store_true", help="관리 훅·ask 규칙 제거")
    a = ap.parse_args(argv)
    harness = os.path.abspath(a.harness)
    try:
        current = read_settings(a.settings)
        merged, changes = remove_settings(current) if a.uninstall else merge_settings(current, harness)
    except (OSError, ValueError) as e:
        print(f"  ⚠ {a.settings} 를 읽거나 병합할 수 없어 중단 — {e}")
        return 2
    if not changes:
        print("  제거할 게이트 없음" if a.uninstall else "  이미 설치됨 — 게이트 훅 3종·ask 규칙")
        return 0
    for c in changes:
        print(("  [변경 예정] " if a.check else "  ✓ ") + c)
    if a.check:
        return 1
    backup = write_settings(merged, a.settings)
    if backup:
        print(f"  기존 설정 백업 — {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
