#!/usr/bin/env python3
"""팀 스킬(ad:*) 사용 통계 리포트.

Claude Code 세션 로그(~/.claude/projects/**/*.jsonl)에서 스킬 호출을 집계한다.
- 사용자 호출: user 메시지의 <command-name>/ad:... 태그
- 모델 호출: assistant tool_use(name=Skill)의 input.skill

사용법:
    python3 tools/skill_usage_report.py            # 전체 기간
    python3 tools/skill_usage_report.py --days 30  # 최근 N일
"""
import argparse
import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
CMD_RE = re.compile(r"<command-name>/?(ad:[a-z0-9-]+)</command-name>")


def iter_lines(root):
    for path in glob.glob(os.path.join(root, "*", "*.jsonl")):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    yield line
        except OSError:
            continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="최근 N일만 (0=전체)")
    ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    args = ap.parse_args()

    cutoff = None
    if args.days:
        cutoff = datetime.now(KST) - timedelta(days=args.days)

    stats = defaultdict(lambda: {"user": 0, "model": 0, "last": None})
    earliest = None

    for line in iter_lines(args.root):
        if "ad:" not in line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = d.get("timestamp")
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(KST)
        except ValueError:
            continue
        if earliest is None or t < earliest:
            earliest = t
        if cutoff and t < cutoff:
            continue

        def hit(skill, kind):
            s = stats[skill]
            s[kind] += 1
            if s["last"] is None or t > s["last"]:
                s["last"] = t

        if d.get("type") == "user":
            content = d.get("message", {}).get("content")
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False) if content else ""
            for m in CMD_RE.finditer(text):
                hit(m.group(1), "user")
        elif d.get("type") == "assistant":
            for block in d.get("message", {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                    skill = (block.get("input") or {}).get("skill", "")
                    if skill.startswith("ad:"):
                        hit(skill, "model")

    # 레포에 존재하는 스킬 목록과 대조 (0회 스킬 표시)
    repo = os.environ.get("TEAM2_HARNESS_PATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    known = sorted(
        "ad:" + os.path.basename(p)[:-3]
        for p in glob.glob(os.path.join(repo, ".claude", "commands", "ad", "*.md"))
    )
    for k in known:
        stats.setdefault(k, {"user": 0, "model": 0, "last": None})

    period = f"최근 {args.days}일" if args.days else f"전체 (로그 시작: {earliest.date() if earliest else '?'})"
    print(f"# ad:* 스킬 사용 통계 — {period}, 기준 {datetime.now(KST).date()}\n")
    print("| 스킬 | 사용자 호출 | 모델 호출 | 계 | 마지막 사용 |")
    print("|------|------------|-----------|----|------------|")
    rows = sorted(stats.items(), key=lambda x: -(x[1]["user"] + x[1]["model"]))
    for name, s in rows:
        total = s["user"] + s["model"]
        last = s["last"].strftime("%Y-%m-%d") if s["last"] else "-"
        mark = " ⚠️" if total == 0 else ""
        print(f"| {name}{mark} | {s['user']} | {s['model']} | {total} | {last} |")
    zero = [n for n, s in stats.items() if s["user"] + s["model"] == 0]
    if zero:
        print(f"\n0회 스킬 {len(zero)}개 — 가지치기 검토 대상 (policies/skill-authoring-principles.md 4단계)")


if __name__ == "__main__":
    main()
