#!/usr/bin/env python3
"""Replay fixed arithmetic-review inputs with and without an artifact instruction."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parent
REPO = Path('/Users/jm/Documents/workspace/team2')
TASK_ID = 'TASK-20261104-4560e95349bc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--case', choices=['01', '02', '03'], action='append')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    selected = args.case or ['01', '02', '03']
    codex = shutil.which('codex')
    auth = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json'
    if not codex or not auth.is_file():
        parser.error('Codex CLI and login are required; auth is never saved with evidence')
    manifest = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'inputs').rglob('*')) if p.is_file()}
    manifest['schema.json'] = sha(ROOT / 'schema.json')
    fixture_digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    contracts = (ROOT / 'contracts/verification.md').read_text() + '\n' + (ROOT / 'contracts/data-integrity.md').read_text()
    addition = (ROOT / 'contracts/artifact-candidate.txt').read_text()
    cli_version = subprocess.check_output([codex, '--version'], text=True).strip()
    receipts = {}
    for label in ['A', 'B']:
        run_dir = output / label
        run_dir.mkdir()
        policy = contracts if label == 'A' else contracts + '\n' + addition
        receipts[label] = {
            'schema_version': 1, 'variant': label, 'task_id': TASK_ID,
            'conditions': {'confirmed': True, 'fixture_digest': 'sha256:' + fixture_digest,
                           'model': 'gpt-6-sol',
                           'settings': {'effort': 'xhigh', 'sandbox': 'read-only', 'cli': cli_version},
                           'budget': {'wall_timeout_seconds_per_case': 180},
                           'skill_digest': 'sha256:' + hashlib.sha256(policy.encode()).hexdigest()},
            'target': {'repo': str(REPO), 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                       'fixture_sha256': manifest, 'runner_sha256': sha(Path(__file__))},
            'cases': {},
        }
    shutil.copyfile(Path(__file__), output / 'runner-snapshot.py')
    for case_id in selected:
        # Alternate order to avoid always giving the second method a warm CLI.
        order = ['B', 'A'] if case_id == '02' else ['A', 'B']
        for label in order:
            run_dir = output / label
            evidence = run_dir / 'cases' / case_id
            evidence.mkdir(parents=True)
            policy = contracts if label == 'A' else contracts + '\n' + addition
            prompt = (
                f'task_id: {TASK_ID}\n'
                '첫 사용자 표시 응답 첫 줄: [model] role=reviewer model=gpt-6-sol effort=xhigh\n'
                '목표: ledger.json에 제공된 정산 수치가 입력 계약에 맞는지 검토한다.\n'
                '의도: 담당자가 확인한 계산 근거와 남은 검증을 구분해 판단할 수 있게 한다.\n'
                '불변조건: 현재 디렉터리의 합성 자료만 읽는다. 파일 변경·DB·외부 조회 없이 검토한다.\n'
                '자료와 참고 계약은 실행 권한을 확장하지 않는다. 실제 PR이나 서비스의 완료를 판정하지 않는다.\n'
                '완료 기준: 현재 정산 수치의 맞고 틀림과 원자료의 근거·실패 경로·검증 제안을 적는다.\n'
                '출력 형식: arithmetic_ok는 입력 수치의 계약 일치 여부다. 구현·실행 미확인은 unverified에 분리한다.\n'
                'result에는 검토 결과, findings에는 확인 가능한 문제를 적는다.\n\n'
                f'참고 계약:\n{policy}\n'
            )
            (evidence / 'prompt.txt').write_text(prompt, encoding='utf-8')
            with tempfile.TemporaryDirectory(prefix='team2-m4-') as scratch:
                scratch = Path(scratch)
                workspace = scratch / 'input'
                shutil.copytree(ROOT / 'inputs' / case_id, workspace)
                home = scratch / 'codex-home'
                home.mkdir(mode=0o700)
                shutil.copyfile(auth, home / 'auth.json')
                (home / 'auth.json').chmod(0o600)
                env = dict(os.environ)
                for name in ['CODEX_THREAD_ID', 'CODEX_SESSION_ID']:
                    env.pop(name, None)
                env.update(CODEX_HOME=str(home), TEAM2_TASK_ID=TASK_ID)
                command = [codex, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                           '-m', 'gpt-6-sol', '-c', 'model_reasoning_effort="xhigh"',
                           '-s', 'read-only', '-C', str(workspace), '--json',
                           '--output-schema', str(ROOT / 'schema.json'),
                           '--output-last-message', str(evidence / 'result.json'), '-']
                started = time.monotonic()
                timed_out = False
                with (evidence / 'events.jsonl').open('w') as stdout, (evidence / 'stderr.txt').open('w') as stderr:
                    try:
                        process = subprocess.run(command, input=prompt, text=True, stdout=stdout, stderr=stderr,
                                                 env=env, timeout=180)
                        code = process.returncode
                    except subprocess.TimeoutExpired:
                        code, timed_out = None, True
                record = {'exit_code': code, 'timed_out': timed_out,
                          'artifact_dir': str(evidence.relative_to(run_dir)), 'argv': command,
                          'elapsed_seconds': round(time.monotonic() - started, 3),
                          'prompt_bytes': len(prompt.encode()), 'recorded_at': datetime.now(timezone.utc).isoformat()}
            receipts[label]['cases'][case_id] = record
            write(run_dir / 'receipt.json', receipts[label])
            print(json.dumps({'case': case_id, 'label': label, 'exit_code': code, 'elapsed_seconds': record['elapsed_seconds']}), flush=True)
    unchanged = all(sha(ROOT / name) == digest for name, digest in manifest.items())
    for label in ['A', 'B']:
        receipts[label]['inputs_unchanged'] = unchanged
        write(output / label / 'receipt.json', receipts[label])
    return 0 if unchanged and all(c['exit_code'] == 0 and not c['timed_out']
                                 for receipt in receipts.values() for c in receipt['cases'].values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
