"""Detached jobs and repeatable result delivery, using synthetic data only."""
import base64
import hashlib
import io
from pathlib import Path
import sys
import threading
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_db_prod_gateway as fixtures
from db_prod_gateway import Gateway
from db_query_control import Denied
from db_prod_watchdog import create_stop_marker
import db_prod_client


class JobFlowTests(unittest.TestCase):
    setUp = fixtures.GatewayTests.setUp
    tearDown = fixtures.GatewayTests.tearDown

    def preview(self):
        return self.gateway.handle(dict(action='prepare', api_version=2, target='lego-prod',
            database='master', sql=fixtures.PROBE_SQL, timeout=5), self.uid)['review']

    def submit(self, review, **kwargs):
        return self.gateway.handle(dict(action='approve_submit', request_id=review['request_id'],
            approval_digest=review['digest'], selected_actions=review['selected_actions'],
            approval_source='explicit-user-chat'), self.uid, **kwargs)

    def status(self, review):
        return self.gateway.handle(dict(action='job_status', request_id=review['request_id']), self.uid)

    def wait(self, review):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            result = self.status(review)
            if result['job_state'] in ('completed','failed','recovery_required','unknown'):
                return result
            time.sleep(.005)
        self.fail('job did not reach a terminal state')

    def test_submission_returns_while_query_runs_and_disconnect_does_not_cancel(self):
        release = threading.Event()
        review = self.preview()
        def poll():
            return True if release.is_set() else None
        with patch.object(fixtures.Backend, 'poll', side_effect=poll):
            try:
                accepted = self.submit(review, disconnected=lambda: True)
                self.assertEqual(accepted['status'], 'accepted')
                self.assertIn(self.status(review)['job_state'], ('starting','dispatching','running'))
                self.assertTrue(self.submit(review)['already_submitted'])
            finally:
                release.set()
            result = self.wait(review)
        self.assertEqual(result['job_state'], 'completed')
        self.assertEqual(result['result_state'], 'available')
        self.assertEqual(fixtures.Backend.started, 1)
        self.assertFalse(self.store.status()['halted'])

    def fetch(self, review, status, offset=0, **changes):
        request = dict(action='fetch_result', request_id=review['request_id'],
                       result_digest=status['result_digest'], epoch=status['epoch'], offset=offset)
        request.update(changes)
        chunks = []
        self.gateway.handle(request, self.uid, publish=chunks.append)
        return chunks[0]

    def ack(self, review, status):
        return self.gateway.handle(dict(action='ack_result', request_id=review['request_id'],
            result_digest=status['result_digest'], epoch=status['epoch']), self.uid)

    def test_repeated_fetch_returns_identical_bytes_until_durable_ack(self):
        review = self.preview(); self.submit(review); status = self.wait(review)
        first = self.fetch(review, status)
        self.assertEqual(self.fetch(review, status), first)
        self.assertEqual(base64.b64decode(first['data_base64']), b'1\n')
        self.assertTrue(first['final'])
        self.assertTrue(self.ack(review, status)['ok'])
        self.assertTrue(self.ack(review, status)['already_delivered'])
        with self.assertRaises(Denied): self.fetch(review, status)
        self.assertEqual(self.status(review)['result_state'], 'delivered')
        self.assertEqual(fixtures.Backend.started, 1)

    def test_legacy_fetch_cannot_bypass_v2_identity_or_ack(self):
        review = self.preview(); self.submit(review); status = self.wait(review)
        with self.assertRaises(Denied):
            self.gateway.handle(dict(action='fetch', run_id=status['run_id'], offset=0),
                                self.uid, publish=lambda chunk: None)
        self.assertEqual(base64.b64decode(self.fetch(review,status)['data_base64']), b'1\n')

    def restart(self):
        self.store.stop('service_started_requires_operator_resume')
        self.gateway = Gateway(self.store, self.vault, self.audit, self.gateway.targets,
            allowed_uids=[self.uid], backend_type=fixtures.Backend)

    def test_restart_loses_bytes_preserves_ack_and_never_replays_sql(self):
        first = self.preview(); self.submit(first); first_status = self.wait(first)
        self.ack(first, first_status)
        second = self.preview(); self.submit(second); second_status = self.wait(second)
        self.restart()
        self.assertTrue(self.ack(first, first_status)['already_delivered'])
        self.assertEqual(self.status(first)['result_state'], 'delivered')
        self.assertEqual(self.status(second)['result_state'], 'lost_on_restart')
        with self.assertRaises(Denied): self.fetch(second, second_status)
        self.assertTrue(self.submit(second)['already_submitted'])
        self.assertEqual(fixtures.Backend.started, 2)

    def test_lost_fetch_reply_is_repeatable_and_wrong_owner_does_not_evict(self):
        review = self.preview(); self.submit(review); status = self.wait(review)
        identity = dict(request_id=review['request_id'], result_digest=status['result_digest'], epoch=status['epoch'])
        request = dict(action='fetch_result', offset=0, **identity)
        self.gateway.allowed_uids.add(self.uid+1)
        with self.assertRaises(Denied):
            self.gateway.handle(request, self.uid+1, publish=lambda value: None)
        with self.assertRaises(OSError):
            self.gateway.handle(request, self.uid, publish=lambda value: (_ for _ in ()).throw(OSError('lost reply')))
        self.assertEqual(base64.b64decode(self.fetch(review,status)['data_base64']), b'1\n')
        for changes in [dict(result_digest='wrong'),dict(epoch=status['epoch']+1),dict(offset=-1),dict(offset=True)]:
            with self.subTest(changes=changes), self.assertRaises(Denied): self.fetch(review,status,**changes)

    def test_new_stop_after_completion_blocks_fetch_and_ack(self):
        review = self.preview(); self.submit(review); status = self.wait(review)
        create_stop_marker(self.gateway._latch_path(), reason='independent_emergency_stop')
        with self.assertRaises(Denied): self.fetch(review,status)
        with self.assertRaises(Denied): self.ack(review,status)
        self.assertEqual(self.status(review)['result_state'], 'stopped')

    def test_ttl_is_not_extended_by_fetch_and_next_result_supersedes_old(self):
        first = self.preview(); self.submit(first); status = self.wait(first)
        self.fetch(first,status)
        later = time.monotonic()+61
        with patch('db_prod_gateway.time.monotonic', return_value=later):
            self.assertEqual(self.status(first)['result_state'], 'expired')
            with self.assertRaises(Denied): self.fetch(first,status)
        second = self.preview(); self.submit(second); second_status = self.wait(second)
        third = self.preview(); self.submit(third); self.wait(third)
        self.assertEqual(self.status(second)['result_state'], 'superseded')
        with self.assertRaises(Denied): self.fetch(second,second_status)

    def test_preview_lost_on_restart_requires_new_review(self):
        review = self.preview()
        self.restart()
        self.assertEqual(self.status(review)['job_state'], 'preview_lost')
        with self.assertRaises(Denied): self.submit(review)
        self.assertEqual(fixtures.Backend.started, 0)

    def test_job_schema_mismatch_fails_closed(self):
        with self.store.transaction() as c:
            c.execute('UPDATE query_job_schema SET version=99')
        with self.assertRaises(Denied): self.restart()
        self.assertEqual(fixtures.Backend.started, 0)

    def test_client_resolves_lost_submission_and_ack_replies_without_replay(self):
        review = self.preview(); requests=[]; dropped_ack=False
        def rpc(request):
            nonlocal dropped_ack
            requests.append(request['action'])
            chunks=[]
            result=self.gateway.handle(request,self.uid,publish=chunks.append)
            if request['action']=='approve_submit': raise OSError('accepted reply lost')
            if request['action']=='ack_result' and not dropped_ack:
                dropped_ack=True;raise OSError('ack reply lost')
            return chunks[0] if chunks else result
        output=io.StringIO()
        with patch.object(db_prod_client,'rpc',side_effect=rpc),patch.object(db_prod_client,'require_current_gateway'), \
             patch.object(sys,'argv',['client','run',review['request_id'],'--from-chat-digest',review['digest']]),redirect_stdout(output):
            self.assertEqual(db_prod_client.main(),0)
        self.assertEqual(requests.count('approve_submit'),1)
        self.assertEqual(requests.count('ack_result'),2)
        self.assertIn('"output": "1\\n"',output.getvalue())
        self.assertEqual(fixtures.Backend.started,1)
        self.assertEqual(self.status(review)['result_state'],'delivered')

    def test_multichunk_result_is_identical_and_memory_only(self):
        data=('한글,\"a\"\n'*1000).encode('utf-8')
        with patch.object(fixtures.Backend,'payload',data):
            review=self.preview();self.submit(review);status=self.wait(review)
        self.assertEqual(status['output_sha256'],hashlib.sha256(data).hexdigest())
        output=bytearray()
        while True:
            chunk=self.fetch(review,status,offset=len(output))
            self.assertEqual(self.fetch(review,status,offset=len(output)),chunk)
            output.extend(base64.b64decode(chunk['data_base64']))
            if chunk['final']:break
        self.assertEqual(bytes(output),data)
        self.assertNotIn(data,self.path.read_bytes())

    def test_timeout_and_explicit_stop_still_control_detached_worker(self):
        for reason in ['timeout','stop']:
            if reason=='stop':self.tearDown();self.setUp()
            with self.subTest(reason=reason),patch.object(fixtures.Backend,'poll',return_value=None):
                request=dict(action='prepare',api_version=2,target='lego-prod',database='master',
                    sql=fixtures.PROBE_SQL,timeout=.1 if reason=='timeout' else 5)
                review=self.gateway.handle(request,self.uid)['review'];self.submit(review)
                if reason=='stop':
                    deadline=time.monotonic()+2
                    while not fixtures.Backend.started and time.monotonic()<deadline:time.sleep(.002)
                    self.assertEqual(fixtures.Backend.started,1)
                    self.store.stop('independent_emergency_stop')
                result=self.wait(review)
                self.assertEqual(result['job_state'],'failed')
                self.assertEqual(result['result_state'],'none')
                self.assertTrue(self.store.status()['halted'])
                self.assertTrue(self.submit(review)['already_submitted'])

    def test_worker_thread_cannot_start_requires_recovery_without_replay(self):
        review=self.preview()
        with patch('db_prod_gateway.threading.Thread.start',side_effect=RuntimeError('thread unavailable')):
            with self.assertRaises(RuntimeError):self.submit(review)
        self.assertEqual(self.status(review)['job_state'],'recovery_required')
        self.assertTrue(self.submit(review)['already_submitted'])
        self.assertEqual((fixtures.Backend.started,self.vault.password_reads),(0,0))

    def test_ack_is_durable_before_memory_cleanup(self):
        review=self.preview();self.submit(review);status=self.wait(review)
        class BrokenCleanup(dict):
            def pop(self,*args,**kwargs):raise OSError('cleanup interrupted')
        self.gateway.results=BrokenCleanup(self.gateway.results)
        with self.assertRaises(OSError):self.ack(review,status)
        self.assertTrue(self.ack(review,status)['already_delivered'])
        with self.assertRaises(Denied):self.fetch(review,status)

    def test_client_rejects_corrupt_stream_before_ack_and_can_fetch_again(self):
        review=self.preview();self.submit(review);self.wait(review);actions=[]
        def rpc(request):
            actions.append(request['action']);chunks=[]
            result=self.gateway.handle(request,self.uid,publish=chunks.append)
            if chunks:
                return dict(chunks[0],data_base64=base64.b64encode(b'X\n').decode())
            return result
        with patch.object(db_prod_client,'rpc',side_effect=rpc),self.assertRaisesRegex(RuntimeError,'result_digest_mismatch'):
            db_prod_client.receive_job(review['request_id'])
        self.assertNotIn('ack_result',actions)
        self.assertEqual(self.status(review)['result_state'],'available')
        self.assertEqual(fixtures.Backend.started,1)

    def test_terminal_tombstone_expires_but_recovery_records_do_not(self):
        review=self.preview();self.submit(review);status=self.wait(review);self.ack(review,status)
        later=time.time()+31*86400
        with patch('db_prod_jobs.time.time',return_value=later):
            with self.assertRaises(Denied):self.status(review)
            with self.assertRaises(Denied):self.ack(review,status)
        pending=self.preview()
        with patch('db_prod_gateway.threading.Thread.start',side_effect=RuntimeError('thread unavailable')):
            with self.assertRaises(RuntimeError):self.submit(pending)
        with patch('db_prod_jobs.time.time',return_value=later):
            self.assertEqual(self.status(pending)['job_state'],'recovery_required')

    def test_v2_cli_requires_capability_without_automatic_restart(self):
        from db_prod_gateway import current_source_fingerprint
        with patch.object(db_prod_client,'rpc',return_value=dict(ok=True,runtime_fingerprint=current_source_fingerprint())):
            with self.assertRaisesRegex(RuntimeError,'gateway_restart_required'):
                db_prod_client.require_current_gateway(require_jobs=True)


if __name__ == '__main__':
    unittest.main()
