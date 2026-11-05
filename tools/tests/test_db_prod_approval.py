"""V2 full review and one-use admission; synthetic data and isolated SQLite only."""
import io
import json
from pathlib import Path
import sys
import copy
import socket
import threading
import time
import sqlite3
import subprocess
from dataclasses import replace
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_prod_client import display_review
import db_prod_client
from db_query_control import Denied
from db_prod_watchdog import create_stop_marker, list_stop_markers, remove_stop_markers
from db_prod_gateway import Server, Handler, Gateway
from db_query_control import Supervisor
import test_db_prod_gateway as fixtures
import test_db_prod_transport as transport_fixtures
from db_prod_transport import SqlcmdBackend


class ReviewDisplayTests(unittest.TestCase):
    def test_every_actual_sql_batch_and_observer_condition_are_visible(self):
        review = {'sql': "SELECT N'사용자 SQL 전체' AS value;\n",
                  'control_sql': {'setup_sql': 'SET NOCOUNT ON;\n',
                                  'observer_sql': 'SELECT 0 AS owned_sessions;\n',
                                  'observer_when': 'cancellation_or_uncertain_completion_only'}}
        output = io.StringIO()
        with redirect_stdout(output):
            display_review(review)
        for sql in [review['sql'], review['control_sql']['setup_sql'], review['control_sql']['observer_sql']]:
            self.assertIn(json.dumps(sql, ensure_ascii=False), output.getvalue())
        self.assertIn('cancellation_or_uncertain_completion_only', output.getvalue())
        self.assertNotIn('표시 생략', output.getvalue())


class ApprovalFlowTests(unittest.TestCase):
    setUp = fixtures.GatewayTests.setUp
    tearDown = fixtures.GatewayTests.tearDown

    def preview(self, **changes):
        args = dict(action='prepare', api_version=2, target='lego-prod', database='master',
                    sql=fixtures.PROBE_SQL, timeout=5, max_rows=None)
        args.update(changes)
        return self.gateway.handle(args, self.uid)['review']

    def test_halted_preview_preserves_stop_and_has_no_password_or_connection(self):
        self.store.stop('service_started_requires_operator_resume')
        before = self.store.status()
        review = self.preview()
        self.assertEqual(self.store.status(), before)
        self.assertEqual(review['api_version'], 2)
        self.assertEqual(review['max_bytes'], 32 * 1024 * 1024)
        self.assertEqual(review['selected_actions'], ['execute_once', 'resume_current_stop'])
        self.assertEqual(review['sql'], fixtures.PROBE_SQL)
        self.assertEqual((self.vault.password_reads, fixtures.Backend.started), (0, 0))

    def submit(self, review, **changes):
        args = dict(action='approve_submit', request_id=review['request_id'],
                    approval_digest=review['approval_digest'], selected_actions=review['selected_actions'],
                    approval_source='explicit-user-chat')
        args.update(changes)
        published = []
        result = self.gateway.handle(args, self.uid, publish=published.append)
        if result.get('status') == 'accepted':
            deadline = time.monotonic()+5
            while time.monotonic() < deadline:
                state = self.gateway.handle(dict(action='job_status', request_id=review['request_id']), self.uid)
                if state['job_state'] in ('completed', 'failed', 'recovery_required', 'unknown'):
                    outcome = state.get('outcome') or dict(ok=False, status=state['job_state'])
                    return outcome, [outcome]
                time.sleep(.005)
            self.fail('job did not finish')
        return result, published

    def test_resume_and_query_use_one_approval_and_send_exactly_once(self):
        self.store.stop('service_started_requires_operator_resume')
        review = self.preview()
        sent = []
        with patch.object(fixtures.Backend, 'dispatch', side_effect=lambda sql, limits: sent.append(sql)):
            result, published = self.submit(review)
            again, _ = self.submit(review)
        self.assertTrue(result['ok'])
        self.assertTrue(published[0]['ok'])
        self.assertEqual(sent, [fixtures.PROBE_SQL])
        self.assertEqual((self.vault.password_reads, fixtures.Backend.started), (1, 1))
        self.assertTrue(again['already_submitted'])
        self.assertFalse(self.store.status()['halted'])
        self.assertIsNone(self.store.status()['active'])

    def test_new_stop_after_marker_cleanup_is_preserved_before_activation(self):
        self.store.stop('service_started_requires_operator_resume')
        review = self.preview()
        activate = self.gateway.approvals.activate
        created = []
        def interrupt(ticket, markers):
            created.append(create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop'))
            return activate(ticket, markers)
        with patch.object(self.gateway.approvals, 'activate', side_effect=interrupt):
            with self.assertRaises(Denied):
                self.submit(review)
        self.assertEqual(tuple(created), list_stop_markers(self.gateway._latch_path()))
        self.assertTrue(self.store.status()['halted'])
        self.assertEqual(self.store.status()['phase'], 'admitting')
        self.assertEqual((self.vault.password_reads, fixtures.Backend.started), (0, 0))

    def test_cli_run_shows_full_scope_and_submits_one_combined_request(self):
        self.store.stop('service_started_requires_operator_resume')
        review = self.preview()
        requests = []
        def rpc(request):
            requests.append(request)
            if request['action'] == 'review':
                return dict(ok=True, review=copy.deepcopy(review))
            if request['action'] == 'job_status':
                return dict(ok=True, job_state='completed', result_state='delivered')
            return dict(ok=True, already_submitted=True, request_id=review['request_id'])
        output = io.StringIO()
        with patch.object(sys, 'argv', ['db_prod_client.py', 'run', review['request_id'], '--from-chat-digest', review['approval_digest']]), \
             patch.object(db_prod_client, 'require_current_gateway'), patch.object(db_prod_client, 'rpc', side_effect=rpc), redirect_stdout(output):
            self.assertEqual(db_prod_client.main(), 0)
        self.assertEqual([x['action'] for x in requests], ['review', 'approve_submit', 'job_status'])
        self.assertEqual(requests[1]['selected_actions'], ['execute_once', 'resume_current_stop'])
        self.assertIn(json.dumps(review['control_sql']['observer_sql'], ensure_ascii=False), output.getvalue())

    def test_ready_approval_has_no_resume_action_and_keeps_epoch(self):
        epoch = self.store.status()['epoch']
        review = self.preview()
        self.assertEqual(review['selected_actions'], ['execute_once'])
        self.assertTrue(self.submit(review)[0]['ok'])
        self.assertEqual(self.store.status()['epoch'], epoch)

    def test_wrong_actions_digest_and_source_never_consume_or_connect(self):
        review = self.preview()
        for change in [dict(selected_actions=[]), dict(selected_actions=['execute_once', 'resume_current_stop']),
                       dict(approval_digest='0'*64), dict(approval_source='agent-self-approval')]:
            with self.subTest(change=change), self.assertRaises(Denied):
                self.submit(review, **change)
        row = self.gateway.approvals.lookup(review['request_id'], 'uid:'+str(self.uid))
        self.assertEqual(row['status'], 'preview')
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_sql_settings_profile_or_control_batch_change_requires_new_review(self):
        for kind in ['sql', 'settings', 'profile', 'protocol']:
            with self.subTest(kind=kind):
                review = self.preview()
                entry = self.gateway.pending[review['request_id']]
                original = copy.deepcopy(self.gateway.targets)
                profile = copy.deepcopy(self.vault.value)
                if kind == 'sql': entry['spec']['sql'] = 'SELECT 12345;'
                if kind == 'settings': self.gateway.targets['lego-prod']['read_only_verified'] = True
                if kind == 'profile': self.vault.value['port'] = 1444
                try:
                    if kind == 'protocol':
                        with patch.object(fixtures.Backend, 'review_sql', return_value=dict(setup_sql='changed', observer_sql='changed')):
                            with self.assertRaises(Denied): self.submit(review)
                    else:
                        with self.assertRaises(Denied): self.submit(review)
                finally:
                    self.gateway.targets = original
                    self.vault.value = profile
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_new_stop_or_equal_count_replaced_marker_invalidates_preview(self):
        latch = self.gateway._latch_path()
        first = create_stop_marker(latch, reason='independent_emergency_stop')
        review = self.preview()
        self.assertIn('release_emergency_stop', review['selected_actions'])
        remove_stop_markers(latch, [first])
        second = create_stop_marker(latch, reason='independent_emergency_stop')
        with self.assertRaises(Denied): self.submit(review)
        self.assertEqual(list_stop_markers(latch), (second,))
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_emergency_release_is_explicit_and_removes_only_reviewed_marker(self):
        create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop')
        review = self.preview()
        with self.assertRaises(Denied):
            self.submit(review, selected_actions=['execute_once', 'resume_current_stop'])
        self.assertTrue(self.submit(review)[0]['ok'])
        self.assertEqual(list_stop_markers(self.gateway._latch_path()), ())

    def test_expiry_or_memory_limit_violation_prevents_connection(self):
        review = self.preview()
        with self.store.transaction() as c:
            c.execute('UPDATE query_approval_v2 SET expires=0 WHERE id=?', (review['request_id'],))
        with self.assertRaises(Denied): self.submit(review)
        for value in [None, 0, True, 32*1024*1024+1]:
            with self.subTest(value=value), self.assertRaises(Denied): self.preview(max_bytes=value)
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_v1_approve_or_execute_cannot_accept_v2_review(self):
        review = self.preview()
        for action in ['approve', 'execute']:
            with self.assertRaises(Denied):
                self.gateway.handle(dict(action=action, request_id=review['request_id'],
                    digest=review['digest'], approval_source='explicit-user-chat'), self.uid)

    def test_marker_cleanup_failure_leaves_durable_recoverable_admission(self):
        self.store.stop('service_started_requires_operator_resume')
        review = self.preview()
        with patch('db_prod_gateway.remove_stop_markers', side_effect=OSError('synthetic disk error')):
            with self.assertRaises(OSError): self.submit(review)
        state = self.store.status()
        self.assertTrue(state['halted'])
        self.assertEqual(state['phase'], 'admitting')
        record = self.gateway.recovery_journal.read(state['active'])
        self.assertEqual(record.metadata['target'], 'lego-prod')
        self.assertIsNone(record.worker_pid)
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))
        self.assertTrue(self.submit(review)[0]['already_submitted'])

    def test_admitting_recovery_requires_new_observer_approval_and_keeps_halt(self):
        self.test_marker_cleanup_failure_leaves_durable_recoverable_admission()
        observed = []
        gateway = Gateway(self.store, self.vault, self.audit, self.gateway.targets,
            allowed_uids=[self.uid], backend_type=fixtures.Backend,
            recovery_process_probe=lambda pid: None, recovery_pid_presence_probe=lambda pid: False,
            recovery_sleep=lambda seconds: None,
            recovery_session_observer=lambda plan: observed.append(plan['observer_sql']) or True)
        review = gateway.handle(dict(action='recovery_prepare'), self.uid)['review']
        with self.assertRaises(Denied):
            gateway.handle(dict(action='recovery_execute', request_id=review['request_id']), self.uid)
        gateway.handle(dict(action='recovery_approve', request_id=review['request_id'], digest=review['digest'],
                            approval_source='explicit-user-chat'), self.uid)
        with patch('db_prod_gateway.current_user_sqlcmd_absent', return_value=True):
            result = gateway.handle(dict(action='recovery_execute', request_id=review['request_id']), self.uid)
        self.assertTrue(result['ok'])
        self.assertEqual(observed, [review['observer_sql']])
        self.assertIsNone(self.store.status()['active'])
        self.assertTrue(self.store.status()['halted'])

    def test_deadline_includes_admission_and_marker_cleanup_time(self):
        self.store.stop('service_started_requires_operator_resume')
        review = self.preview(timeout=.01)
        original = self.gateway.approvals.activate
        def delayed(*args):
            time.sleep(.02)
            return original(*args)
        with patch.object(self.gateway.approvals, 'activate', side_effect=delayed):
            with self.assertRaises(Denied): self.submit(review)
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_raw_sql_does_not_enter_durable_ledger(self):
        self.gateway.targets['lego-prod']['read_only_verified'] = True
        review = self.preview(sql="SELECT N'private-fixture-49257' AS example;")
        self.submit(review)
        self.assertNotIn(b'private-fixture-49257', self.path.read_bytes())

    def test_same_uid_socket_run_displays_sql_and_receives_complete_result(self):
        create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop')
        review = self.preview()
        sock = Path('/tmp') / ('q2-'+review['request_id'][:12]+'.sock')
        try:
            with Server(str(sock), Handler) as server:
                server.gateway = self.gateway
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                output = io.StringIO()
                try:
                    with patch.object(db_prod_client, 'SOCKET', str(sock)), \
                         patch.object(sys, 'argv', ['db_prod_client.py', 'run', review['request_id'], '--from-chat-digest', review['digest']]), redirect_stdout(output):
                        self.assertEqual(db_prod_client.main(), 0)
                finally:
                    server.shutdown(); thread.join(2)
            self.assertIn('"output": "1\\n"', output.getvalue())
            self.assertIn(json.dumps(review['control_sql']['observer_sql'], ensure_ascii=False), output.getvalue())
            self.assertEqual(fixtures.Backend.started, 1)
        finally:
            sock.unlink(missing_ok=True)

    def test_admission_ticket_cannot_be_extended_reused_or_used_for_other_sql(self):
        review = self.preview()
        entry = self.gateway.pending[review['request_id']]
        meta = dict(target='lego-prod', database='master', host_tag=review['host_tag'],
                    profile_digest=review['profile_fingerprint'], gateway_pid=self.gateway.gateway_pid,
                    gateway_birth=self.gateway.gateway_birth)
        ticket = self.gateway.approvals.admit(review['request_id'], review['digest'], review['selected_actions'],
                    'explicit-user-chat', entry['spec'], [], self.gateway.instance, meta)
        self.gateway.approvals.activate(ticket, self.gateway._stop_markers)
        supervisor = Supervisor(self.store)
        for invalid, spec in [(replace(ticket, deadline=ticket.deadline+60), entry['spec']),
                              (ticket, dict(entry['spec'], sql='SELECT 999;'))]:
            with self.assertRaises(Denied):
                supervisor.execute_admitted(invalid, **spec, backend=fixtures.Backend())
        self.assertEqual(fixtures.Backend.started, 0)
        self.assertTrue(supervisor.execute_admitted(ticket, **entry['spec'], backend=fixtures.Backend())['ok'])
        with self.assertRaises(Denied):
            supervisor.execute_admitted(ticket, **entry['spec'], backend=fixtures.Backend())
        self.assertEqual(fixtures.Backend.started, 1)

    def test_independent_processes_cannot_both_consume_and_own_admission(self):
        reviews = [self.preview(), self.preview()]
        code = """
import json,sys
sys.path.insert(0,sys.argv[1])
from db_query_control import Store,Denied
from db_prod_approval import ApprovalLedger
d=json.load(sys.stdin)
try:
 t=ApprovalLedger(Store(sys.argv[2])).admit(d['id'],d['digest'],d['actions'],'explicit-user-chat',d['spec'],[],'fixture',{})
 print('won' if t else 'duplicate')
except Denied:
 print('denied')
"""
        processes = []
        for r in reviews:
            p = subprocess.Popen([sys.executable, '-c', code, str(Path(__file__).resolve().parents[1]), str(self.path)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            p.stdin.write(json.dumps(dict(id=r['request_id'], digest=r['digest'], actions=r['selected_actions'],
                                         spec=self.gateway.pending[r['request_id']]['spec'])))
            p.stdin.close(); p.stdin = None
            processes.append(p)
        results = []
        for p in processes:
            out, err = p.communicate(timeout=10)
            self.assertEqual(p.returncode, 0, err)
            results.append(out.strip())
        self.assertEqual(sorted(results), ['denied', 'won'])
        with self.store.transaction() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM approvals WHERE status='consumed'").fetchone()[0], 1)
        self.assertEqual(self.store.status()['phase'], 'admitting')
        self.assertFalse(self.store.status()['halted'])

    def test_audit_failure_or_new_stop_during_credentials_never_opens_db(self):
        review = self.preview()
        self.audit.fail = True
        with self.assertRaises(Denied): self.submit(review)
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_new_stop_during_credentials_never_opens_db(self):
        review = self.preview()
        credentials = self.vault.credentials
        def stop(*args, **kwargs):
            value = credentials(*args, **kwargs)
            create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop')
            return value
        with patch.object(self.vault, 'credentials', side_effect=stop):
            result, _ = self.submit(review)
        self.assertFalse(result['ok'])
        self.assertEqual(fixtures.Backend.started, 0)
        self.assertTrue(self.store.status()['halted'])

    def test_transaction_failure_cannot_half_consume_approval_or_open_after_cleanup(self):
        from contextlib import contextmanager
        for phase in ['admitting', 'starting']:
            with self.subTest(phase=phase):
                # Each iteration has a separate coordinator.
                if phase == 'starting':
                    self.tearDown(); self.setUp()
                self.store.stop('service_started_requires_operator_resume')
                review = self.preview()
                original = self.store.transaction
                fired = []
                @contextmanager
                def interrupted():
                    with original() as c:
                        yield c
                        if not fired and c.execute('SELECT phase FROM control').fetchone()[0] == phase:
                            fired.append(True)
                            raise OSError('synthetic commit failure')
                with patch.object(self.store, 'transaction', side_effect=interrupted):
                    with self.assertRaises(OSError): self.submit(review)
                self.assertTrue(fired)
                self.assertTrue(self.store.status()['halted'])
                self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))
                row = self.gateway.approvals.lookup(review['request_id'], 'uid:'+str(self.uid))
                self.assertEqual(row['status'], 'preview' if phase == 'admitting' else 'admitting')

    def test_missing_consumed_approval_refuses_backend_start(self):
        review = self.preview()
        execute = self.gateway.execute
        def corrupt(*args, **kwargs):
            with self.store.transaction() as c:
                c.execute('DELETE FROM approvals WHERE id=?', (review['request_id'],))
            return execute(*args, **kwargs)
        with patch.object(self.gateway, 'execute', side_effect=corrupt):
            self.assertFalse(self.submit(review)[0]['ok'])
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_ready_admission_never_writes_external_halt_or_epoch(self):
        with self.store.transaction() as c:
            c.execute('CREATE TABLE external_writes(value INTEGER)')
            c.execute('''CREATE TRIGGER monitor_external_halt AFTER UPDATE OF halted,epoch ON control
                         BEGIN INSERT INTO external_writes VALUES (1); END''')
        self.assertTrue(self.submit(self.preview())[0]['ok'])
        with self.store.transaction() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM external_writes').fetchone()[0], 0)

    def test_process_death_after_a_b_or_c_keeps_slot_and_recovery_metadata(self):
        code = """
import json,sys,os
sys.path.insert(0,sys.argv[1])
from db_query_control import Store
from db_prod_approval import ApprovalLedger
from db_prod_watchdog import remove_stop_markers,list_stop_markers,process_fingerprint
d=json.load(sys.stdin); ledger=ApprovalLedger(Store(sys.argv[2]))
d['meta']['gateway_pid']=os.getpid(); d['meta']['gateway_birth']=process_fingerprint(os.getpid())
t=ledger.admit(d['id'],d['digest'],d['actions'],'explicit-user-chat',d['spec'],d['markers'],'fixture',d['meta'])
if d['stage'] in ('B','C'): remove_stop_markers(d['latch'],d['markers'])
if d['stage']=='C': ledger.activate(t,lambda:list_stop_markers(d['latch']))
os._exit(42)
"""
        for stage in ['A', 'B', 'C']:
            with self.subTest(stage=stage):
                if stage != 'A': self.tearDown(); self.setUp()
                create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop')
                review = self.preview()
                meta = dict(target='lego-prod', database='master', host_tag=review['host_tag'],
                            profile_digest=review['profile_fingerprint'], gateway_pid=self.gateway.gateway_pid,
                            gateway_birth=self.gateway.gateway_birth)
                data = dict(id=review['request_id'], digest=review['digest'], actions=review['selected_actions'],
                            spec=self.gateway.pending[review['request_id']]['spec'], markers=review['stop_snapshot']['markers'],
                            latch=str(self.gateway._latch_path()), meta=meta, stage=stage)
                with subprocess.Popen([sys.executable, '-c', code, str(Path(__file__).resolve().parents[1]), str(self.path)],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as p:
                    try:
                        out, err = p.communicate(json.dumps(data), timeout=10)
                    except subprocess.TimeoutExpired:
                        p.kill(); p.wait()
                        raise
                self.assertEqual(p.returncode, 42, err)
                state = self.store.status()
                self.assertIsNotNone(state['active'])
                admission = self.gateway.approvals.lookup(review['request_id'], 'uid:'+str(self.uid))
                self.assertEqual(admission['runtime'], review['runtime_fingerprint'])
                self.assertEqual(state['phase'], 'starting' if stage == 'C' else 'admitting')
                self.assertEqual(bool(state['halted']), stage != 'C')
                self.store.stop('service_started_requires_operator_resume')
                restarted = Gateway(self.store, self.vault, self.audit, self.gateway.targets,
                    allowed_uids=[self.uid], backend_type=fixtures.Backend)
                stored_meta = restarted.recovery_journal.read(state['active']).metadata
                self.assertEqual(stored_meta['gateway_pid'], p.pid)
                self.assertTrue(stored_meta['gateway_birth'])
                self.assertEqual(stored_meta['host_tag'], meta['host_tag'])
                recovered_review = restarted.handle(dict(action='recovery_prepare'), self.uid)['review']
                self.assertEqual(recovered_review['run_id'], state['active'])
                self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_partial_marker_cleanup_failure_never_reopens_or_retries(self):
        create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop')
        review = self.preview()
        def after_removal(path, markers):
            remove_stop_markers(path, markers)
            raise OSError('synthetic directory fsync failure')
        with patch('db_prod_gateway.remove_stop_markers', side_effect=after_removal):
            with self.assertRaises(OSError): self.submit(review)
        self.assertEqual(list_stop_markers(self.gateway._latch_path()), ())
        self.assertTrue(self.store.status()['halted'])
        self.assertEqual(self.store.status()['phase'], 'admitting')
        self.assertTrue(self.submit(review)[0]['already_submitted'])
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_cli_preview_shows_v2_review_and_uses_explicit_default_memory_limit(self):
        seen = []
        def rpc(request):
            seen.append(request)
            return self.gateway.handle(request, self.uid)
        output = io.StringIO()
        with patch.object(sys, 'argv', ['db_prod_client.py', 'preview', '--target', 'lego-prod', '--database', 'master', '--timeout', '5']), \
             patch.object(sys, 'stdin', io.StringIO(fixtures.PROBE_SQL)), patch.object(db_prod_client, 'require_current_gateway'), \
             patch.object(db_prod_client, 'rpc', side_effect=rpc), redirect_stdout(output):
            self.assertEqual(db_prod_client.main(), 0)
        self.assertEqual(seen[0]['api_version'], 2)
        self.assertEqual(seen[0]['max_bytes'], 33554432)
        self.assertIn('조건부 종료 확인 SQL', output.getvalue())
        self.assertEqual((fixtures.Backend.started, self.vault.password_reads), (0, 0))

    def test_real_transport_adapter_writes_reviewed_batches_and_bounds_output(self):
        for limited in [False, True]:
            with self.subTest(limited=limited):
                observer_sql = []
                class NoWatch:
                    def start(self): return self
                    def close(self, **kwargs): pass
                class Factory(transport_fixtures.ShortWriteFactory):
                    def __call__(self, *args, **kwargs):
                        process = super().__call__(*args, **kwargs)
                        process.pid = 222
                        return process
                factory = Factory(output=b'fixture-too-large\n' if limited else b'1\n')
                class Transport(SqlcmdBackend):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs, popen_factory=factory,
                            watchdog_factory=lambda *a, **k: NoWatch(),
                            observer_runner=lambda *a: observer_sql.append(a[3]) or True)
                    def _signal_group(self, sig):
                        # The process is a stdio fake, never signal a real PID.
                        self.process.send_signal(sig)
                self.gateway = Gateway(self.store, self.vault, self.audit, self.gateway.targets,
                    allowed_uids=[self.uid], backend_type=Transport,
                    recovery_process_probe=lambda pid: 'fixture-worker-birth')
                review = self.preview(max_bytes=4 if limited else 1024)
                # Independent fixed protocol fixture, never generated by review_sql/control_sql.
                setup = b"SET NOCOUNT ON;\nPRINT 'SQLCMD_READY';\nGO\n"
                observer = """SET NOCOUNT ON;
DECLARE @has_session_visibility int = CASE WHEN HAS_PERMS_BY_NAME(NULL, NULL, N'VIEW SERVER STATE') = 1 OR HAS_PERMS_BY_NAME(NULL, NULL, N'VIEW SERVER PERFORMANCE STATE') = 1 THEN 1 ELSE 0 END;
DECLARE @session_count int = 0, @checks int = 0;
WHILE @has_session_visibility = 1 AND @checks < 16
BEGIN
    SELECT @session_count = COUNT(*) FROM sys.dm_exec_sessions AS s
    WHERE s.host_name = N'{tag}' AND s.session_id <> @@SPID;
    IF @session_count = 0 BREAK;
    SET @checks += 1;
    IF @checks < 16 WAITFOR DELAY '00:00:00.200';
END;
SELECT @has_session_visibility AS has_session_visibility, @session_count AS session_count;
""".format(tag=review['host_tag'])
                self.assertEqual(review['control_sql']['setup_sql'].encode('utf-8'), setup)
                self.assertEqual(review['control_sql']['observer_sql'], observer)
                result, _ = self.submit(review)
                self.assertEqual(result['ok'], not limited)
                self.assertEqual(len(factory.processes), 1)
                self.assertEqual(bytes(factory.processes[0].stdin.data),
                    setup + b'SELECT 1 AS connection_ok;')
                self.assertEqual(observer_sql, [observer] if limited else [])


if __name__ == '__main__':
    unittest.main()
