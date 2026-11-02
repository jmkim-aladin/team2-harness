#!/usr/bin/env python3
"""Team skill usage from the shared local Codex/Claude collector.

Only explicit user invocations and Claude Skill tool calls are counted.
Session directory dates, mentions, injected skill catalogs and shell variables
are not evidence of a skill invocation. --days filters each record timestamp.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from agent_usage import collect_usage, known_skill_names


def skill_rows(stats, known):
    rows = []
    for name in sorted(n for n in known if n.startswith('ad-')):
        claude = stats['claude']
        codex = stats['codex']
        user = claude['skill_sources'].get('user', {}).get(name, 0)
        model = claude['skill_sources'].get('model', {}).get(name, 0)
        cx = codex['skill_hits'].get(name, 0)
        rows.append(dict(skill='ad:' + name[3:], user=user, model=model, codex=cx,
                         total=user + model + cx,
                         last=max(claude['last'].get(name, ''), codex['last'].get(name, '')) or None))
    return sorted(rows, key=lambda r: (-r['total'], r['skill']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--days', type=int, default=0, help='최근 N일; 0=전체 기간')
    ap.add_argument('--root', type=Path, default=Path.home() / '.claude/projects')
    ap.add_argument('--codex-root', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'sessions')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if args.days < 0:
        ap.error('--days must be nonnegative')
    harness = Path(os.environ.get('TEAM2_HARNESS_PATH', Path(__file__).resolve().parents[1]))
    known = known_skill_names(harness, Path.home() / '.claude', Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')), Path.home() / '.agents/skills')
    stats = collect_usage(args.root, args.codex_root, days=args.days, known_skills=known)
    rows = skill_rows(stats, known)
    if args.json:
        print(json.dumps(dict(schema_version=2, days=args.days, rows=rows), ensure_ascii=False, indent=2))
        return
    period = f'최근 {args.days}일' if args.days else '전체 기간'
    print(f'# ad:* 명시적 스킬 호출 — {period}\n')
    print('| 스킬 | Claude 입력 | Claude Skill 도구 | Codex 입력 | 계 | 마지막 관측(UTC) |')
    print('|------|--------------|-------------|--------------|----|------------------|')
    for row in rows:
        print(f"| {row['skill']} | {row['user']} | {row['model']} | {row['codex']} | {row['total']} | {row['last'] or '-'} |")
    print('\n0회는 명시적 호출 관측 없음이다. 자연어로 실행한 작업·스킬 본문 읽기·Hermes cron 사용 여부를 뜻하지 않는다.')


if __name__ == '__main__':
    main()
