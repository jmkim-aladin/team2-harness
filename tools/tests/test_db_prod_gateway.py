"""Current-user gateway contracts. Synthetic credentials; no real keychain/DB."""
import base64
import copy
import io
import json
import hashlib
from contextlib import contextmanager
import os
import sqlite3
import socket
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_query_control import Store, Supervisor, Denied
from db_prod_gateway import Gateway, LatchStore, PROBE_SQL, SESSION_VISIBILITY_PROBE_SQL, SESSION_STOP_PROBE_SQL, validate_read_sql
from db_prod_profiles import ProfileError, parse_profile, profile_digest
from db_prod_diagnostics import Diagnostics
from db_prod_watchdog import create_stop_marker


class Vault:
    def __init__(self):
        self.value = dict(host="fixture.invalid", port=1433, account="fixture")
        self.password_reads = 0

    def profile(self, *args, **kwargs):
        return copy.deepcopy(self.value)

    def credentials(self, target, expected, **kwargs):
        self.password_reads += 1
        if profile_digest(expected) != profile_digest(self.value):
            raise ProfileError("profile_changed_new_approval_required")
        return dict(self.value, password="synthetic-only")


class Audit:
    def __init__(self):
        self.events = []
        self.fail = False

    def write(self, event, **detail):
        if self.fail:
            raise OSError("synthetic audit error")
        self.events.append((event, detail))


class Backend:
    started = 0
    payload = b"1\n"
    result = True
    close_ok = True
    instances = []

    @staticmethod
    def validate_sql(sql): return True
    @staticmethod
    def review_sql(tag): return {"observer_sql": "SELECT 0; -- " + tag, "setup_sql": "SET NOCOUNT ON;"}

    def __init__(self, *args, **kwargs):
        self.cancelled = False
        self.options = kwargs
        self.__class__.instances.append(self)

    def start(self, run):
        self.__class__.started += 1
        return {"host_tag": run}

    def dispatch(self, sql, limits): pass
    def poll(self): return self.result
    def cancel(self): self.cancelled = True
    def closed(self): return self.close_ok
    def output_bytes(self): return self.payload


class RecoveryBackend(Backend):
    process_pid = 222
    close_ok = False
    observed = 0

    def observe_closed(self, host_tag, timeout=5):
        type(self).observed += 1
        return host_tag.startswith("q-") and timeout == 5


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "control.db"
        Store.initialize(self.path)
        self.store = Store(self.path)
        Supervisor(self.store).resume(lambda: True)
        Backend.started, Backend.payload, Backend.result, Backend.close_ok, Backend.instances = 0, b"1\n", True, True, []
        self.vault, self.audit = Vault(), Audit()
        self.uid = os.getuid()
        self.gateway = Gateway(self.store, self.vault, self.audit,
            {"lego-prod": dict(enabled=True, read_only_verified=False)}, allowed_uids=[self.uid], backend_type=Backend)

    def tearDown(self): self.tmp.cleanup()

    def request(self, **changes):
        args = dict(action="prepare", target="lego-prod", database="master", sql=PROBE_SQL,
                    timeout=5, max_rows=1, max_bytes=1024)
        args.update(changes)
        return self.gateway.handle(args, self.uid)["review"]

    def approve(self, review, **changes):
        args = dict(action="approve", request_id=review["request_id"], digest=review["digest"], approval_source="explicit-user-chat")
        args.update(changes)
        return self.gateway.handle(args, self.uid)

    def execute(self, review):
        published = []
        result = self.gateway.handle(dict(action="execute", request_id=review["request_id"]), self.uid, publish=published.append)
        return result, published

    def test_prepare_does_not_read_password_or_connect(self):
        review = self.request()
        self.assertEqual((Backend.started, self.vault.password_reads), (0, 0))
        self.assertEqual(review["sql"], PROBE_SQL)
        self.assertIn(review["host_tag"], review["control_sql"]["observer_sql"])
        self.assertIn("resource_max_bytes", review)

    def test_operator_opening_is_database_scoped_and_still_requires_sql_approval(self):
        with self.assertRaises(Denied):
            self.request(database="EbookCms", sql="SELECT DB_NAME();")
        self.gateway.targets["lego-prod"]["operator_authorized_read_databases"] = ["EbookCms"]
        review = self.request(database="EbookCms", sql="SELECT DB_NAME();")
        self.assertFalse(self.gateway.targets["lego-prod"]["read_only_verified"])
        self.assertEqual((Backend.started, self.vault.password_reads), (0, 0))
        result, _ = self.execute(review)
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual((Backend.started, self.vault.password_reads), (0, 0))
        with self.assertRaises(Denied):
            self.request(database="master", sql="SELECT DB_NAME();")

    def test_operator_opening_preserves_read_only_sql_and_stop_controls(self):
        self.gateway.targets["lego-prod"]["operator_authorized_read_databases"] = ["EbookCms"]
        for sql in ("DELETE FROM dbo.Example;", "EXEC dbo.Example;", "SELECT * INTO dbo.Example FROM dbo.Other;",
                    "SELECT NEXT VALUE FOR dbo.OrderSequence AS n;",
                    "SELECT next /*comment*/ value for [dbo].[OrderSequence];"):
            with self.subTest(sql=sql), self.assertRaises(Denied):
                self.request(database="EbookCms", sql=sql)
        self.store.stop("operator_stop")
        with self.assertRaises(Denied):
            self.request(database="EbookCms", sql="SELECT DB_NAME();")
        self.assertEqual((Backend.started, self.vault.password_reads), (0, 0))

    def test_operator_database_allowlist_does_not_accept_string_or_mixed_types(self):
        for malformed in ("EbookCms", ["EbookCms", None], True):
            self.gateway.targets["lego-prod"]["operator_authorized_read_databases"] = malformed
            with self.subTest(allowlist=malformed), self.assertRaises(Denied):
                self.request(database="EbookCms", sql="SELECT DB_NAME();")

    def test_operator_opening_rejects_explicit_remote_references(self):
        self.gateway.targets["lego-prod"]["operator_authorized_read_databases"] = ["EbookCms"]
        for sql in ("SELECT * FROM OtherDb.dbo.T;", "SELECT * FROM OtherDb..T;",
                    "SELECT * FROM [LinkedServer].[OtherDb].[dbo].[T];",
                    'SELECT * FROM "OtherDb"."dbo"."T";',
                    "SELECT * FROM OtherDb /*a*/ . dbo /*b*/ . T;"):
            with self.subTest(sql=sql), self.assertRaises(Denied):
                self.request(database="EbookCms", sql=sql)
        review = self.request(database="EbookCms", sql="SELECT 'a.b.c', 1.5 FROM [dbo].[T]; -- a.b.c")
        self.assertEqual(review["read_access_basis"], "operator_authorized_database_permissions_unverified")
        self.assertFalse(review["indirect_object_dependencies_verified"])
        self.assertEqual((Backend.started, self.vault.password_reads), (0, 0))

    def test_cancel_closed_query_allows_fresh_prepare_but_revokes_old_approval(self):
        old = self.request(); self.approve(old)
        current = self.request(); self.approve(current)
        gateway = self.gateway

        class CancelOnPoll(Backend):
            def poll(self):
                gateway.handle(dict(action="stop"), os.getuid())
                return None

        gateway.backend_type = CancelOnPoll
        result, published = self.execute(current)
        self.assertEqual(result["status"], "stopped")
        self.assertTrue(result["session_closed"])
        self.assertEqual(published, [])
        state = gateway.handle(dict(action="status"), self.uid)
        self.assertFalse(state["halted"])
        self.assertIsNone(state["active"])
        self.assertEqual(state["stop_markers"], [])
        gateway.backend_type = Backend
        stale, _ = self.execute(old)
        self.assertEqual(stale["status"], "approval_required")
        fresh = self.request()
        unapproved, _ = self.execute(fresh)
        self.assertEqual(unapproved["status"], "approval_required")

    def test_cancel_cannot_reopen_failed_or_unconfirmed_state(self):
        self.store.stop("query_failed")
        response = self.gateway.handle(dict(action="stop"), self.uid)
        self.assertTrue(response["halted"])
        self.assertEqual(self.store.status()["reason"], "query_failed")
        with self.assertRaises(Denied):
            self.request()

    def test_parallel_status_settlement_does_not_reintroduce_a_hard_marker(self):
        from db_prod_watchdog import remove_stop_markers, list_stop_markers
        current = self.request(); self.approve(current)
        gateway = self.gateway
        class CancelOnPoll(Backend):
            def poll(self):
                gateway.handle(dict(action="stop"), os.getuid())
                return None
        gateway.backend_type = CancelOnPoll
        original_status = self.store.status
        raced = []
        def racing_status():
            state = original_status()
            if (not raced and state["reason"] == "operator_cancel"
                    and state["halted"] and state["active"] is None):
                raced.append(True)
                markers = gateway._latch_path()
                remove_stop_markers(markers, list_stop_markers(markers))
                self.assertTrue(Store(self.path).clear(state, resume=True, reason="operator_cancel_completed"))
            return state
        with patch.object(self.store, "status", side_effect=racing_status):
            result, _ = self.execute(current)
        self.assertTrue(result["session_closed"])
        self.assertEqual(raced, [True])
        self.assertFalse(gateway.handle(dict(action="status"), self.uid)["halted"])
        self.assertEqual(gateway._stop_markers(), ())

    def test_cancel_during_unconfirmed_cleanup_stays_blocked(self):
        current = self.request(); self.approve(current)
        gateway = self.gateway
        gateway.supervisor_factory = lambda store: Supervisor(store, cleanup_timeout=0.01, poll_interval=0.001)
        class UnconfirmedCancel(Backend):
            def poll(self):
                gateway.handle(dict(action="stop"), os.getuid())
                return None
            def closed(self): return False
        gateway.backend_type = UnconfirmedCancel
        result, _ = self.execute(current)
        self.assertEqual(result["status"], "unconfirmed")
        gateway.handle(dict(action="stop"), self.uid)
        state = gateway.handle(dict(action="status"), self.uid)
        self.assertTrue(state["halted"])
        self.assertIsNotNone(state["active"])
        self.assertEqual(state["reason"], "session_cleanup_unconfirmed")

    def test_independent_cancel_marker_settles_but_emergency_marker_stays(self):
        markers = self.gateway._latch_path()
        create_stop_marker(markers, reason="operator_cancel")
        self.assertFalse(self.gateway.handle(dict(action="status"), self.uid)["halted"])
        create_stop_marker(markers, reason="independent_emergency_stop")
        self.gateway.handle(dict(action="stop"), self.uid)
        self.assertTrue(self.gateway.handle(dict(action="status"), self.uid)["halted"])

    def test_cancel_marker_kind_is_visible_before_diagnostic_body_is_written(self):
        markers = self.gateway._latch_path()
        latched = LatchStore(self.path, markers)
        writing, release = threading.Event(), threading.Event()
        original_write = os.write
        errors = []
        def paused_write(descriptor, payload):
            if payload == b"operator_cancel":
                writing.set()
                if not release.wait(2):
                    raise RuntimeError("fixture_barrier_timeout")
            return original_write(descriptor, payload)
        def create():
            try:
                create_stop_marker(markers, reason="operator_cancel")
            except Exception as error:
                errors.append(error)
        with patch("db_prod_watchdog.os.write", side_effect=paused_write):
            writer = threading.Thread(target=create)
            writer.start()
            try:
                self.assertTrue(writing.wait(1))
                self.assertEqual(latched.status()["reason"], "operator_cancel")
            finally:
                release.set()
                writer.join(2)
        self.assertFalse(writer.is_alive())
        self.assertEqual(errors, [])

    def test_new_emergency_marker_during_cancel_release_wins(self):
        from db_prod_watchdog import remove_stop_markers
        markers = self.gateway._latch_path()
        create_stop_marker(markers, reason="operator_cancel")
        self.store.cancel()
        def racing_remove(path, expected):
            remove_stop_markers(path, expected)
            create_stop_marker(path, reason="independent_emergency_stop")
        with patch("db_prod_gateway.remove_stop_markers", side_effect=racing_remove):
            self.assertFalse(self.gateway._settle_cancel())
        state = self.gateway.handle(dict(action="status"), self.uid)
        self.assertTrue(state["halted"])
        self.assertTrue(state["stop_markers"])

    def test_new_epoch_during_cancel_release_is_not_cleared(self):
        from db_prod_watchdog import remove_stop_markers
        markers = self.gateway._latch_path()
        create_stop_marker(markers, reason="operator_cancel")
        self.store.cancel()
        def racing_remove(path, expected):
            remove_stop_markers(path, expected)
            self.store.stop("audit_unavailable")
        with patch("db_prod_gateway.remove_stop_markers", side_effect=racing_remove):
            self.assertFalse(self.gateway._settle_cancel())
        self.assertTrue(self.store.status()["halted"])
        self.assertEqual(self.store.status()["reason"], "audit_unavailable")

    def test_cancel_release_audit_failure_stays_blocked(self):
        create_stop_marker(self.gateway._latch_path(), reason="operator_cancel")
        self.store.cancel()
        self.audit.fail = True
        with self.assertRaises(Denied):
            self.gateway._settle_cancel()
        self.assertTrue(self.store.status()["halted"])
        self.assertEqual(self.store.status()["reason"], "audit_unavailable")

    def test_cli_cancel_persists_without_daemon_and_preserves_hard_stop(self):
        import db_prod_client as client
        markers = self.gateway._latch_path()
        with patch.object(client, "STATE", self.path.parent), patch.object(client, "STOP_MARKERS", markers), \
                patch.object(client, "rpc", side_effect=OSError("offline")):
            # The CLI's state filename is fixed; give it an isolated fixture.
            cli_path = self.path.parent / "control.sqlite3"
            Store.initialize(cli_path)
            cli_store = Store(cli_path)
            Supervisor(cli_store).resume(lambda: True)
            stopped = client.emergency_stop(persistent=False)
            self.assertTrue(stopped["latch_persisted"])
            self.assertTrue(cli_store.status()["halted"])
            self.assertEqual(cli_store.status()["reason"], "operator_cancel")
            client.emergency_stop(persistent=True)
            client.emergency_stop(persistent=False)
            self.assertEqual(cli_store.status()["reason"], "independent_emergency_stop")

    def test_cli_settled_cancel_reports_current_state_separately_from_receipt(self):
        import db_prod_client as client
        markers = self.gateway._latch_path()
        response = dict(ok=True, halted=False, active=None, phase="idle",
                        ready_for_new_request=True, stop_markers=[])
        with patch.object(client, "STATE", self.path.parent), patch.object(client, "STOP_MARKERS", markers), \
                patch.object(client, "rpc", return_value=response):
            cli_path = self.path.parent / "control.sqlite3"
            Store.initialize(cli_path)
            Supervisor(Store(cli_path)).resume(lambda: True)
            result = client.emergency_stop(persistent=False)
            self.assertTrue(result["session_closed"])
            self.assertFalse(result["halted"])
            self.assertFalse(result["latch_active"])
            self.assertTrue(result["latch_persisted"])
            self.assertIn("request_marker", result)
            self.assertNotIn("stop_marker", result)

    def test_fixed_ten_second_probe_requires_approval_and_does_not_enable_general_sql(self):
        review = self.request(sql=SESSION_VISIBILITY_PROBE_SQL, timeout=20)
        self.assertEqual(review["sql"], SESSION_VISIBILITY_PROBE_SQL)
        self.assertEqual((Backend.started, self.vault.password_reads), (0, 0))
        result, published = self.execute(review)
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual((Backend.started, self.vault.password_reads, published), (0, 0, []))
        for sql in (SESSION_VISIBILITY_PROBE_SQL.replace("00:00:10", "00:00:11"),
                    SESSION_VISIBILITY_PROBE_SQL + "\nSELECT 1;", "SELECT APP_NAME();"):
            with self.subTest(sql=sql), self.assertRaises(Denied):
                self.request(sql=sql, timeout=20)

    def test_fixed_thirty_second_stop_probe_requires_approval(self):
        review = self.request(sql=SESSION_STOP_PROBE_SQL, timeout=40)
        self.assertEqual(review["sql"], SESSION_STOP_PROBE_SQL)
        result, published = self.execute(review)
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual((Backend.started, self.vault.password_reads, published), (0, 0, []))
        for sql in (SESSION_STOP_PROBE_SQL.replace("00:00:30", "00:00:31"),
                    SESSION_STOP_PROBE_SQL + "\nSELECT 1;"):
            with self.subTest(sql=sql), self.assertRaises(Denied):
                self.request(sql=sql, timeout=40)

    def test_keychain_failure_diagnostic_is_returned_and_audited(self):
        review = self.request(); self.approve(review)
        def fail(*_args, **_kwargs):
            raise ProfileError("keychain_access_cancelled")
        self.vault.credentials = fail
        result, published = self.execute(review)
        expected = [{"stage": "credentials", "code": "keychain_access_cancelled"}]
        self.assertFalse(result["ok"])
        self.assertEqual(result["diagnostics"], expected)
        failure = next(detail for event, detail in self.audit.events if event == "execution_failed")
        self.assertEqual(failure["diagnostics"], expected)
        self.assertEqual(failure["run_id"], result["run_id"])
        self.assertEqual((Backend.started, published), (0, []))

    def test_unknown_startup_error_is_not_exposed(self):
        class BrokenBackend(Backend):
            def start(self, run):
                raise RuntimeError("PRIVATE_PASSWORD PRIVATE_SQL")
        self.gateway.backend_type = BrokenBackend
        review = self.request(); self.approve(review)
        result, _ = self.execute(review)
        self.assertEqual(result["diagnostics"], [{"stage": "startup", "code": "internal_error"}])
        self.assertNotIn("PRIVATE", repr(self.audit.events))

    def test_transport_diagnostic_replaces_generic_wrapper_and_is_audited(self):
        class BrokenBackend(Backend):
            def start(self, run):
                self.detail = Diagnostics()
                self.detail.capture("startup", "stderr", b"PRIVATE_HOST: connection refused")
                self.detail.failure("startup", code="startup_failed")
                raise RuntimeError("PRIVATE_DRIVER_DETAIL")
            def diagnostics(self):
                return self.detail.snapshot()
        self.gateway.backend_type = BrokenBackend
        review = self.request(); self.approve(review)
        result, published = self.execute(review)
        self.assertFalse(result["ok"])
        self.assertEqual(result["diagnostics"][0]["code"], "startup_failed")
        self.assertEqual(len(result["diagnostics"]), 1)
        failure = next(detail for event, detail in self.audit.events if event == "execution_failed")
        self.assertEqual(failure["diagnostics"], result["diagnostics"])
        self.assertEqual(published, [])
        self.assertNotIn("PRIVATE", repr(self.audit.events))

    def test_unknown_worker_recovery_failure_keeps_slot_and_returns_diagnostic_once(self):
        class StartupFailure(Backend):
            close_ok = False
            observed = 0
            def start(self, run):
                raise RuntimeError("startup_failed")
            def observe_closed(self, host_tag, timeout=5):
                type(self).observed += 1
                self.detail = Diagnostics()
                self.detail.capture("observer", "stderr", b"PRIVATE_HOST x509: unknown authority")
                self.detail.failure("observer", code="observer_failed")
                return False
            def diagnostics(self):
                return getattr(self, "detail", Diagnostics()).snapshot()
        self.gateway.backend_type = StartupFailure
        self.gateway.supervisor_factory = lambda store: Supervisor(store, cleanup_timeout=0.01, poll_interval=0.001)
        self.gateway.recovery_process_probe = lambda _: None
        self.gateway.recovery_pid_presence_probe = lambda _: False
        self.gateway.recovery_sleep = lambda _: None
        review = self.request(); self.approve(review)
        original, _ = self.execute(review)
        self.assertFalse(original["session_closed"])
        recovery = self.gateway.recovery_prepare({}, self.uid)["review"]
        request = dict(recovery_request_id=recovery["request_id"])
        with self.assertRaises(Denied):
            self.gateway.recovery_execute(recovery["request_id"], self.uid)
        self.assertEqual(StartupFailure.observed, 0)
        self.gateway.recovery_approve(dict(request, digest=recovery["digest"], approval_source="explicit-user-chat"), self.uid)
        with patch("db_prod_gateway.current_user_sqlcmd_absent", return_value=True):
            result = self.gateway.recovery_execute(recovery["request_id"], self.uid)
        self.assertFalse(result["ok"])
        self.assertEqual(StartupFailure.observed, 1)
        self.assertEqual(result["diagnostics"][0]["stage"], "observer")
        self.assertNotIn("PRIVATE", repr(self.audit.events))
        state = self.store.status()
        self.assertEqual(state["active"], original["run_id"])
        self.assertEqual(state["phase"], "unconfirmed")
        self.assertTrue(state["halted"])
        with self.assertRaises(Denied):
            self.gateway.recovery_execute(recovery["request_id"], self.uid)
        with self.store.transaction() as connection:
            row = connection.execute("SELECT status FROM recovery_approvals WHERE id=?", (recovery["request_id"],)).fetchone()
        self.assertEqual(row["status"], "consumed")

    def test_no_approval_no_password_or_connection(self):
        result, published = self.execute(self.request())
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual((Backend.started, self.vault.password_reads, published), (0, 0, []))

    def test_bad_digest_and_source_do_not_record_approval(self):
        review = self.request()
        for change in ({"digest":"bad"}, {"approval_source":"agent-auto"}):
            with self.assertRaises(Denied): self.approve(review, **change)
        self.assertFalse(any(event == "approved" for event, _ in self.audit.events))

    def test_unknown_uid_cannot_prepare(self):
        with self.assertRaises(Denied): self.gateway.handle(dict(action="status"), self.uid+10000)

    def test_profile_change_invalidates_approval_before_connect(self):
        review = self.request(); self.approve(review)
        self.vault.value["host"] = "changed.invalid"
        result, _ = self.execute(review)
        self.assertFalse(result["ok"])
        self.assertEqual(Backend.started, 0)
        self.assertTrue(self.store.status()["halted"])

    def test_stop_revokes_approval_without_connection(self):
        review = self.request(); self.approve(review)
        self.gateway.handle(dict(action="stop"), self.uid)
        result, published = self.execute(review)
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual((Backend.started, published), (0, []))

    def test_restart_halt_without_markers_requires_exact_epoch_for_resume(self):
        self.store.stop("service_started_requires_operator_resume")
        status = self.gateway.handle(dict(action="status"), self.uid)
        self.assertEqual(status["stop_markers"], [])
        request = dict(action="resume", expected_epoch=status["epoch"],
                       expected_stop_generation=status["stop_generation"], expected_stop_markers=[])
        result = self.gateway.handle(request, self.uid)
        self.assertFalse(result["halted"])
        self.assertEqual(Backend.started, 0)
        with self.assertRaises(Denied):
            self.gateway.handle(request, self.uid)

    def test_success_receipt_then_bounded_chunks(self):
        Backend.payload = b"x" * 300000
        review = self.request(max_bytes=400000, max_rows=None); self.approve(review)
        result, receipts = self.execute(review)
        self.assertTrue(result["ok"])
        self.assertLess(len(str(receipts[0])), 1024)
        assembled = bytearray()
        while True:
            chunks = []
            self.gateway.handle(dict(action="fetch", run_id=result["run_id"], offset=len(assembled)), self.uid, publish=chunks.append)
            chunk = chunks[0]
            assembled.extend(base64.b64decode(chunk["data_base64"]))
            if chunk["final"]: break
        self.assertEqual(assembled, Backend.payload)
        self.assertFalse(self.gateway.results)

    def test_real_unix_socket_client_receives_large_result_with_small_send_buffer(self):
        from contextlib import redirect_stdout, redirect_stderr
        from db_prod_gateway import Handler, Server
        import db_prod_client

        class SmallBufferHandler(Handler):
            def setup(self):
                super().setup()
                self.request.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)

        Backend.payload = b"x" * 50221
        review = self.request(max_bytes=65536, max_rows=None)
        self.approve(review)
        path = str(Path(self.tmp.name) / "fixture.sock")
        with Server(path, SmallBufferHandler) as server:
            server.gateway = self.gateway
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            stdout, stderr = io.StringIO(), io.StringIO()
            try:
                with patch.object(db_prod_client, "SOCKET", path), patch.object(sys, "argv", [
                        "db_prod_client.py", "execute", review["request_id"]]), redirect_stdout(stdout), redirect_stderr(stderr):
                    code = db_prod_client.main()
                self.assertEqual(code, 0, stderr.getvalue())
                result = json.loads(stdout.getvalue())
                self.assertEqual(result["output"].encode(), Backend.payload)
                self.assertFalse(self.gateway.results)
                self.assertIsNone(self.store.status()["active"])
            finally:
                server.shutdown()
                thread.join(timeout=2)

    def test_cli_time_only_default_and_output_larger_than_eight_mib(self):
        from contextlib import redirect_stdout
        import db_prod_client
        with patch.object(db_prod_client, "require_current_gateway"), patch.object(
                db_prod_client, "rpc", return_value={"ok": True}) as request, patch.object(
                sys, "argv", ["db_prod_client.py", "prepare", "--target", "lego-prod",
                              "--database", "master", "--timeout", "15"]), patch.object(
                sys, "stdin", io.StringIO("SELECT 1;")), redirect_stdout(io.StringIO()):
            self.assertEqual(db_prod_client.main(), 0)
            self.assertIsNone(request.call_args.args[0]["max_rows"])
            self.assertIsNone(request.call_args.args[0]["max_bytes"])
        review = self.request(max_rows=None, max_bytes=None)
        self.assertIsNone(review["resource_max_bytes"])

        payload = b"x" * (8 * 1024 * 1024 + 1)
        def request(message):
            if message["action"] == "execute":
                return dict(ok=True, session_closed=True, run_id="fixture",
                            output_bytes=len(payload), output_sha256=hashlib.sha256(payload).hexdigest())
            offset = message["offset"]
            chunk = payload[offset:offset+2048]
            end = offset + len(chunk)
            return dict(ok=True, offset=offset, next_offset=end,
                        data_base64=base64.b64encode(chunk).decode(), final=end == len(payload))
        output = io.StringIO()
        with patch.object(db_prod_client, "require_current_gateway"), patch.object(
                db_prod_client, "rpc", side_effect=request), patch.object(
                sys, "argv", ["db_prod_client.py", "execute", "fixture"]), redirect_stdout(output):
            self.assertEqual(db_prod_client.main(), 0)
        self.assertEqual(json.loads(output.getvalue())["output"].encode(), payload)

    def test_gateway_observer_timeout_covers_full_session_removal_grace(self):
        from db_prod_transport import DEFAULT_OBSERVER_TIMEOUT
        review = self.request(timeout=20)
        self.approve(review)
        result, _ = self.execute(review)
        self.assertTrue(result["ok"])
        self.assertEqual(Backend.instances[-1].options["observer_timeout"], DEFAULT_OBSERVER_TIMEOUT)

    def test_stop_discards_unread_result(self):
        review = self.request(); self.approve(review)
        result, _ = self.execute(review)
        self.gateway.handle(dict(action="stop"), self.uid)
        with self.assertRaises(Denied):
            self.gateway.handle(dict(action="fetch", run_id=result["run_id"], offset=0), self.uid, publish=lambda _:None)

    def test_finish_commit_failure_never_releases_plaintext(self):
        review = self.request(); self.approve(review)
        original = self.store.transaction
        failed = []

        @contextmanager
        def fail_finish_commit():
            with original() as connection:
                yield connection
                if self.gateway.results and not failed:
                    failed.append(True)
                    raise sqlite3.OperationalError("synthetic completion commit failure")

        self.store.transaction = fail_finish_commit
        def unavailable_stop(*args, **kwargs):
            raise sqlite3.OperationalError("synthetic stop write unavailable")
        self.store.stop = unavailable_stop
        receipts = []
        result = self.gateway.handle(dict(action="execute", request_id=review["request_id"]),
                                     self.uid, publish=receipts.append)
        self.assertFalse(result["ok"])
        self.assertEqual(len(receipts), 1)
        self.assertFalse(self.gateway.results)
        chunks = []
        with self.assertRaises(Denied):
            self.gateway.handle(dict(action="fetch", run_id=receipts[0]["run_id"], offset=0),
                                self.uid, publish=chunks.append)
        self.assertEqual(chunks, [])
        self.assertIsNotNone(self.store.status()["active"])
        self.assertFalse(self.store.status()["halted"])

    def test_fetch_receipt_race_waits_for_completion_commit(self):
        review = self.request(); self.approve(review)
        chunks, errors, threads = [], [], []

        def publish(receipt):
            def fetch():
                try:
                    self.gateway.handle(dict(action="fetch", run_id=receipt["run_id"], offset=0),
                                        self.uid, publish=chunks.append)
                except Exception as error:
                    errors.append(error)
            thread = threading.Thread(target=fetch)
            threads.append(thread)
            thread.start()
            time.sleep(0.02)
            self.assertEqual(chunks, [])

        result = self.gateway.handle(dict(action="execute", request_id=review["request_id"]),
                                     self.uid, publish=publish)
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
        self.assertTrue(result["ok"])
        self.assertEqual(errors, [])
        self.assertEqual(base64.b64decode(chunks[0]["data_base64"]), Backend.payload)

    def test_client_rejects_stale_daemon_and_keeps_error_text_private(self):
        from db_prod_client import require_current_gateway, safe_client_error
        from db_prod_gateway import current_source_fingerprint, RUNTIME_FINGERPRINT
        status = self.gateway.handle(dict(action="status"), self.uid)
        self.assertEqual(status["runtime_fingerprint"], RUNTIME_FINGERPRINT)
        for actual in (None, "older-build"):
            with patch("db_prod_client.rpc", return_value=dict(ok=True, runtime_fingerprint=actual)):
                with self.assertRaisesRegex(RuntimeError, "gateway_restart_required"):
                    require_current_gateway()
        with patch("db_prod_client.rpc", return_value=dict(ok=True, runtime_fingerprint=current_source_fingerprint())):
            require_current_gateway()
        self.assertEqual(safe_client_error(RuntimeError("PRIVATE_HOST PRIVATE_RESULT")), "client_request_failed")
        self.assertEqual(safe_client_error(RuntimeError("result_commit_pending")), "result_commit_pending")

    def test_replay_never_reconnects(self):
        review = self.request(); self.approve(review)
        self.execute(review)
        with self.assertRaises(Denied): self.execute(review)
        self.assertEqual(Backend.started, 1)

    def test_audit_failure_blocks_execution(self):
        review = self.request(); self.approve(review)
        self.audit.fail = True
        with self.assertRaises(Denied): self.execute(review)
        self.assertEqual(Backend.started, 0)
        self.assertTrue(self.store.status()["halted"])

    def test_query_error_cancels_and_latches(self):
        review = self.request(); self.approve(review)
        Backend.result = False
        result, published = self.execute(review)
        self.assertFalse(result["ok"])
        self.assertTrue(result["session_closed"])
        self.assertTrue(Backend.instances[0].cancelled)
        self.assertEqual(published, [])
        self.assertTrue(self.store.status()["halted"])

    def test_global_slot_refuses_other_requests(self):
        first, second = self.request(), self.request()
        self.approve(first); self.approve(second)
        Backend.result = None
        thread = threading.Thread(target=lambda:self.execute(first))
        thread.start()
        try:
            deadline = time.monotonic()+2
            while not Backend.started and time.monotonic()<deadline: time.sleep(0.01)
            result, _ = self.execute(second)
            self.assertEqual(result["status"], "busy")
            self.assertEqual(Backend.started, 1)
        finally:
            self.store.stop(); thread.join(3)
        self.assertFalse(thread.is_alive())

    def test_latch_survives_new_store_object(self):
        latch = Path(self.tmp.name)/"stop"
        latch.touch()
        store = LatchStore(self.path, latch)
        self.assertTrue(store.status()["halted"])
        self.assertTrue(LatchStore(self.path, latch).status()["halted"])

    def test_read_parser_blocks_explicit_and_implicit_procedures(self):
        for sql in ("dbo.ForbiddenWrite;", "sp_who;", "[dbo].[ForbiddenWrite];", "EXEC dbo.ForbiddenWrite;",
                    "CREATE OR ALTER PROC p AS SELECT 1;", "WITH x AS (SELECT 1 a) DELETE FROM t;", "SELECT 1 INTO t;"):
            with self.subTest(sql=sql), self.assertRaises(Denied): validate_read_sql(sql)
        validate_read_sql("/* outer /* inner */ comment */ WITH x AS (SELECT 'DROP' a) SELECT a FROM x;")

    def test_profile_parser_rejects_hidden_suffix_duplicate_or_bad_port(self):
        for raw in ('{"host":"x","port":1433,"account":"a"}\u0000junk',
                    '{"host":"x","host":"y","port":1433,"account":"a"}',
                    '{"host":"x","port":true,"account":"a"}'):
            with self.assertRaises(ProfileError): parse_profile(raw)

    def test_stop_then_observer_recovery_approval_fences_and_keeps_halted_idle(self):
        RecoveryBackend.started = 0
        RecoveryBackend.result = None
        RecoveryBackend.close_ok = False
        RecoveryBackend.observed = 0
        worker_fenced = {"value": False}

        def probe(pid):
            if pid != 222:
                return None
            return "different-birth" if worker_fenced["value"] else "worker-birth"

        gateway = Gateway(
            self.store,
            self.vault,
            self.audit,
            {"lego-prod": dict(enabled=True, read_only_verified=False)},
            allowed_uids=[self.uid],
            backend_type=RecoveryBackend,
            recovery_process_probe=probe,
            recovery_pid_presence_probe=lambda _pid: False,
            recovery_sleep=lambda _seconds: None,
            supervisor_factory=lambda store: Supervisor(store, cleanup_timeout=0.01, poll_interval=0.001),
        )
        review = gateway.prepare(
            dict(target="lego-prod", database="master", sql=PROBE_SQL,
                 timeout=5, max_rows=1, max_bytes=1024), self.uid
        )["review"]
        gateway.handle(dict(action="approve", request_id=review["request_id"], digest=review["digest"],
                            approval_source="explicit-user-chat"), self.uid)
        execution = []
        worker = threading.Thread(
            target=lambda: execution.append(
                gateway.handle(dict(action="execute", request_id=review["request_id"]), self.uid,
                               publish=lambda _value: None)
            )
        )
        worker.start()
        deadline = time.monotonic() + 2
        while RecoveryBackend.started == 0 and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertEqual(RecoveryBackend.started, 1)
        gateway.handle(dict(action="stop"), self.uid)
        worker.join(2)
        self.assertFalse(worker.is_alive())
        worker_fenced["value"] = True
        orphan = self.store.status()
        self.assertEqual(orphan["phase"], "unconfirmed")
        self.assertIsNotNone(orphan["active"])
        recovery = gateway.handle(dict(action="recovery_prepare"), self.uid)
        recovery_review = recovery["review"]
        self.assertIn("observer_sql", recovery_review)
        gateway.handle(
            dict(action="recovery_approve", recovery_request_id=recovery_review["recovery_request_id"],
                 digest=recovery_review["digest"], approval_source="explicit-user-chat"), self.uid
        )
        result = gateway.handle(
            dict(action="recovery_execute", recovery_request_id=recovery_review["recovery_request_id"]), self.uid
        )
        self.assertTrue(result["ok"])
        state = self.store.status()
        self.assertTrue(state["halted"])
        self.assertIsNone(state["active"])
        self.assertEqual(state["phase"], "idle")
        self.assertEqual(RecoveryBackend.observed, 1)

    def test_resume_requires_fresh_epoch_and_does_not_clear_new_stop(self):
        latch = Path(self.tmp.name) / "resume-stop.latch"
        latch.touch()
        store = LatchStore(self.path, latch)
        gateway = Gateway(
            store,
            self.vault,
            self.audit,
            {"lego-prod": dict(enabled=True, read_only_verified=False)},
            allowed_uids=[self.uid],
            backend_type=Backend,
        )
        stopped = store.stop("operator_stop")
        status = gateway.handle(dict(action="status"), self.uid)
        self.assertEqual(status["epoch"], stopped["epoch"])
        self.assertEqual(status["stop_generation"], stopped["epoch"])
        store.stop("new_stop_during_prompt")
        with self.assertRaises(Denied) as error:
            gateway.handle(
                dict(action="resume", expected_epoch=status["epoch"],
                     expected_stop_generation=status["stop_generation"],
                     expected_stop_markers=[latch.name]), self.uid
            )
        self.assertEqual(str(error.exception), "resume_confirmation_changed")
        self.assertTrue(latch.exists())
        self.assertTrue(store.status()["halted"])

    def test_resume_removes_latch_only_after_matching_confirmation(self):
        latch = Path(self.tmp.name) / "resume-valid.latch"
        latch.touch()
        store = LatchStore(self.path, latch)
        gateway = Gateway(
            store,
            self.vault,
            self.audit,
            {"lego-prod": dict(enabled=True, read_only_verified=False)},
            allowed_uids=[self.uid],
            backend_type=Backend,
        )
        stopped = store.stop("operator_stop")
        result = gateway.handle(
            dict(action="resume", expected_epoch=stopped["epoch"],
                 expected_stop_generation=stopped["epoch"],
                 expected_stop_markers=[latch.name]), self.uid
        )
        self.assertTrue(result["ok"])
        self.assertFalse(latch.exists())
        self.assertFalse(store.status()["halted"])

    def test_independent_marker_latches_generic_gateway_and_coordinated_resume(self):
        gateway = self.gateway
        markers = Path(self.path).parent / "stop.d"
        marker = create_stop_marker(markers, reason="independent_emergency_stop")
        status = gateway.handle(dict(action="status"), self.uid)
        self.assertTrue(status["halted"])
        self.assertEqual(status["stop_markers"], [marker])
        resumed = gateway.handle(
            dict(action="resume", expected_epoch=status["epoch"],
                 expected_stop_generation=status["stop_generation"],
                 expected_stop_markers=[marker]), self.uid
        )
        self.assertFalse(resumed["halted"])


if __name__ == "__main__": unittest.main()
