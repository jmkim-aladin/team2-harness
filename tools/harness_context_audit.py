#!/usr/bin/env python3
"""Audit local Codex/Claude logs separately; report observed usage and estimate metadata.

Usage: python3 tools/harness_context_audit.py --days 30 --engine both --json
Observed model requests, tool calls and static chars/4 estimates are distinct.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
from pathlib import Path
from statistics import median
from datetime import datetime, timedelta, timezone

from agent_usage import collect_usage, known_skill_names, skill_files

HOME = Path.home()
HARNESS = Path(os.environ.get('TEAM2_HARNESS_PATH', HOME / 'Documents/workspace/team2'))
CLAUDE_DIR = HOME / '.claude'
CODEX_DIR = Path(os.environ.get('CODEX_HOME', HOME / '.codex'))
LIMITS = dict(resident_tokens=8000, avg_context_tokens=200000, bash_share=.50, cd_share=.20, reread_count=5)
LIMITATIONS = [
    '상주량은 발견한 지시문·스킬 메타데이터의 chars/4 근사치이며 실제 토큰 수가 아니다. 도구 스키마·숨은 시스템 지침·자동 메모리·원격 스킬은 포함하지 않는다.',
    '스킬은 설치 목록에 있는 명시적 선두 $alias, Claude command-name 또는 Skill 호출만 집계한다. 자연어 요청에 따른 실제 스킬 본문 읽기는 집계하지 않는다.',
    '평균 컨텍스트는 usage가 관측된 모델 응답의 입력 토큰 평균이다. 도구 호출 수·context window 한도와 다르며 usage 없는 요청은 평균에서 제외한다.',
    'Codex는 세션별 response_id가 있는 native usage를 우선하며 native 전환 이전의 legacy 변경값은 보존한다. 이후 ID 연결이 불명확한 legacy snapshot은 quality.legacy_snapshots_after_native로 제외 범위를 표시한다.',
    'Read는 명시적 파일 읽기 도구만 집계한다. 셸·REPL 래퍼 내부 읽기는 추정하지 않으며 도구 결과 지연은 로그 시각 차이다.',
    'usage는 로컬 로그 관측값이며 구독 사용 한도나 청구액을 환산한 값이 아니다. Hermes cron과 로그 밖 실행은 별도 확인한다.',
]


def read(path):
    try:
        return Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return ''


def load_json(path):
    try:
        d = json.loads(read(path) or '{}')
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def description_cost(path, engine):
    text = read(path)
    fm = re.search(r'^---\n(.*?)\n---', text, re.S)
    if not fm:
        return 0
    if engine == 'claude' and re.search(r'^disable-model-invocation:\s*true\s*$', fm[1], re.M):
        return 0
    if engine == 'codex' and re.search(r'^\s*allow_implicit_invocation:\s*false\s*$', read(Path(path).parent / 'agents/openai.yaml'), re.M):
        return 0
    desc = re.search(r'^description:\s*(.*(?:\n[ \t]+.*)*)', fm[1], re.M)
    return len(desc[1]) if desc else 0


def plugin_skill_roots(home):
    settings = load_json(home / 'settings.json')
    installed = load_json(home / 'plugins/installed_plugins.json')
    enabled = {k for k, v in settings.get('enabledPlugins', {}).items() if v}
    for key, entries in installed.get('plugins', {}).items():
        if key not in enabled:
            continue
        # The registry may list multiple installations; count physical paths once.
        for entry in entries:
            if isinstance(entry, dict) and entry.get('installPath'):
                yield key.split('@')[0], Path(entry['installPath']) / 'skills'


def resident_budget(engine, *, harness=HARNESS, claude_home=CLAUDE_DIR, codex_home=CODEX_DIR, agents_home=None):
    harness, claude_home, codex_home = map(Path, (harness, claude_home, codex_home))
    rows, seen = {}, set()

    def instructions(path, imports=False):
        path = Path(path)
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            return
        seen.add(resolved)
        text = read(path)
        rows[str(path)] = len(text)
        if imports:
            for name in re.findall(r'^\s*@([^\s]+)\s*$', text, re.M):
                imported = Path(name).expanduser()
                instructions(imported if imported.is_absolute() else path.parent / imported, True)

    if engine == 'claude':
        instructions(claude_home / 'CLAUDE.md', True)
        instructions(harness / 'CLAUDE.md', True)
        roots = [claude_home / 'skills']
        roots.extend(root for _, root in plugin_skill_roots(claude_home))
        commands = list((harness / '.claude/commands/ad').glob('*.md'))
    else:
        instructions(codex_home / 'AGENTS.md')
        instructions(harness / 'AGENTS.md')
        roots = [codex_home / 'skills'] + ([Path(agents_home)] if agents_home else [])
        commands = []
    for root in roots:
        for p in skill_files(root):
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                rows[str(p)] = description_cost(p, engine)
    for p in commands:
        rows[str(p)] = description_cost(p, engine)
    return rows


def hooks(engine, *, harness=HARNESS, claude_home=CLAUDE_DIR, codex_home=CODEX_DIR):
    files = [Path(claude_home) / 'settings.json', Path(harness) / '.claude/settings.json', Path(harness) / '.claude/settings.local.json'] if engine == 'claude' else [Path(codex_home) / 'hooks.json', Path(harness) / '.codex/hooks.json']
    result = []
    for path in files:
        for event, groups in load_json(path).get('hooks', {}).items():
            for group in groups:
                for hook in group.get('hooks', []):
                    # Only expose the executable, never credentials in command args.
                    try:
                        words = shlex.split(hook.get('command', ''))
                    except ValueError:
                        words = []
                    head = Path(words[0]).name if words and '=' not in words[0] else '<redacted>'
                    result.append(dict(source=str(path), event=event, matcher=group.get('matcher', '(all)'), command=head))
    return result


def build_report(days=90, engine='both', *, claude_root=None, codex_root=None,
                 harness=HARNESS, claude_home=CLAUDE_DIR, codex_home=CODEX_DIR, agents_home=HOME / '.agents/skills', now=None):
    now = now or datetime.now(timezone.utc)
    known = known_skill_names(harness, claude_home, codex_home, agents_home)
    for plugin, root in plugin_skill_roots(Path(claude_home)):
        for p in skill_files(root):
            known.update([p.parent.name, plugin + ':' + p.parent.name])
    stats = collect_usage(claude_root or Path(claude_home) / 'projects', codex_root or Path(codex_home) / 'sessions', days=days, now=now, known_skills=known, engines=('claude', 'codex') if engine == 'both' else (engine,))
    engines = {}
    for name in ('claude', 'codex') if engine == 'both' else (engine,):
        data = stats[name]
        budget = resident_budget(name, harness=harness, claude_home=claude_home, codex_home=codex_home, agents_home=agents_home)
        data['resident_chars'] = sum(budget.values())
        data['resident_tokens_estimate'] = data['resident_chars'] // 4
        data['resident_breakdown_chars'] = budget
        data['configured_hooks'] = hooks(name, harness=harness, claude_home=claude_home, codex_home=codex_home)
        warnings = []
        if data['resident_tokens_estimate'] > LIMITS['resident_tokens']:
            warnings.append('상주 메타데이터 근사치가 예산을 초과함; 실제 로드 경로 확인 필요')
        if data['avg_context_tokens'] is not None and data['avg_context_tokens'] > LIMITS['avg_context_tokens']:
            warnings.append('관측 모델 요청당 평균 입력이 컨텍스트 예산을 초과함')
        if data['bash_share'] is not None and data['bash_share'] > LIMITS['bash_share']:
            warnings.append('셸 도구 비중이 높음; 원인과 작업 성격 확인 필요')
        if data['cd_share'] is not None and data['cd_share'] > LIMITS['cd_share']:
            warnings.append('직접 관측 셸 호출 중 cd 비중이 높음')
        data['warnings'] = warnings
        engines[name] = data
    return dict(schema_version=2, days=days, observed_window_end=now.isoformat(),
                observed_window_start=(now - timedelta(days=days)).isoformat() if days else None,
                engines=engines, limitations=LIMITATIONS)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--days', type=int, default=90, help='0=전체 기간')
    ap.add_argument('--engine', choices=['both', 'claude', 'codex'], default='both')
    ap.add_argument('--claude-root', type=Path)
    ap.add_argument('--codex-root', type=Path)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if args.days < 0:
        ap.error('--days must be nonnegative')
    report = build_report(args.days, args.engine, claude_root=args.claude_root, codex_root=args.codex_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(f'하네스 컨텍스트 감사 — 최근 {args.days}일' if args.days else '하네스 컨텍스트 감사 — 전체 기간')
    for engine, stats in report['engines'].items():
        print(f'\n## {engine}')
        print(f"상주 메타데이터: {stats['resident_chars']:,} chars / 약 {stats['resident_tokens_estimate']:,} tok (추정)")
        avg = stats['avg_context_tokens']
        print(f"관측 usage 응답: {stats['usage_requests']:,}; 평균 입력: {avg:,.0f} tok" if avg is not None else '관측 입력 usage 없음 — 평균 입력 미확인')
        print(f"도구 호출: {sum(stats['tool_calls'].values()):,}; 설정된 훅: {len(stats['configured_hooks'])}")
        for tool, count in sorted(stats['tool_calls'].items(), key=lambda x: -x[1])[:12]:
            latency = stats['tool_latency'].get(tool, [])
            med = f'{median(latency):.2f}s' if latency else '미확인'
            print(f'  {tool}: {count:,}회 / 결과 시각차 중앙값 {med}')
        print('명시적 스킬 호출:', ', '.join(f'{n}={c}' for n, c in sorted(stats['skill_hits'].items(), key=lambda x: -x[1])[:15]) or '관측 없음')
        print('반복 읽기(기간 합계; 같은 작업의 재독이라는 뜻은 아님):')
        for path, count in sorted(stats['reads'].items(), key=lambda x: -x[1])[:15]:
            if count > LIMITS['reread_count']:
                print(f'  {count}회 {path}')
        for warning in stats['warnings']:
            print('  [관찰]', warning)
    print('\n집계 범위·한계:')
    for limit in report['limitations']:
        print('-', limit)


if __name__ == '__main__':
    main()
