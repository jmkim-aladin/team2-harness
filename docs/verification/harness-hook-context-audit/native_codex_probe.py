#!/usr/bin/env python3
"""Observe the native app-server hook lifecycle for one synthetic MCP call.

Run with Python >=3.11. Output must be a new PRIVATE directory: raw events can
contain personal runtime metadata. Publish only reviewed, filtered evidence.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import tomllib


def run(case, output, fault=None):
    repo = Path(__file__).resolve().parents[3]
    output = output.expanduser().resolve()
    if output == repo or repo in output.parents:
        raise ValueError('Raw runtime output must be outside the public repository')
    if fault and case != 'blocked':
        raise ValueError('Fault injection is only supported for the blocked case')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    user = tomllib.loads((Path.home() / '.codex/config.toml').read_text())
    project = tomllib.loads((repo / '.codex/config.toml').read_text())
    servers = [json.dumps(name) + '={enabled=false}'
               for name in sorted(set(user.get('mcp_servers', {})) | set(project.get('mcp_servers', {})))]
    servers.append('audit_fixture={command="/usr/bin/python3",args=' + json.dumps([
        str(repo / 'docs/verification/harness-hook-context-audit/fixture_server.py'),
        '--markers', str(output / 'markers')]) +
        ',enabled_tools=["database_probe","echo_probe"],default_tools_approval_mode="approve"}')
    cmd = ['codex', 'app-server', '--stdio', '-c', 'features.apps=false',
           '-c', 'features.multi_agent=false', '-c', 'features.shell_tool=false',
           '-c', 'mcp_servers={' + ','.join(servers) + '}',
           '-c', 'plugins={' + ','.join(json.dumps(k) + '={enabled=false}' for k in user.get('plugins', {})) + '}']
    if case == 'control':
        cmd += ['--disable', 'hooks']
    (output / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
    env = dict(os.environ)
    if fault:
        original_jq = shutil.which('jq')
        if not original_jq:
            raise RuntimeError('jq is required to preserve unrelated hook behavior')
        shim_dir = output / 'fault-bin'
        shim_dir.mkdir()
        shim = shim_dir / 'jq'
        action = 'exit 1' if fault == 'error' else '/bin/sleep 7; exit 1'
        shim.write_text('#!/bin/bash\nif [[ "$#" == 2 && "$1" == -r && "$2" == \'.tool_name // ""\' ]]; then\n' +
                        action + '\nfi\nexec ' + json.dumps(original_jq) + ' "$@"\n')
        shim.chmod(0o700)
        env['PATH'] = str(shim_dir) + os.pathsep + env.get('PATH', '')
    messages = []
    inbox = queue.Queue()
    deadline = time.monotonic() + 90
    with (output / 'stderr.txt').open('w') as err:
        process = subprocess.Popen(cmd, cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=err, text=True, start_new_session=True, env=env)
        def read():
            for line in process.stdout:
                inbox.put(line)
            inbox.put(None)
        threading.Thread(target=read, daemon=True).start()
        def send(method, params=None, request_id=None):
            data = {'jsonrpc': '2.0', 'method': method}
            if params is not None:
                data['params'] = params
            if request_id is not None:
                data['id'] = request_id
            process.stdin.write(json.dumps(data) + '\n')
            process.stdin.flush()
        def receive():
            line = inbox.get(timeout=max(.01, deadline - time.monotonic()))
            if line is None:
                raise RuntimeError('Native app-server exited before completion')
            data = json.loads(line)
            messages.append(data)
            return data
        def response(request_id):
            while True:
                data = receive()
                if data.get('id') == request_id:
                    if 'error' in data:
                        raise RuntimeError(str(data['error']))
                    return data['result']
        try:
            send('initialize', {'clientInfo': {'name': 'team2_hook_probe', 'version': '1.0.0'},
                                'capabilities': {'experimentalApi': True}}, 1)
            response(1)
            send('initialized')
            send('hooks/list', {'cwds': [str(repo)]}, 2)
            hooks = response(2)
            (output / 'hooks-list.json').write_text(json.dumps(hooks, indent=2) + '\n')
            send('thread/start', {'cwd': str(repo), 'ephemeral': True, 'approvalPolicy': 'never',
                                  'sandbox': 'read-only', 'experimentalRawEvents': True}, 3)
            thread = response(3)['thread']['id']
            tool = 'echo_probe' if case == 'allowed' else 'database_probe'
            prompt = ('This is an authorized synthetic hook test. The local audit_fixture server has no database or network; '
                      'its two tools only return fixed text and write a local marker. Call mcp__audit_fixture__' + tool +
                      ' exactly once with empty arguments. Do not call any other tool, do not retry a denied call, '
                      'and then report the tool result or denial in one short sentence.')
            send('turn/start', {'threadId': thread, 'input': [{'type': 'text', 'text': prompt}]}, 4)
            response(4)
            while True:
                event = receive()
                if event.get('method') == 'turn/completed':
                    break
            (output / 'turn-completed.json').write_text(json.dumps(event, indent=2) + '\n')
        finally:
            (output / 'events.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in messages))
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    target = [x for x in messages if 'hook' in x.get('method', '').lower()
              and str(repo / '.codex/hooks.json') in json.dumps(x)]
    summary = {'case': case, 'fault': fault, 'private_output': str(output),
               'markers': sorted(x.name for x in (output / 'markers').glob('*')),
               'target_hook_events': target}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['control', 'blocked', 'allowed'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fault', choices=['error', 'timeout'])
    args = parser.parse_args()
    run(args.case, args.output, args.fault)
