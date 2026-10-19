"""Contract tests for a single central query coordinator, no DB credentials."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_query_control import Store, Supervisor


class Backend:
    def __init__(self, result=None, closed=True):
        self.result = result
        self.confirm_close = closed
        self.cancelled = False
        self.dispatched = threading.Event()

    def start(self, run):
        return {"session": 55, "connection": run}

    def dispatch(self, sql, limits):
        self.dispatched.set()

    def poll(self):
        return self.result

    def cancel(self):
        self.cancelled = True

    def closed(self):
        return self.confirm_close


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"control.sqlite3"
        Store.initialize(self.path)
        self.store = Store(self.path)
        self.control = Supervisor(self.store, cleanup_timeout=0.1, poll_interval=0.01)
        self.assertTrue(self.control.resume(lambda: True))

    def tearDown(self):
        self.directory.cleanup()

    def run_query(self, **kwargs):
        request = self.store.prepare(owner=kwargs["owner"], target=kwargs["target"],
                                     sql="SELECT 1;", timeout=kwargs.get("timeout", 60))
        self.store.approve(request["id"], request["digest"], operator="human")
        return self.control.execute(**kwargs, approval_id=request["id"])

    def test_two_agent_sessions_share_one_slot_and_stop_latches(self):
        backend = Backend()
        results = []
        thread = threading.Thread(target=lambda: results.append(self.run_query(
            owner="agent-a", target="prod-a", backend=backend, timeout=2)))
        thread.start()
        try:
            self.assertTrue(backend.dispatched.wait(1))
            other = Supervisor(Store(self.path))
            self.assertEqual(other.execute(owner="agent-b", target="prod-b", backend=Backend(True))["status"], "busy")
            # An independent controller process only needs the persistent store.
            other.stop()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertTrue(backend.cancelled)
            self.assertEqual(results[0]["status"], "stopped")
            self.assertTrue(Store(self.path).status()["halted"])
            self.assertEqual(other.execute(owner="agent-c", target="prod-a", backend=Backend(True))["status"], "halted")
        finally:
            self.control.stop()
            thread.join(2)

    def test_query_error_cancels_and_requires_explicit_resume(self):
        backend = Backend(False)
        result = self.run_query(owner="agent", target="prod", backend=backend)
        self.assertEqual(result["status"], "stopped")
        self.assertTrue(backend.cancelled)
        self.assertIsNone(self.store.status()["active"])
        self.assertFalse(self.control.resume(lambda: False))
        self.assertTrue(self.control.resume(lambda: True))
        self.assertTrue(self.run_query(owner="agent", target="prod", backend=Backend(True))["ok"])

    def test_stop_or_disconnect_between_poll_close_and_finish_observes_once(self):
        for reason in ("operator_stop", "client_disconnected"):
            for stage in ("poll", "closed"):
                with self.subTest(reason=reason, stage=stage):
                    store = self.store
                    class RacingBackend(Backend):
                        completion_basis = None
                        observations = 0
                        def poll(self):
                            if stage == "poll":
                                store.stop(reason)
                            return True
                        def closed(self):
                            if self.cancelled:
                                self.observations += self.completion_basis != "observer"
                                self.completion_basis = "observer"
                            else:
                                self.completion_basis = "normal_exit"
                                if stage == "closed":
                                    store.stop(reason)
                            return True
                    backend = RacingBackend(True)
                    published = []
                    result = self.run_query(owner="agent", target="prod", backend=backend, publish=published.append)
                    self.assertFalse(result["ok"])
                    self.assertTrue(result["session_closed"])
                    self.assertEqual((backend.observations, backend.completion_basis), (1, "observer"))
                    self.assertEqual(published, [])
                    self.assertIsNone(self.store.status()["active"])
                    self.assertTrue(self.store.status()["halted"])
                    self.assertTrue(self.control.resume(lambda: True))

    def test_receipt_failure_observes_before_releasing_slot(self):
        for observed in (True, False):
            with self.subTest(observed=observed):
                class ReceiptBackend(Backend):
                    completion_basis = None
                    observations = 0
                    def closed(self):
                        if self.cancelled:
                            self.observations += 1
                            self.completion_basis = "observer" if observed else None
                            return observed
                        self.completion_basis = "normal_exit"
                        return True
                def fail_receipt(_receipt):
                    raise OSError("synthetic disconnected socket")
                backend = ReceiptBackend(True)
                result = self.run_query(owner="agent", target="prod", backend=backend, publish=fail_receipt)
                self.assertFalse(result["ok"])
                self.assertEqual(result["session_closed"], observed)
                self.assertEqual(backend.observations, 1)
                self.assertEqual(self.store.status()["active"] is None, observed)
                self.assertTrue(self.store.status()["halted"])
                if observed:
                    self.assertTrue(self.control.resume(lambda: True))

    def test_missing_server_confirmation_never_releases_slot(self):
        backend = Backend(False, closed=False)
        result = self.run_query(owner="agent", target="prod", backend=backend)
        self.assertEqual(result["status"], "unconfirmed")
        self.assertIsNotNone(Store(self.path).status()["active"])
        self.assertFalse(self.control.resume(lambda: True))
        self.assertTrue(self.control.reconcile(lambda: True))
        self.assertTrue(self.store.status()["halted"])
        self.assertTrue(self.control.resume(lambda: True))

    def test_stale_running_slot_does_not_expire_or_auto_resume(self):
        request = self.store.prepare(owner="dead-worker", target="prod", sql="SELECT 1;")
        self.store.approve(request["id"], request["digest"], operator="human")
        run = self.store.reserve("dead-worker", "prod", "SELECT 1;", request["id"])
        fresh = Supervisor(Store(self.path))
        self.assertEqual(fresh.execute(owner="new", target="prod", backend=Backend(True))["status"], "busy")
        fresh.stop()
        self.assertFalse(fresh.resume(lambda: True))
        self.assertFalse(fresh.reconcile(lambda: True))
        self.assertEqual(self.store.status()["active"], run)

    def test_stop_before_dispatch_prevents_sql_submission(self):
        control = self.control
        class StopAtStart(Backend):
            def start(self, run):
                control.stop()
                return super().start(run)
        backend = StopAtStart(True)
        result = self.run_query(owner="agent", target="prod", backend=backend)
        self.assertFalse(backend.dispatched.is_set())
        self.assertFalse(result["ok"])
        self.assertTrue(backend.cancelled)

    def test_missing_or_pending_approval_never_opens_connection(self):
        class NeverStart(Backend):
            def start(self, run):
                raise AssertionError("Unapproved SQL reached DB")
        request = self.store.prepare(owner="agent", target="prod", sql="SELECT 1;")
        self.assertEqual(request["review"]["sql"], "SELECT 1;")
        for approval in (None, request["id"], "forged"):
            result = self.control.execute(owner="agent", target="prod", backend=NeverStart(), approval_id=approval)
            self.assertEqual(result["status"], "approval_required")

    def test_approval_binds_full_sql_target_owner_and_limits_and_is_one_use(self):
        request = self.store.prepare(owner="agent", target="prod", sql="SELECT 1;", max_rows=5000)
        self.store.approve(request["id"], request["digest"], operator="human")
        base = dict(owner="agent", target="prod", sql="SELECT 1;", max_rows=5000, approval_id=request["id"])
        for change in (dict(sql="SELECT 2;"), dict(target="other"), dict(owner="other"),
                       dict(max_rows=None), dict(max_bytes=9000), dict(timeout=30)):
            result = self.control.execute(**{**base, **change}, backend=Backend(True))
            self.assertEqual(result["status"], "approval_required")
        self.assertTrue(self.control.execute(**base, backend=Backend(True))["ok"])
        self.assertEqual(self.control.execute(**base, backend=Backend(True))["status"], "approval_required")

    def test_sixty_seconds_is_hard_maximum(self):
        for timeout in (61, 0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.store.prepare(owner="agent", target="prod", sql="SELECT 1;", timeout=timeout)

    def test_new_stop_during_resume_check_cannot_be_cleared(self):
        self.control.stop()
        def observer():
            Store(self.path).stop()
            return True
        self.assertFalse(self.control.resume(observer))
        self.assertTrue(self.store.status()["halted"])

    def test_dispatch_is_one_use_even_when_submit_throws_after_sending(self):
        request = self.store.prepare(owner="agent", target="prod", sql="SELECT 1;")
        self.store.approve(request["id"], request["digest"], operator="human")
        run = self.store.reserve("agent", "prod", "SELECT 1;", request["id"])
        sent = []
        def submitted_then_failed():
            sent.append("sent")
            raise RuntimeError("lost acknowledgement")
        with self.assertRaises(RuntimeError):
            self.store.dispatch(run, {"session": 55}, submitted_then_failed)
        self.assertEqual(self.store.status()["phase"], "dispatching")
        with self.assertRaises(Exception):
            self.store.dispatch(run, {"session": 55}, lambda: sent.append("duplicate"))
        self.assertEqual(sent, ["sent"])

    def test_stop_before_publish_discards_result(self):
        store = self.store
        class StopAfterQuery(Backend):
            def closed(self):
                store.stop()
                return True
        published = []
        result = self.run_query(owner="agent", target="prod", backend=StopAfterQuery(True), publish=published.append)
        self.assertFalse(result["ok"])
        self.assertEqual(published, [])

    def test_success_publishes_inside_same_transaction_as_completion(self):
        published = []
        result = self.run_query(owner="agent", target="prod", backend=Backend(True), publish=published.append)
        self.assertTrue(result["ok"])
        self.assertEqual(published[0]["run_id"], result["run_id"])
        self.control.stop()
        self.assertTrue(self.store.status()["halted"])
        self.assertEqual(len(published), 1)

    def test_distinct_agent_processes_cannot_both_acquire_slot(self):
        approvals = []
        for owner in ("process-a", "process-b"):
            request = self.store.prepare(owner=owner, target="prod", sql="SELECT 1;")
            self.store.approve(request["id"], request["digest"], operator="human")
            approvals.append((owner, request["id"]))
        script = """import json,sys
sys.path.insert(0,sys.argv[4])
from db_query_control import Store,Denied
try:
 run=Store(sys.argv[1]).reserve(sys.argv[2],'prod','SELECT 1;',sys.argv[3])
 print(json.dumps({'status':'admitted','run':run}))
except Denied as error:
 print(json.dumps({'status':str(error)}))
"""
        children = [subprocess.Popen([sys.executable, "-c", script, str(self.path), owner, request,
                                      str(Path(__file__).resolve().parents[1])], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True) for owner, request in approvals]
        statuses = []
        for child in children:
            stdout, stderr = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, stderr)
            statuses.append(json.loads(stdout)["status"])
        self.assertCountEqual(statuses, ["admitted", "busy"])
        self.assertIsNotNone(Store(self.path).status()["active"])

    def test_publish_then_failure_cannot_republish_or_auto_resume(self):
        published = []
        def lost_ack(receipt):
            published.append(receipt)
            raise RuntimeError("Publication acknowledgement lost")
        result = self.run_query(owner="agent", target="prod", backend=Backend(True), publish=lost_ack)
        self.assertFalse(result["ok"])
        self.assertTrue(self.store.status()["halted"])
        self.assertEqual(self.store.status()["phase"], "idle")
        self.assertIsNone(self.store.status()["active"])
        with self.assertRaises(Exception):
            self.store.finish(result["run_id"], closed=True, successful=True, publish=published.append)
        self.assertEqual(len(published), 1)
        self.assertEqual(self.control.execute(owner="agent", target="prod", backend=Backend(True))["status"], "halted")
        self.assertTrue(self.control.resume(lambda: True))


if __name__ == "__main__":
    unittest.main()
