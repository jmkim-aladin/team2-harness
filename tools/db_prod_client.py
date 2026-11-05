#!/usr/bin/env python3
"""Client for the one installed production gateway; no credentials or DB driver."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

INSTALL = Path(__file__).resolve().parent
sys.path.insert(0, str(INSTALL))
STATE = Path.home() / "Library/Application Support/team2-db"
SOCKET = str(Path("/tmp") / ("team2-db-" + str(os.getuid())) / "query.sock")
STOP_MARKERS = STATE / "stop.d"

SAFE_CLIENT_ERRORS = frozenset((
    "gateway_restart_required", "result_delivery_incomplete", "result_delivery_invalid",
    "result_digest_mismatch", "incomplete_gateway_response", "response_too_large",
    "result_unavailable_or_stopped", "result_commit_pending", "result_offset_mismatch",
    "v2_review_required", "approved_digest_mismatch", "operator_terminal_required",
    'job_unknown_or_expired', 'result_identity_mismatch', 'result_ack_unconfirmed',
))


def require_current_gateway(*, require_jobs=False, require_csv=False):
    from db_prod_gateway import current_source_fingerprint
    status = rpc(dict(action="status"))
    if not status.get("ok") or status.get("runtime_fingerprint") != current_source_fingerprint():
        raise RuntimeError("gateway_restart_required")
    if require_jobs and not {'detached_jobs','repeatable_fetch','durable_ack'} <= set(status.get('capabilities', [])):
        raise RuntimeError('gateway_restart_required')
    if require_csv and 'csv_export' not in status.get('capabilities', []):
        raise RuntimeError('gateway_restart_required')


def safe_client_error(error):
    token = error.args[0] if error.args else None
    return token if isinstance(token, str) and token in SAFE_CLIENT_ERRORS else "client_request_failed"

def rpc(request, timeout=75):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(SOCKET)
        client.sendall(json.dumps(request, ensure_ascii=False).encode() + b"\n")
        data = bytearray()
        while not data.endswith(b"\n"):
            part = client.recv(65536)
            if not part:
                raise RuntimeError("incomplete_gateway_response")
            data.extend(part)
            if len(data) > 12 * 1024 * 1024:
                raise RuntimeError("response_too_large")
        return json.loads(data)


def display_review(review):
    # JSON escaping prevents SQL literals containing terminal controls from
    # hiding part of the approval screen. The complete string remains visible.
    for key in ("request_id", "target", "database", "owner", "timeout", "max_rows", "max_bytes",
                "output_limit_unit", "resource_max_bytes", "read_access_basis", "indirect_object_dependencies_verified",
                "profile_fingerprint", "observer_fingerprint", "host_tag", "digest"):
        print(key + ": " + json.dumps(review.get(key), ensure_ascii=False))
    print("\n사용자 SQL 전문(JSON 문자열 표기):")
    print(json.dumps(review["sql"], ensure_ascii=False))
    print("\n연결 준비 SQL(JSON 표기):")
    print(json.dumps(review["control_sql"]["setup_sql"], ensure_ascii=False))
    print("\n조건부 종료 확인 SQL(JSON 표기):")
    print(json.dumps(review["control_sql"]["observer_sql"], ensure_ascii=False))
    print("실행 조건: " + str(review["control_sql"].get("observer_when", "cancellation_or_uncertain_completion_only")))
    if review.get("api_version") == 2:
        for key in ("api_version", "runtime_fingerprint", "selected_actions", "stop_snapshot",
                    "envelope_digest", "approval_digest", "expires_at", "output_mode",
                    'observer_limits', 'memory_limit_scope'):
            print(key + ": " + json.dumps(review.get(key), ensure_ascii=False))
        export = ""
        if review.get("output_mode") == "csv":
            # The complete export contract is part of what the user approves.
            print("export_spec: " + json.dumps(review["export_spec"], ensure_ascii=False))
            print("export_spec_digest: " + json.dumps(review["export_spec_digest"]))
            print("저장 위치: " + review["export_spec"]["artifact_directory"])
            export = " + 결과를 위 저장 위치에 CSV로 저장(SQL 재실행 없음)"
        if "release_emergency_stop" in review["selected_actions"]:
            print("승인 동작: 표시한 긴급 중단을 해제하고 이 SQL을 1회 실행" + export)
        elif "resume_current_stop" in review["selected_actions"]:
            print("승인 동작: 표시한 중단을 해제하고 이 SQL을 1회 실행" + export)
        else:
            print("승인 동작: 표시한 SQL을 1회 실행 (중단 해제 없음)" + export)


def display_recovery_review(review):
    """Render the complete observer-only recovery batch before approval."""

    for key in ("recovery_request_id", "run_id", "epoch", "target", "database", "host_tag", "profile_digest",
                "timeout", "max_rows", "max_bytes", "digest"):
        print(key + ": " + json.dumps(review.get(key), ensure_ascii=False))
    print("\n운영 세션 종료 확인 SQL 전문(JSON 문자열 표기):")
    print(json.dumps(review["observer_sql"], ensure_ascii=False))


def emergency_stop(*, persistent=True):
    # No daemon, SQL worker, socket, UI prompt or audit write is a prerequisite.
    sys.path.insert(0, str(INSTALL))
    from db_prod_watchdog import StopMarkerError, create_stop_marker
    from db_query_control import Store
    try:
        marker = create_stop_marker(STOP_MARKERS, reason="independent_emergency_stop" if persistent else "operator_cancel")
    except StopMarkerError as error:
        raise RuntimeError(str(error)) from None
    stopped = False
    try:
        store = Store(STATE / "control.sqlite3")
        if persistent:
            store.stop("independent_emergency_stop")
        else:
            store.cancel()
        stopped = True
    except Exception:
        # Watchdogs independently read the marker, even if the daemon is frozen.
        pass
    result = dict(ok=True, halted=True, stop_marker=marker, latch_persisted=True,
                coordinator_updated=stopped, session_closed=False,
                status="blocked_cancellation_requested_check_status")
    if not persistent:
        try:
            state = rpc(dict(action="settle_cancel"), timeout=1)
            if state.get("ok"):
                result.update({key: state[key] for key in ("halted", "active", "phase", "ready_for_new_request")})
                if state.get("ready_for_new_request"):
                    result["status"] = "cancel_completed_ready_for_new_request"
                    result["session_closed"] = True
                    result["request_marker"] = result.pop("stop_marker")
                # latch_persisted records acknowledgement of the request;
                # latch_active describes the current state after settlement.
                result["latch_active"] = bool(state.get("stop_markers"))
        except Exception:
            pass  # The durable marker remains usable without a live daemon.
    return result


def initialize():
    if os.geteuid() == 0:
        raise RuntimeError("run_as_current_user")
    for path in (STATE, Path(SOCKET).parent, STOP_MARKERS):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
            raise RuntimeError("unsafe_runtime_directory")
    helper = STATE / "db-prod-keychain"
    compiled = subprocess.run(["/usr/bin/swiftc", str(INSTALL / "db_prod_keychain.swift"), "-o", str(helper)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if compiled.returncode:
        raise RuntimeError("keychain_helper_compile_failed")
    os.chmod(helper, 0o700)
    config = STATE / "config.json"
    if not config.exists():
        fd = os.open(str(config), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(dict(allowed_uids=[os.getuid()], targets={
                target: dict(enabled=True, read_only_verified=False) for target in ("lego-prod", "cool-prod")
            }), stream)
    sys.path.insert(0, str(INSTALL))
    from db_query_control import Store
    from db_prod_watchdog import StopMarkerError, create_stop_marker, list_stop_markers
    path = STATE / "control.sqlite3"
    if not path.exists():
        Store.initialize(path)
    try:
        if not list_stop_markers(STOP_MARKERS):
            create_stop_marker(STOP_MARKERS, reason="initial_halt")
    except StopMarkerError as error:
        raise RuntimeError(str(error)) from None
    return dict(ok=True, initialized=True, database_connected=False, halted=True)


def start():
    try:
        return rpc(dict(action="status"), timeout=1)
    except Exception:
        pass
    # A daemon uses no database or credentials at startup. No auto resume.
    subprocess.Popen([sys.executable, "-I", str(INSTALL / "db_prod_gateway.py"), "serve"],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True, env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "HOME": str(Path.home())})
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            return rpc(dict(action="status"), timeout=0.5)
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("gateway_start_failed")


def export_columns(value):
    columns = []
    for item in value.split(","):
        name, _, kind = item.strip().partition(":")
        if not name or kind not in ("string", "number", "boolean"):
            raise argparse.ArgumentTypeError("name:type 목록 (type은 string|number|boolean)")
        columns.append(dict(name=name, type=kind))
    return columns


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("양수를 입력하세요")
    return number


def positive_limit(value):
    if value == "unlimited":
        return None
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("양수 또는 unlimited를 입력하세요")
    return number


def fetch_output(result):
    if not result.get('ok') or not result.get('session_closed') or result.get('already_submitted'):
        return result
    output = bytearray()
    while True:
        chunk = rpc(dict(action='fetch', run_id=result['run_id'], offset=len(output)))
        if not chunk.get('ok') and chunk.get('status') in SAFE_CLIENT_ERRORS:
            raise RuntimeError(chunk['status'])
        if not chunk.get('ok') or chunk.get('offset') != len(output):
            raise RuntimeError('result_delivery_incomplete')
        output.extend(base64.b64decode(chunk['data_base64'], validate=True))
        if len(output) > result['output_bytes'] or len(output) != chunk['next_offset']:
            raise RuntimeError('result_delivery_invalid')
        if chunk['final']:
            break
    if len(output) != result['output_bytes'] or hashlib.sha256(output).hexdigest() != result['output_sha256']:
        raise RuntimeError('result_digest_mismatch')
    result['output'] = output.decode('utf-8', errors='replace')
    return result


def receive_job(request_id, *, wait=True):
    deadline = time.monotonic()+75
    while True:
        status = rpc(dict(action='job_status', request_id=request_id))
        if status.get('ok') and status.get('job_state') not in (
                'completed','failed','unknown','recovery_required','preview','preview_lost',
                'admitting','starting','dispatching','running','finishing','unconfirmed'):
            raise RuntimeError('result_delivery_invalid')
        if (not status.get('ok') or status.get('job_state') in ('completed','failed','unknown','recovery_required','preview','preview_lost')
                or not wait or time.monotonic() >= deadline):
            break
        time.sleep(.1)
    if status.get('result_state') != 'available':
        return status
    identity = dict(request_id=request_id, result_digest=status['result_digest'], epoch=status['epoch'])
    length, output = status['output_bytes'], bytearray()
    if type(length) is not int or not 0 <= length <= 32*1024*1024:
        raise RuntimeError('result_delivery_invalid')
    while True:
        chunk = rpc(dict(action='fetch_result', offset=len(output), **identity))
        if (not chunk.get('ok') or any(chunk.get(k) != v for k,v in identity.items())
                or type(chunk.get('offset')) is not int or chunk['offset'] != len(output)):
            raise RuntimeError('result_delivery_invalid')
        data = base64.b64decode(chunk['data_base64'], validate=True)
        if len(data) > 2048 or len(output)+len(data) > length or chunk.get('next_offset') != len(output)+len(data):
            raise RuntimeError('result_delivery_invalid')
        output.extend(data)
        if chunk.get('final') is True:
            break
        if not data:
            raise RuntimeError('result_delivery_incomplete')
    if len(output) != length or hashlib.sha256(output).hexdigest() != status['output_sha256']:
        raise RuntimeError('result_digest_mismatch')
    # A lost ack reply may be repeated; never submit SQL again here.
    try:
        ack = rpc(dict(action='ack_result', **identity))
    except (OSError, RuntimeError, ValueError):
        ack = rpc(dict(action='ack_result', **identity))
    if not ack.get('ok'):
        raise RuntimeError('result_ack_unconfirmed')
    return dict(status, result_state='delivered', output=output.decode('utf-8',errors='replace'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ('prepare', 'preview'):
        prepare = sub.add_parser(name, help='SQL은 stdin; preview는 v2 접속 없는 재개 포함 검토')
        prepare.add_argument('--target', choices=('lego-prod', 'cool-prod'), required=True)
        prepare.add_argument('--database', required=True)
        prepare.add_argument('--timeout', type=float, required=True)
        prepare.add_argument('--max-rows', type=positive_limit, default=None, help='기본 unlimited')
        prepare.add_argument('--max-bytes', type=positive_limit,
                             default=32*1024*1024 if name == 'preview' else None,
                             help='preview 기본/최대 32MiB; prepare 기본 unlimited')
        if name == 'preview':
            prepare.add_argument('--output', choices=('memory', 'csv'), default='memory',
                                 help='csv: stdin은 SELECT 하나, 결과를 승인된 위치에 CSV로 저장')
            prepare.add_argument('--columns', type=export_columns, help='csv 컬럼 name:type,... (순서 고정)')
            prepare.add_argument('--purpose', help='csv 용도 (manifest에 기록)')
            prepare.add_argument('--max-file-bytes', type=positive_int, help='csv 파일 byte 상한 (필수)')
            prepare.add_argument('--max-record-bytes', type=positive_int, default=1 << 20, help='csv 한 행 byte 상한')
            prepare.add_argument('--max-source-bytes', type=positive_int, help='sqlcmd 출력 byte 상한 (기본: 파일 상한에서 계산)')
    for name in ("review", "approve", "execute", 'run', 'job-status', 'result'):
        command = sub.add_parser(name)
        command.add_argument("request_id")
        if name in ('approve', 'run'):
            command.add_argument("--from-chat-digest", help="사용자가 이 전문을 명시 승인한 뒤에만 에이전트가 전달")
    sub.add_parser("recovery-prepare")
    recovery_review = sub.add_parser("recovery-review")
    recovery_review.add_argument("request_id")
    recovery_approve = sub.add_parser("recovery-approve")
    recovery_approve.add_argument("request_id")
    recovery_approve.add_argument("--from-chat-digest", help="사용자가 관찰 SQL 전문을 명시 승인한 뒤에만 전달")
    recovery_execute = sub.add_parser("recovery-execute")
    recovery_execute.add_argument("request_id")
    for name in ("init", "start", "status", "stop", "resume", "emergency-stop"):
        sub.add_parser(name)
    args = parser.parse_args()
    if args.action == 'preview':
        csv_options = (args.columns, args.purpose, args.max_file_bytes, args.max_source_bytes)
        if args.output == 'csv' and None in csv_options[:3]:
            parser.error('--output csv에는 --columns, --purpose, --max-file-bytes가 필요합니다')
        if args.output != 'csv' and any(value is not None for value in csv_options):
            parser.error('CSV 옵션은 --output csv와 함께만 사용합니다')
    try:
        if args.action in ("prepare", "approve", "execute", 'preview', 'run'):
            require_current_gateway(require_jobs=args.action in ('preview','run'),
                                    require_csv=args.action == 'preview' and args.output == 'csv')
        if args.action in ("emergency-stop", "stop"):
            result = emergency_stop(persistent=args.action == "emergency-stop")
        elif args.action == "init":
            result = initialize()
        elif args.action == "start":
            result = start()
        elif args.action in ("approve", "review"):
            result = rpc(dict(action="review", request_id=args.request_id))
            if not result.get("ok"):
                print(json.dumps(result, ensure_ascii=False)); return 1
            review = result["review"]
            display_review(review)
            if args.action == "review":
                return 0
            expected = "APPROVE " + review["digest"][:12]
            source = "human-terminal"
            if args.from_chat_digest:
                if args.from_chat_digest != review["digest"]:
                    raise RuntimeError("approved_digest_mismatch")
                source = "explicit-user-chat"
            else:
                if not sys.stdin.isatty():
                    raise RuntimeError("operator_terminal_required")
                print("\n위 사용자 SQL과 제어 SQL을 이 조건으로 1회 실행합니다.")
                if input("승인하려면 " + expected + " 입력: ") != expected:
                    print("승인하지 않았습니다. DB 연결 없음."); return 1
            result = rpc(dict(action="approve", request_id=args.request_id, digest=review["digest"], approval_source=source))
        elif args.action in ("recovery-approve", "recovery-review"):
            result = rpc(dict(action="recovery_review", recovery_request_id=args.request_id))
            if not result.get("ok"):
                print(json.dumps(result, ensure_ascii=False)); return 1
            review = result["review"]
            display_recovery_review(review)
            if args.action == "recovery-review":
                return 0
            expected = "APPROVE " + review["digest"][:12]
            source = "human-terminal"
            if args.from_chat_digest:
                if args.from_chat_digest != review["digest"]:
                    raise RuntimeError("approved_digest_mismatch")
                source = "explicit-user-chat"
            else:
                if not sys.stdin.isatty():
                    raise RuntimeError("operator_terminal_required")
                print("\n위 운영 세션 종료 확인 SQL 전문을 이 조건으로 1회 실행합니다.")
                if input("승인하려면 " + expected + " 입력: ") != expected:
                    print("승인하지 않았습니다. DB 연결 없음."); return 1
            result = rpc(dict(action="recovery_approve", recovery_request_id=args.request_id,
                              digest=review["digest"], approval_source=source))
        elif args.action == "recovery-prepare":
            result = rpc(dict(action="recovery_prepare"))
        elif args.action == "recovery-execute":
            result = rpc(dict(action="recovery_execute", recovery_request_id=args.request_id))
        elif args.action == "resume":
            if not sys.stdin.isatty():
                raise RuntimeError("operator_terminal_required")
            status = rpc(dict(action="status"))
            if not status.get("ok") or status.get("active") or status.get("phase") != "idle":
                print(json.dumps(status, ensure_ascii=False)); return 1
            expected_epoch = status.get("epoch")
            expected_generation = status.get("stop_generation")
            expected_markers = status.get("stop_markers")
            if (type(expected_epoch) is not int or type(expected_generation) is not int
                    or not isinstance(expected_markers, list)):
                raise RuntimeError("resume_confirmation_unavailable")
            print("확인할 stop marker nonce: " + json.dumps(expected_markers, ensure_ascii=False))
            if input("종료 확인된 idle 상태입니다. 이 nonce만 삭제하려면 RESUME 입력: ") != "RESUME":
                return 1
            # The gateway rechecks the same epoch and exact marker list.  A
            # marker created after this prompt remains and re-latches the store.
            result = rpc(dict(action="resume", expected_epoch=expected_epoch,
                              expected_stop_generation=expected_generation,
                              expected_stop_markers=expected_markers))
        elif args.action in ('prepare', 'preview'):
            sql = sys.stdin.read(1024 * 1024 + 1)
            if len(sql.encode("utf-8")) > 1024 * 1024:
                raise RuntimeError("sql_too_large")
            if args.action == 'preview' and args.output == 'csv':
                export = dict(columns=args.columns, purpose=args.purpose, max_file_bytes=args.max_file_bytes,
                              max_record_bytes=args.max_record_bytes, max_rows=args.max_rows)
                if args.max_source_bytes is not None:
                    export['max_source_bytes'] = args.max_source_bytes
                result = rpc(dict(action="prepare", api_version=2, output_mode='csv', target=args.target,
                                  database=args.database, select_sql=sql, timeout=args.timeout, export=export))
            else:
                result = rpc(dict(action="prepare", api_version=2 if args.action == 'preview' else 1,
                                  target=args.target, database=args.database,
                                  sql=sql, timeout=args.timeout, max_rows=args.max_rows, max_bytes=args.max_bytes))
            if args.action == 'preview' and result.get('ok'):
                display_review(result['review'])
        elif args.action == 'run':
            result = rpc(dict(action='review', request_id=args.request_id))
            if not result.get('ok'):
                print(json.dumps(result, ensure_ascii=False)); return 1
            review = result['review']
            if review.get('api_version') != 2:
                raise RuntimeError('v2_review_required')
            display_review(review)
            source = 'human-terminal'
            if args.from_chat_digest:
                if args.from_chat_digest != review['approval_digest']:
                    raise RuntimeError('approved_digest_mismatch')
                source = 'explicit-user-chat'
            else:
                if not sys.stdin.isatty():
                    raise RuntimeError('operator_terminal_required')
                expected = 'APPROVE ' + review['approval_digest'][:12]
                if input('표시된 모든 동작과 SQL을 1회 승인하려면 '+expected+' 입력: ') != expected:
                    return 1
            try:
                result = rpc(dict(action='approve_submit', request_id=args.request_id,
                    approval_digest=review['approval_digest'], selected_actions=review['selected_actions'], approval_source=source))
            except (OSError, RuntimeError, ValueError):
                # Submission is ambiguous. Resolve the same ID, without replay.
                try:
                    result = receive_job(args.request_id)
                except (OSError, RuntimeError, ValueError):
                    result = dict(ok=False, status='submission_unknown', request_id=args.request_id,
                                  next_action='job-status; never resubmit automatically')
            else:
                if result.get('ok'):
                    result = receive_job(args.request_id)
        elif args.action in ('job-status', 'result'):
            result = receive_job(args.request_id) if args.action == 'result' else rpc(dict(action='job_status', request_id=args.request_id))
        elif args.action == "execute":
            result = fetch_output(rpc(dict(action="execute", request_id=args.request_id)))
        else:
            result = rpc(dict(action=args.action))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.action in ('run', 'result'):
            # ok means the RPC worked; the exit code reports the job (and export) outcome.
            export = result.get('export')
            succeeded = (result.get('ok') and result.get('job_state', 'completed') == 'completed'
                         and (export is None or export.get('state') == 'exported'))
            return 0 if succeeded else 1
        return 0 if result.get("ok") else 1
    except KeyboardInterrupt:
        if args.action in ('run','result'):
            print('결과 대기만 중단했습니다. 작업은 유지됩니다. job-status/result로 이어받거나 stop으로 조회를 중단하세요.',file=sys.stderr)
        else:
            print("취소 요청: 연결 종료를 실행기가 감지합니다. stop/status로 서버 종료 상태를 확인하세요.", file=sys.stderr)
        return 130
    except Exception as error:
        print("실행기 요청 실패: " + safe_client_error(error)
              + ". 비밀값과 서버 오류 원문은 출력하지 않습니다.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
