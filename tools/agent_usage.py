"""Stream local agent logs into engine-specific, deduplicated usage observations.

No prompts, source contents or shell arguments are retained in the report. Skill
counts are explicit leading user invocations or Claude Skill calls, not mentions.
"""
from __future__ import annotations

import json
import re
import shlex
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL = re.compile(r'^\s*\$([a-z][a-z0-9_-]*)(?=\s|$)')
COMMAND = re.compile(r'^\s*(?:<command-message>[^<]*</command-message>\s*)?<command-name>/?([a-z][a-z0-9:_-]*)</command-name>')


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
    except ValueError:
        return None


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def canonical_skill(name):
    return 'ad-' + name[3:] if name.startswith('ad:') else name


def records(path, quality):
    try:
        with path.open(encoding='utf-8', errors='replace') as f:
            for number, line in enumerate(f):
                try:
                    rec = json.loads(line)
                except (ValueError, RecursionError):
                    quality['malformed_records'] += 1
                    continue
                if not isinstance(rec, dict):
                    quality['malformed_records'] += 1
                    continue
                yield number, rec
    except OSError:
        quality['unreadable_files'] += 1


def text_blocks(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ''
    return '\n'.join(c.get('text', '') for c in content
                     if isinstance(c, dict) and c.get('type') in ('text', 'input_text')
                     and isinstance(c.get('text'), str))


def skill_files(root):
    """Discover installed entrypoints, skipping disabled and hidden trees."""
    root = Path(root)
    if not root.is_dir():
        return []
    found = []
    for child in root.iterdir():
        if child.name.startswith('.') and child.name != '.system':
            continue
        entry = child / 'SKILL.md'
        if entry.is_file():
            found.append(entry)
        elif child.name in ('synced', '.system'):
            found.extend(child.rglob('SKILL.md'))
    return found


def known_skill_names(harness, claude_home, codex_home, agents_home=None):
    names = set()
    for root in [Path(claude_home) / 'skills', Path(codex_home) / 'skills', agents_home]:
        if root is None:
            continue
        for p in skill_files(root):
            names.add(p.parent.name)
            try:
                m = re.search(r'^name:\s*[\"\']?([^\n\"\']+)', p.read_text(), re.M)
                if m:
                    names.add(m.group(1).strip())
            except OSError:
                continue
    names.update('ad-' + p.stem for p in (Path(harness) / '.claude/commands/ad').glob('*.md'))
    return names


def _new_stats():
    return dict(skill_hits=Counter(), last={}, skill_sources=defaultdict(Counter),
                tool_calls=Counter(), tool_result_chars=Counter(), tool_errors=Counter(),
                tool_latency=defaultdict(list), reads=Counter(), bash_head=Counter(),
                tokens=Counter(), quality=Counter(), usage_requests=0,
                context_sum=0, context_requests=0, usage_sources=Counter())


def _hit(stats, name, source, t, known):
    name = canonical_skill(name)
    if name not in known:
        return
    stats['skill_hits'][name] += 1
    stats['skill_sources'][source][name] += 1
    day = t.date().isoformat()
    stats['last'][name] = max(stats['last'].get(name, ''), day)


def _merge_usage(store, key, usage, engine):
    if not isinstance(usage, dict):
        return
    # A single Claude message is serialized repeatedly as blocks arrive. Preserve
    # the latest observed maximum for each counter instead of summing snapshots.
    fields = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens') if engine == 'claude' else (
        'input_tokens', 'output_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'reasoning_output_tokens')
    values = {field: usage[field] for field in fields if integer(usage.get(field))}
    if not values:
        return
    item = store.setdefault(key, {})
    for field, n in values.items():
        item[field] = max(item.get(field, 0), n)


def _finish_usage(stats, usage, engine, source):
    for item in usage.values():
        stats['usage_requests'] += 1
        stats['usage_sources'][source] += 1
        stats['tokens'].update(item)
        if 'input_tokens' not in item:
            stats['quality']['requests_without_input_usage'] += 1
            continue
        context = item['input_tokens']
        if engine == 'claude':
            # Claude input excludes both cache categories. Codex input already
            # includes cached input, so adding cache fields there double-counts.
            context += item.get('cache_read_input_tokens', 0) + item.get('cache_creation_input_tokens', 0)
        stats['context_sum'] += context
        stats['context_requests'] += 1


def _arguments(payload):
    value = payload.get('arguments', payload.get('input', {}))
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def _tool(stats, payload, t, scope, seen, pending, engine):
    call_id = payload.get('call_id') or payload.get('id')
    if not isinstance(call_id, str) or not call_id:
        stats['quality']['tools_without_id'] += 1
        return False
    key = (scope, call_id)
    if key in seen:
        return False
    seen.add(key)
    name = payload.get('name')
    name = name if isinstance(name, str) else '?'
    stats['tool_calls'][name] += 1
    pending[key] = (name, t)
    args = _arguments(payload) if engine == 'codex' else payload.get('input') or {}
    if not isinstance(args, dict):
        args = {}
    if name in ('Read', 'read_file'):
        path = args.get('file_path') or args.get('path')
        if isinstance(path, str):
            stats['reads'][path] += 1
    if name in ('Bash', 'bash', 'exec_command', 'shell_command'):
        cmd = args.get('command') or args.get('cmd')
        if isinstance(cmd, str):
            try:
                words = shlex.split(cmd)
            except ValueError:
                words = []
            if words:
                # Do not retain environment assignment values or shell arguments.
                head = words[0]
                stats['bash_head']['<assignment>' if '=' in head else Path(head).name] += 1
    return True


def _output(stats, payload, t, scope, pending):
    call_id = payload.get('tool_use_id') or payload.get('call_id')
    if not isinstance(call_id, str):
        return
    name, start = pending.pop((scope, call_id), (None, None))
    if name is None:
        return
    body = payload.get('output', payload.get('content', ''))
    value = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    stats['tool_result_chars'][name] += len(value)
    if t >= start:
        stats['tool_latency'][name].append((t - start).total_seconds())
    if payload.get('is_error') is True:
        stats['tool_errors'][name] += 1


def collect_usage(claude_root, codex_root, *, days=90, now=None, known_skills=(), engines=('claude', 'codex')):
    if days < 0:
        raise ValueError('days must be nonnegative; 0 means all available records')
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days) if days else datetime.min.replace(tzinfo=timezone.utc)
    known = {canonical_skill(s) for s in known_skills}
    result = {engine: _new_stats() for engine in ('claude', 'codex')}
    seen_tools, pending, seen_users = set(), {}, set()
    claude_usage, native_usage, fallback_usage = {}, {}, {}

    for engine, root in [('claude', Path(claude_root)), ('codex', Path(codex_root))]:
        stats = result[engine]
        if engine not in engines:
            continue
        for path in sorted(root.rglob('*.jsonl')):
            stats['quality']['files_scanned'] += 1
            scope = str(path)
            user_events, user_messages = [], []
            local_native, local_fallback, legacy_positions = {}, {}, {}
            previous_total = None
            legacy_sequence = 0
            current_legacy_key = None
            first_native = None
            for number, rec in records(path, stats['quality']):
                t = timestamp(rec.get('timestamp'))
                if t is None:
                    stats['quality']['records_without_timestamp'] += 1
                    continue
                meta = rec.get('metadata') or {}
                if isinstance(meta, dict) and meta.get('inherited_user_message'):
                    continue
                if not isinstance(meta, dict):
                    meta = {}
                kind = rec.get('type')
                payload = rec.get('payload') or {}
                if not isinstance(payload, dict):
                    continue
                # Read the identity and cumulative cursor even outside the window:
                # a session can resume today in an old directory, and repeated
                # historical totals must not become a new request at the cutoff.
                if engine == 'codex' and kind == 'session_meta':
                    identity = payload.get('id')
                    scope = identity if isinstance(identity, str) and identity else scope
                if engine == 'codex' and kind == 'token_usage_record':
                    native_fields = payload.get('usage')
                    if isinstance(payload.get('response_id'), str) and isinstance(native_fields, dict) and any(integer(v) for v in native_fields.values()):
                        if first_native is None:
                            first_native = number
                legacy_key = None
                if engine == 'codex' and kind == 'event_msg' and payload.get('type') == 'token_count':
                    info = payload.get('info') or {}
                    if isinstance(info, dict) and isinstance(info.get('total_token_usage'), dict):
                        total = info['total_token_usage']
                        fingerprint = tuple((k, total[k]) for k in ('input_tokens', 'output_tokens', 'total_tokens') if integer(total.get(k)))
                        if fingerprint and fingerprint != previous_total:
                            legacy_sequence += 1
                            legacy_key = (scope, legacy_sequence)
                            current_legacy_key = legacy_key
                        previous_total = fingerprint or previous_total
                if not cutoff <= t <= now:
                    continue
                if engine == 'claude':
                    identity = rec.get('sessionId') or rec.get('session_id')
                    scope = identity if isinstance(identity, str) and identity else scope
                    message = rec.get('message') or {}
                    if not isinstance(message, dict):
                        continue
                    content = message.get('content')
                    if kind == 'assistant':
                        usage = message.get('usage')
                        if isinstance(usage, dict) and usage:
                            identity = message.get('id') or rec.get('requestId') or rec.get('uuid')
                            if not isinstance(identity, str):
                                identity = (str(path), number)
                            _merge_usage(claude_usage, (scope, identity), usage, engine)
                        for block in content if isinstance(content, list) else []:
                            if not isinstance(block, dict) or block.get('type') != 'tool_use':
                                continue
                            fresh = _tool(stats, block, t, ('claude', scope), seen_tools, pending, engine)
                            if fresh and block.get('name') == 'Skill':
                                inp = block.get('input') or {}
                                skill = inp.get('skill') if isinstance(inp, dict) else None
                                if isinstance(skill, str):
                                    _hit(stats, skill, 'model', t, known)
                    elif kind == 'user' and not rec.get('isMeta'):
                        identity = rec.get('uuid')
                        if not isinstance(identity, str):
                            identity = (str(path), number)
                        key = ('claude', scope, identity)
                        if key not in seen_users:
                            seen_users.add(key)
                            match = COMMAND.match(text_blocks(content))
                            if match:
                                _hit(stats, match.group(1), 'user', t, known)
                        for block in content if isinstance(content, list) else []:
                            if isinstance(block, dict) and block.get('type') == 'tool_result':
                                _output(stats, block, t, ('claude', scope), pending)
                else:
                    if kind == 'token_usage_record':
                        identity = payload.get('response_id')
                        if isinstance(identity, str) and identity:
                            native_scope = payload.get('thread_id') or payload.get('session_id')
                            if not isinstance(native_scope, str):
                                native_scope = scope
                            _merge_usage(local_native, (native_scope, identity), payload.get('usage'), engine)
                        else:
                            stats['quality']['native_usage_without_response_id'] += 1
                    elif legacy_key or (kind == 'event_msg' and payload.get('type') == 'token_count' and current_legacy_key in local_fallback):
                        legacy_key = legacy_key or current_legacy_key
                        usage = (payload.get('info') or {}).get('last_token_usage')
                        if isinstance(usage, dict) and usage:
                            _merge_usage(local_fallback, legacy_key, usage, engine)
                            legacy_positions.setdefault(legacy_key, number)
                    if kind == 'event_msg' and payload.get('type') == 'user_message':
                        identity = payload.get('id') or rec.get('ordinal') or number
                        if not isinstance(identity, (str, int)):
                            identity = number
                        user_events.append((payload.get('message', ''), t, identity))
                    elif kind == 'response_item':
                        retained = meta.get('retained_source') or {}
                        origin = retained.get('id', {}) if isinstance(retained, dict) else {}
                        origin = origin if isinstance(origin, dict) else {}
                        retained_id = origin.get('message_id') if origin.get('role') == 'user' else None
                        actual_user = meta.get('client_authored') is not False or isinstance(retained_id, str)
                        if payload.get('role') == 'user' and actual_user:
                            content = payload.get('content')
                            blocks = content if isinstance(content, list) else [dict(type='input_text', text=content)]
                            for index, block in enumerate(blocks):
                                text = text_blocks([block])
                                if not SKILL.match(text):
                                    continue
                                skill = canonical_skill(SKILL.match(text).group(1))
                                identity = payload.get('id') or rec.get('ordinal') or number
                                if not isinstance(identity, (str, int)):
                                    identity = number
                                identity = ('retained', retained_id, skill) if isinstance(retained_id, str) else (identity, skill)
                                user_messages.append((text, t, identity))
                        if payload.get('type') in ('function_call', 'custom_tool_call'):
                            _tool(stats, payload, t, ('codex', scope), seen_tools, pending, engine)
                        elif payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
                            _output(stats, payload, t, ('codex', scope), pending)
            if engine == 'codex':
                for key, usage in local_native.items():
                    _merge_usage(native_usage, key, usage, engine)
                for key, usage in local_fallback.items():
                    if first_native is None or legacy_positions[key] < first_native:
                        _merge_usage(fallback_usage, key, usage, engine)
                    else:
                        # No request ID links this snapshot to a native response.
                        # Do not guess an additional request; expose the coverage.
                        stats['quality']['legacy_snapshots_after_native'] += 1
                event_mirrors = defaultdict(list)
                stable_event_ids = set()
                for source, candidates in [('event', user_events), ('item', user_messages)]:
                    for text, t, identity in candidates:
                        if not isinstance(text, str):
                            continue
                        match = SKILL.match(text)
                        if not match:
                            continue
                        skill = canonical_skill(match.group(1))
                        if isinstance(identity, tuple) and identity[0] == 'retained':
                            key = ('codex', identity)
                        else:
                            key = ('codex', scope, source, identity)
                        if key in seen_users:
                            continue
                        seen_users.add(key)
                        origin = identity
                        if isinstance(identity, tuple):
                            origin = identity[1] if identity[0] == 'retained' else identity[0]
                        origin = origin if isinstance(origin, str) else None
                        mirror = (scope, t, skill)
                        candidates = event_mirrors[mirror]
                        if source == 'item':
                            if origin is not None and (scope, origin, skill) in stable_event_ids:
                                if origin in candidates:
                                    candidates.remove(origin)
                                continue
                            paired = False
                            for index, event_origin in enumerate(candidates):
                                if origin is None or event_origin is None or origin == event_origin:
                                    candidates.pop(index)
                                    stats['quality']['user_mirror_time_fallback'] += 1
                                    paired = True
                                    break
                            if paired:
                                continue
                        _hit(stats, skill, 'user', t, known)
                        if source == 'event':
                            candidates.append(origin)
                            if origin is not None:
                                stable_event_ids.add((scope, origin, skill))
    _finish_usage(result['claude'], claude_usage, 'claude', 'assistant_message_usage')
    _finish_usage(result['codex'], native_usage, 'codex', 'token_usage_record')
    _finish_usage(result['codex'], fallback_usage, 'codex', 'legacy_token_count')
    for engine, stats in result.items():
        n = stats['context_requests']
        stats['avg_context_tokens'] = stats.pop('context_sum') / n if n else None
        stats['context_requests'] = n
        shell_names = ('Bash', 'bash') if engine == 'claude' else ('exec_command', 'shell_command')
        shell_count = sum(stats['tool_calls'][k] for k in shell_names)
        calls = sum(stats['tool_calls'].values())
        stats['bash_share'] = shell_count / calls if calls else None
        stats['cd_share'] = stats['bash_head']['cd'] / shell_count if shell_count else None
        stats['quality']['shell_commands_with_visible_arguments'] = sum(stats['bash_head'].values())
        for field in ['skill_hits', 'last', 'tool_calls', 'tool_result_chars', 'tool_errors', 'reads', 'bash_head', 'tokens', 'quality', 'usage_sources']:
            stats[field] = dict(stats[field])
        stats['skill_sources'] = {k: dict(v) for k, v in stats['skill_sources'].items()}
        stats['tool_latency'] = dict(stats['tool_latency'])
    return result
