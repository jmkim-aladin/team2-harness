"""Synthetic subprocess tests for the production-shaped sqlcmd transport."""

from pathlib import Path
import os
import json
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_prod_transport import (  # noqa: E402
    Credentials,
    ObserverResult,
    DEFAULT_CHILD_HOME,
    DEFAULT_CHILD_LOCALE,
    DEFAULT_CHILD_PATH,
    OBSERVER_MAX_BYTES,
    OBSERVER_MAX_ROWS,
    OBSERVER_MAX_TIMEOUT,
    STARTUP_SQL,
    SqlcmdBackend,
    TransportError,
    default_command_factory,
    default_env_factory,
    control_sql,
    review_sql,
)


_EOF = object()


class QueueStream:
    def __init__(self):
        self.items = queue.Queue()

    def feed(self, value):
        self.items.put(value)

    def close(self):
        self.items.put(_EOF)

    def read(self, _size):
        value = self.items.get(timeout=2)
        if value is _EOF:
            return b""
        return value


class FakeStdin:
    def __init__(self, process):
        self.process = process
        self.data = bytearray()
        self.closed = False

    def write(self, value):
        self.data.extend(value)
        if b"SQLCMD_READY" in self.data and not self.process.startup_seen:
            self.process.startup_seen = True
            self.process.stdout.feed(b"SQLCMD_READY\n")
        return len(value)

    def flush(self):
        return None

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.process.query_closed(self.data)


class ShortWriteStdin(FakeStdin):
    """Raw-pipe substitute that deliberately returns partial writes."""

    def __init__(self, process, max_chunk=3):
        super().__init__(process)
        self.max_chunk = max_chunk

    def write(self, value):
        value = bytes(value)
        return super().write(value[: self.max_chunk])


class FakeProcess:
    def __init__(self, *, output=b"", stderr=b"", finish_on_query=True):
        self.stdout = QueueStream()
        self.stderr = QueueStream()
        self.stdin = FakeStdin(self)
        self.returncode = None
        self.output = output
        self.error = stderr
        self.finish_on_query = finish_on_query
        self.startup_seen = False
        self.signals = []
        self.pid = None

    def query_closed(self, data):
        if not self.startup_seen or data == STARTUP_SQL.encode("utf-8"):
            # The startup stream remains open.  Closing it before approved SQL
            # is a cancellation/handshake failure, not query completion.
            return
        if self.finish_on_query:
            self.stdout.feed(self.output)
            self.stderr.feed(self.error)
            self.stdout.close()
            self.stderr.close()
            self.returncode = 0 if not self.error else 1

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        del timeout
        if self.returncode is None:
            self.returncode = 130
        return self.returncode

    def send_signal(self, sig):
        self.signals.append(sig)
        self.returncode = 130
        self.stdout.close()
        self.stderr.close()

    def kill(self):
        self.send_signal(9)


class ShortWriteProcess(FakeProcess):
    def __init__(self, **kwargs):
        max_chunk = kwargs.pop("write_chunk", 3)
        super().__init__(**kwargs)
        self.stdin = ShortWriteStdin(self, max_chunk=max_chunk)


class ProcessFactory:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.kwargs = {}
        self.processes = []

    def __call__(self, argv, **kwargs):
        self.kwargs["argv"] = argv
        self.kwargs["popen"] = kwargs
        process = FakeProcess(**self.options)
        self.processes.append(process)
        return process


class ShortWriteFactory(ProcessFactory):
    def __call__(self, argv, **kwargs):
        self.kwargs["argv"] = argv
        self.kwargs["popen"] = kwargs
        process = ShortWriteProcess(**self.options)
        self.processes.append(process)
        return process


class ObserverProcess:
    def __init__(self, *, stdout=b"1 0\n", stderr=b"", returncode=0):
        self.stdin = object()
        self.stdout_payload = stdout
        self.stderr_payload = stderr
        self.returncode = returncode
        self.communicate_input = None
        self.communicate_timeout = None
        self.signals = []

    def communicate(self, *, input=None, timeout=None):
        self.communicate_input = input
        self.communicate_timeout = timeout
        return self.stdout_payload, self.stderr_payload

    def poll(self):
        return self.returncode

    def kill(self):
        self.signals.append(9)
        self.returncode = 137

    def wait(self, timeout=None):
        del timeout
        return self.returncode


class ObserverProcessFactory:
    def __init__(self, **kwargs):
        self.process = ObserverProcess(**kwargs)
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.process


def backend(*, output=b"1\n", stderr=b"", observer=True, factory=None, host_tag=None, **kwargs):
    credentials = {"host": "prod.example", "port": 1433, "account": "reader", "password": "secret"}
    observer_credentials = {
        "host": "prod.example",
        "port": 1433,
        "account": "session_observer",
        "password": "observer-secret",
    }
    factory = factory or ProcessFactory(output=output, stderr=stderr, **kwargs)
    if observer is True:
        runner = lambda *_args: ObserverResult(True, 0)
    elif observer is False:
        runner = lambda *_args: ObserverResult(False, 0)
    else:
        runner = observer
    return (
        SqlcmdBackend(
            credentials,
            "ProdDb",
            observer_credentials=observer_credentials,
            popen_factory=factory,
            observer_runner=runner,
            host_tag=host_tag,
            startup_timeout=0.2,
            cancel_grace=0.03,
        ),
        factory,
    )


def observer_backend(*, stdout=b"1 0\n", stderr=b"", returncode=0, host_tag="t2q-recovery"):
    credentials = {
        "host": "prod.example",
        "port": 1433,
        "account": "session_observer",
        "password": "observer-secret",
    }
    factory = ObserverProcessFactory(
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
    )
    return (
        SqlcmdBackend(
            credentials,
            "ProdDb",
            observer_credentials=credentials,
            popen_factory=factory,
            host_tag=host_tag,
            observer_timeout=60,
        ),
        factory,
    )


class TransportTests(unittest.TestCase):
    def test_exited_worker_with_pending_reader_cannot_release_results(self):
        instance, _factory = backend()
        instance.start("run")
        instance.dispatch("SELECT 1;", {"timeout": 5, "max_rows": 1})
        while instance.poll() is None:
            time.sleep(0.01)
        self.assertTrue(instance.poll())
        release = threading.Event()
        reader = threading.Thread(target=release.wait, daemon=True)
        reader.start()
        instance._stdout_thread = reader
        instance._closed_confirmation = True
        try:
            with self.assertRaises(TransportError):
                instance.output_bytes()
            self.assertFalse(instance.poll())
            self.assertEqual(instance.failure_reason, "worker_output_unconfirmed")
        finally:
            release.set()
            reader.join(timeout=1)
        self.assertFalse(instance.poll())
        with self.assertRaises(TransportError):
            instance.output_bytes()

    def test_go_row_framing_is_invariant_under_pipe_chunk_boundaries(self):
        for payload, succeeds in ((b"1\n\n", True), (b"1\r\n\r\n", True),
                                  (b"\r\n\r\n", True), (b"1\n\r", False),
                                  (b"1\n2\n\n", False), (b"\r\n\r\n\r\n", False)):
            partitions = [[payload[:i], payload[i:]] for i in range(1, len(payload))]
            partitions += [[bytes([byte]) for byte in payload], [payload]]
            for chunks in partitions:
                with self.subTest(payload=payload, chunks=chunks):
                    worker, _ = backend()
                    worker._ready.set()
                    worker._query_collecting = True
                    worker._max_rows = 1
                    for chunk in chunks:
                        worker._record_stdout(chunk)
                    worker._check_row_limit(final=True)
                    self.assertEqual(worker.failure_reason is None, succeeds)

    def test_observer_accepts_go_client_result_terminator(self):
        worker, factory = observer_backend(stdout=b"                     1             0\n\n")
        self.assertTrue(worker.observe_closed("t2q-recovery"))
        self.assertEqual(len(factory.calls), 1)

    def test_go_result_terminator_does_not_hide_extra_or_empty_data_rows(self):
        for output, expected in ((b"1\n\n", True), (b"\n\n", True),
                                 (b"1\n2\n\n", False), (b"\n\n\n", False)):
            with self.subTest(output=output):
                worker, _ = backend(output=output)
                worker.start("framing")
                worker.dispatch("SELECT 1;", {"timeout": 1, "max_rows": 1, "max_bytes": 256})
                deadline = time.monotonic() + 1
                result = worker.poll()
                while result is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                    result = worker.poll()
                self.assertIs(result, expected)
                if expected:
                    self.assertTrue(worker.closed())
                    self.assertEqual(worker.output_bytes(), output)
                else:
                    self.assertEqual(worker.failure_reason, "output_rows_exceeded")

    def test_startup_stderr_and_observer_failure_are_separate_diagnostics(self):
        process = FakeProcess()
        # Exit before the handshake, with an error split across pipe reads.
        process.stdin = type("BrokenPipe", (), {"write": lambda *_: (_ for _ in ()).throw(BrokenPipeError())})()
        process.stderr.feed(b"PRIVATE_HOST PRIVATE_ACCOUNT PRIVATE_PASSWORD x5")
        process.stderr.feed(b"09: certificate signed by unknown authority")
        process.stderr.close()
        process.stdout.close()
        process.returncode = 1
        worker, _ = backend(factory=lambda *_a, **_kw: process, observer=False)
        with self.assertRaises(TransportError):
            worker.start("diagnostics")
        self.assertFalse(worker.closed())
        diagnostic = {item["stage"]: item for item in worker.diagnostics()}
        self.assertEqual(diagnostic["startup"]["code"], "startup_write_failed")
        self.assertEqual(diagnostic["startup"]["sources"]["stderr"]["signatures"][0]["category"], "tls_certificate")
        self.assertEqual(diagnostic["observer"]["code"], "observer_permission_denied")
        self.assertNotIn("PRIVATE", json.dumps(diagnostic))

    def test_spawn_os_error_is_retained(self):
        def missing(*_a, **_kw):
            raise FileNotFoundError(2, "PRIVATE_PATH")
        worker, _ = backend(factory=missing)
        with self.assertRaises(TransportError):
            worker.start("missing")
        item = worker.diagnostics()[0]
        self.assertEqual((item["code"], item["errno"]), ("process_start_failed", 2))
        self.assertNotIn("PRIVATE", json.dumps(item))

    def test_query_diagnostics_exclude_result_stdout_and_error_values(self):
        worker, _ = backend(output=b"PRIVATE_RESULT\n", stderr=b"Msg 229 permission was denied PRIVATE_SQL")
        worker.start("query-diagnostics")
        worker.dispatch("SELECT 1;", {"max_rows": 10, "max_bytes": 1024, "timeout": 1})
        deadline = time.monotonic() + 1
        outcome = worker.poll()
        while outcome is None and time.monotonic() < deadline:
            time.sleep(0.01)
            outcome = worker.poll()
        self.assertIs(outcome, False)
        self.assertTrue(worker.closed())
        diagnostic = {item["stage"]: item for item in worker.diagnostics()}
        self.assertEqual(diagnostic["query"]["code"], "worker_error_output")
        self.assertNotIn("startup", diagnostic)
        self.assertNotIn("stdout", diagnostic["query"]["sources"])
        self.assertEqual(diagnostic["query"]["sources"]["stderr"]["sql_error_numbers"], [229])
        self.assertNotIn("PRIVATE", json.dumps(diagnostic))

    def test_observer_stderr_is_retained_without_retry_or_secrets(self):
        worker, factory = observer_backend(stderr=b"Msg 18456 Login failed for user PRIVATE_ACCOUNT", returncode=1)
        self.assertFalse(worker.observe_closed("t2q-recovery"))
        self.assertFalse(worker.observe_closed("t2q-recovery"))
        self.assertEqual(len(factory.calls), 1)
        item = worker.diagnostics()[0]
        self.assertEqual((item["stage"], item["exit_code"]), ("observer", 1))
        self.assertEqual(item["sources"]["stderr"]["sql_error_numbers"], [18456])
        self.assertNotIn("PRIVATE", json.dumps(item))

    def test_default_argv_and_environment_keep_connection_values_out_of_argv(self):
        credentials = Credentials.from_value(
            {"host": "db.example", "port": 1433, "account": "reader", "password": "pw"}
        )
        argv = default_command_factory(credentials, "ProdDb", "t2q-run", 3)
        self.assertEqual(argv[0], "/opt/homebrew/bin/sqlcmd")
        self.assertEqual(argv[argv.index("-i") + 1], "/dev/stdin")
        self.assertEqual(argv[argv.index("-N") + 1], "true")
        self.assertIn("-x", argv)
        self.assertNotIn("-X1", argv)
        self.assertIn("-C", argv)
        self.assertNotIn("-S", argv)
        self.assertNotIn("-U", argv)
        self.assertNotIn("pw", argv)
        env = default_env_factory(credentials)
        self.assertEqual(env["SQLCMDSERVER"], "db.example,1433")
        self.assertEqual(env["SQLCMDUSER"], "reader")
        self.assertEqual(env["SQLCMDPASSWORD"], "pw")

    def test_default_environment_does_not_inherit_sqlcmd_config_or_unrelated_values(self):
        credentials = Credentials.from_value(
            {"host": "db.example", "port": 1433, "account": "reader", "password": "pw"}
        )
        inherited = {
            "PATH": "/attacker/bin",
            "HOME": "/Users/other",
            "LANG": "ko_KR.UTF-8",
            "LC_ALL": "ko_KR.UTF-8",
            "LC_CTYPE": "ko_KR.UTF-8",
            "SQLCMDINI": "/tmp/unapproved-startup.sql",
            "SQLCMDDBNAME": "other_db",
            "SQLCMDCOLORSCHEME": "dark",
            "PYTHONPATH": "/tmp/agent-code",
            "AWS_SECRET_ACCESS_KEY": "unrelated-secret",
            "TERM": "xterm-256color",
        }
        with patch.dict(os.environ, inherited, clear=True):
            env = default_env_factory(credentials)

        self.assertEqual(
            set(env),
            {
                "PATH",
                "HOME",
                "LANG",
                "LC_ALL",
                "LC_CTYPE",
                "SQLCMDSERVER",
                "SQLCMDUSER",
                "SQLCMDPASSWORD",
            },
        )
        self.assertEqual(env["PATH"], DEFAULT_CHILD_PATH)
        self.assertEqual(env["HOME"], DEFAULT_CHILD_HOME)
        self.assertEqual(env["LANG"], DEFAULT_CHILD_LOCALE)
        self.assertEqual(env["LC_ALL"], DEFAULT_CHILD_LOCALE)
        self.assertEqual(env["LC_CTYPE"], DEFAULT_CHILD_LOCALE)
        for key in (
            "SQLCMDINI",
            "SQLCMDDBNAME",
            "SQLCMDCOLORSCHEME",
            "PYTHONPATH",
            "AWS_SECRET_ACCESS_KEY",
            "TERM",
        ):
            self.assertNotIn(key, env)

    def test_credentials_are_snapshot_and_repr_does_not_reveal_password(self):
        source = {"host": "db", "port": 1433, "account": "u", "password": "pw"}
        credentials = Credentials.from_value(source)
        source["password"] = "changed"
        self.assertEqual(credentials.password, "pw")
        with self.assertRaises(Exception):
            credentials.password = "changed"
        self.assertNotIn("pw", repr(credentials))

    def test_review_sql_contains_only_transport_control_batches(self):
        reviewed = review_sql("t2q-fixed")
        self.assertIn("SET NOCOUNT ON", reviewed["setup_sql"])
        self.assertIn("VIEW SERVER STATE", reviewed["observer_sql"])
        self.assertIn("VIEW SERVER PERFORMANCE STATE", reviewed["observer_sql"])
        self.assertIn("s.host_name = N't2q-fixed'", reviewed["observer_sql"])
        self.assertIn("s.session_id <> @@SPID", reviewed["observer_sql"])

    def test_observe_closed_runs_observer_without_start_or_user_sql(self):
        instance, factory = observer_backend()
        self.assertIsNone(instance.process)
        self.assertTrue(instance.observe_closed("t2q-recovery", timeout=5))
        self.assertEqual(len(factory.calls), 1)
        self.assertEqual(
            factory.process.communicate_input,
            control_sql("t2q-recovery").encode("utf-8"),
        )
        self.assertNotIn(STARTUP_SQL.encode("utf-8"), factory.process.communicate_input)
        self.assertEqual(factory.process.communicate_timeout, OBSERVER_MAX_TIMEOUT)
        self.assertEqual(instance.host_tag, "t2q-recovery")
        self.assertEqual(instance.observer_host_tag, "t2q-recovery-observer")
        self.assertIsNone(instance.identity)

    def test_observe_closed_failure_is_latched_to_one_observer_call(self):
        for kwargs in (
            {"stdout": b"0 0\n"},
            {"stdout": b"1 0\n", "returncode": 1},
        ):
            with self.subTest(kwargs=kwargs):
                instance, factory = observer_backend(**kwargs)
                self.assertFalse(instance.observe_closed("t2q-recovery"))
                self.assertFalse(instance.observe_closed("t2q-recovery"))
                self.assertEqual(len(factory.calls), 1)

    def test_observe_closed_requires_configured_tag_and_timeout_cap(self):
        instance, factory = observer_backend()
        self.assertFalse(instance.observe_closed("other-tag", timeout=5))
        self.assertFalse(instance.observe_closed("t2q-recovery", timeout=5.1))
        self.assertEqual(factory.calls, [])

    def test_observe_closed_rejects_non_one_row_two_integer_observer_output(self):
        bad_outputs = (
            b"1 0\n1 0\n",
            b"1 0 7\n",
            b"1 x\n",
            b"1 0\n" + b"x" * OBSERVER_MAX_BYTES,
        )
        for output in bad_outputs:
            with self.subTest(output=output[:24]):
                instance, _factory = observer_backend(stdout=output)
                self.assertFalse(instance.observe_closed("t2q-recovery"))

    def test_observe_closed_rejects_stderr_nonzero_permission_and_exit(self):
        for kwargs in (
            {"stderr": b"diagnostic"},
            {"stdout": b"0 0\n"},
            {"stdout": b"1 0\n", "returncode": 1},
        ):
            with self.subTest(kwargs=kwargs):
                instance, _factory = observer_backend(**kwargs)
                self.assertFalse(instance.observe_closed("t2q-recovery"))

    def test_observer_limits_are_exported_and_normal_timeout_is_capped(self):
        self.assertEqual(OBSERVER_MAX_TIMEOUT, 5.0)
        self.assertEqual(OBSERVER_MAX_ROWS, 1)
        self.assertEqual(OBSERVER_MAX_BYTES, 256)
        instance, _factory = observer_backend()
        self.assertEqual(instance.observer_timeout, OBSERVER_MAX_TIMEOUT)

    def test_start_uses_configured_tag_and_does_not_send_user_sql(self):
        instance, factory = backend(host_tag="t2q-reviewed")
        identity = instance.start("run-created-later")
        self.assertEqual(identity["host_tag"], "t2q-reviewed")
        self.assertEqual(instance.host_tag, "t2q-reviewed")
        self.assertNotIn(b"SELECT", factory.processes[0].stdin.data)
        instance.cancel()

    def test_dispatch_writes_approved_sql_exactly_once_and_returns_result(self):
        instance, factory = backend()
        instance.start("run")
        sql = "SELECT 'GO' AS value;"
        instance.dispatch(sql, {"timeout": 5, "max_rows": 2, "max_bytes": 100})
        deadline = time.monotonic() + 1
        while instance.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(instance.poll())
        data = bytes(factory.processes[0].stdin.data)
        self.assertEqual(data.count(sql.encode()), 1)
        self.assertTrue(data.endswith(sql.encode()))
        self.assertTrue(instance.closed())
        self.assertEqual(instance.output_bytes(), b"1\n")

    def test_startup_and_query_write_all_handles_short_raw_pipe_writes(self):
        factory = ShortWriteFactory(output=b"1\n", write_chunk=2)
        instance, _factory = backend(factory=factory)
        instance.start("short-write")
        sql = "SELECT 123456789;"
        instance.dispatch(sql, {"timeout": 5})
        deadline = time.monotonic() + 1
        while instance.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(instance.poll())
        self.assertEqual(
            bytes(factory.processes[0].stdin.data),
            STARTUP_SQL.encode("utf-8") + sql.encode("utf-8"),
        )

    def test_nonprogress_write_is_a_failure(self):
        class ZeroWriteStdin(FakeStdin):
            def write(self, _value):
                return 0

        class ZeroWriteProcess(FakeProcess):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.stdin = ZeroWriteStdin(self)

        class ZeroWriteFactory(ProcessFactory):
            def __call__(self, argv, **kwargs):
                self.kwargs["argv"] = argv
                self.kwargs["popen"] = kwargs
                process = ZeroWriteProcess(**self.options)
                self.processes.append(process)
                return process

        factory = ZeroWriteFactory(output=b"1\n")
        instance, _factory = backend(factory=factory)
        with self.assertRaises(TransportError):
            instance.start("zero-write")
        self.assertTrue(instance.cancelled)

    def test_client_controls_are_rejected_but_general_sql_is_not_limited(self):
        instance, _factory = backend()
        instance.start("run")
        for sql in (
            "SELECT 1;\nGO\n",
            "SELECT 1;\nGO 2\n",
            "SELECT 1;\nGO;\n",
            ":setvar X 1\nSELECT 1",
            "!! dir",
            "SELECT '$(X)';",
            "SELECT 1;\nRESET\nSELECT 2;",
            "SELECT 1;\nQUIT\nSELECT 2;",
            "SELECT 1;\nEXIT(dbo.ForbiddenWrite)\n",
            "SELECT 1;\nED\nSELECT 2;",
            "SELECT 1;\nON ERROR IGNORE\nSELECT 2;",
        ):
            with self.assertRaises(ValueError):
                instance.dispatch(sql, {"timeout": 5})
        instance.dispatch("SELECT 'GO';", {"timeout": 5})
        while instance.poll() is None:
            time.sleep(0.01)

    def test_gateway_validator_contract_is_available_on_backend_type(self):
        self.assertTrue(SqlcmdBackend.validate_sql("UPDATE dbo.T SET value = 1;"))
        with self.assertRaises(ValueError):
            SqlcmdBackend.validate_sql("SELECT 1;\nGO\n")

    def test_timeout_cancel_is_idempotent_and_close_requires_observer(self):
        instance, factory = backend(finish_on_query=False)
        instance.start("run")
        instance.dispatch("WAITFOR DELAY '00:01:00';", {"timeout": 1})
        self.assertIsNone(instance.poll())
        instance.cancel()
        instance.cancel()
        self.assertTrue(instance.cancelled)
        self.assertTrue(factory.processes[0].signals)
        self.assertTrue(instance.closed())

    def test_output_row_cap_fails_and_does_not_release_result(self):
        instance, _factory = backend(output=b"a\nb\n")
        instance.start("run")
        instance.dispatch("SELECT 1;", {"timeout": 5, "max_rows": 1})
        while instance.poll() is None:
            time.sleep(0.01)
        self.assertFalse(instance.poll())
        self.assertEqual(instance.failure_reason, "output_rows_exceeded")
        with self.assertRaises(TransportError):
            instance.output_bytes()

    def test_explicit_output_byte_cap_fails_but_unlimited_has_no_hidden_cap(self):
        instance, _factory = backend(output=b"12345")
        instance.start("run")
        instance.dispatch("SELECT 1;", {"timeout": 5, "max_bytes": 4})
        while instance.poll() is None:
            time.sleep(0.01)
        self.assertFalse(instance.poll())
        self.assertEqual(instance.failure_reason, "output_bytes_exceeded")

        payload = b"x" * (8 * 1024 * 1024 + 1)
        resource, _factory = backend(output=payload)
        resource.start("resource")
        resource.dispatch("SELECT 1;", {"timeout": 5, "max_rows": None, "max_bytes": None})
        while resource.poll() is None:
            time.sleep(0.01)
        self.assertTrue(resource.poll())
        self.assertTrue(resource.closed())
        self.assertEqual(resource.output_bytes(), payload)

    def test_stderr_is_generic_failure_without_returning_error_text(self):
        instance, _factory = backend(stderr=b"secret server diagnostic")
        instance.start("run")
        instance.dispatch("SELECT 1;", {"timeout": 5})
        while instance.poll() is None:
            time.sleep(0.01)
        self.assertFalse(instance.poll())
        self.assertNotIn("secret server diagnostic", str(instance.failure_reason))

    def test_observer_permission_absence_never_confirms_close(self):
        instance, _factory = backend(observer=False)
        instance.start("run")
        instance.dispatch("SELECT 1;", {"timeout": 5})
        while instance.poll() is None:
            time.sleep(0.01)
        instance.cancel()
        self.assertFalse(instance.closed())
        with self.assertRaises(TransportError):
            instance.output_bytes()

    def test_closed_failure_is_latched_to_one_observer_call(self):
        calls = []

        def observer(*args):
            calls.append(args)
            return ObserverResult(False, 0)

        instance, _factory = backend(observer=observer)
        instance.start("cleanup-once")
        instance.dispatch("SELECT 1;", {"timeout": 5})
        while instance.poll() is None:
            time.sleep(0.01)
        instance.cancel()
        self.assertFalse(instance.closed())
        self.assertFalse(instance.closed())
        self.assertEqual(len(calls), 1)

    def test_normal_exit_releases_output_without_observer(self):
        calls = []
        def observer(*args):
            calls.append(args)
            return ObserverResult(False, 0)
        instance, _ = backend(observer=observer, output=b"1\n")
        instance.start("normal")
        instance.dispatch("SELECT 1;", {"timeout": 5})
        while instance.poll() is None:
            time.sleep(0.01)
        self.assertTrue(instance.closed())
        self.assertTrue(instance.closed())
        self.assertEqual(instance.completion_basis, "normal_exit")
        self.assertEqual(instance.output_bytes(), b"1\n")
        self.assertEqual(calls, [])
        # A late stop invalidates normal-exit release and still observes once.
        instance.cancel()
        self.assertFalse(instance.closed())
        self.assertEqual(len(calls), 1)
        with self.assertRaises(TransportError):
            instance.output_bytes()

    def test_error_and_unpolled_exit_still_require_observer(self):
        for stderr in (b"driver error", b""):
            with self.subTest(stderr=stderr):
                calls = []
                def observer(*args):
                    calls.append(args)
                    return ObserverResult(True, 0)
                instance, _ = backend(observer=observer, stderr=stderr)
                instance.start("uncertain")
                instance.dispatch("SELECT 1;", {"timeout": 5})
                instance._writer_thread.join(timeout=1)
                if stderr:
                    self.assertFalse(instance.poll())
                self.assertTrue(instance.closed())
                self.assertEqual(instance.completion_basis, "observer")
                self.assertEqual(len(calls), 1)
                with self.assertRaises(TransportError):
                    instance.output_bytes()


if __name__ == "__main__":
    unittest.main()

