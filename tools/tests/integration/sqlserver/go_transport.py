#!/usr/bin/env python3
"""Real host Go client against an owned, disposable loopback SQL Server.

Unlike the ODBC fixture, this checks the production command factory and the
client's stdin/EOF behavior. No Keychain, production profile, or existing DB.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from verify import DEFAULT_IMAGE, Lab
from db_prod_transport import Credentials, SqlcmdBackend
from db_query_control import Store, Supervisor
from db_prod_gateway import Gateway, LatchStore
from db_prod_watchdog import create_stop_marker


class LoopbackLab(Lab):
    def run(self, args, **kwargs):
        if args[:2] == ["docker", "run"]:
            # The host client needs a private ephemeral port. Never bind all
            # interfaces and never reuse a server outside this owned fixture.
            args = list(args)
            index = args.index("--network")
            assert args[index + 1] == "none"
            args[index:index + 2] = ["--publish", "127.0.0.1::1433"]
        return super().run(args, **kwargs)

    def host_port(self):
        result = self.run(["docker", "inspect", self.name, "--format", "{{json .NetworkSettings.Ports}}"])
        ports = json.loads(self.require(result, "fixture port"))["1433/tcp"]
        assert len(ports) == 1 and ports[0]["HostIp"] == "127.0.0.1"
        return int(ports[0]["HostPort"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    lab = LoopbackLab(DEFAULT_IMAGE)
    lab.report["scope"] = "host Go transport and automatic session cleanup on owned loopback SQL Server"
    backends = []
    captured = []

    class RecordingProcess(subprocess.Popen):
        def communicate(self, *args, **kwargs):
            output = super().communicate(*args, **kwargs)
            captured.append(output)
            return output

    try:
        lab.start()
        credentials = Credentials("127.0.0.1", lab.host_port(), "sa", lab.passwords["sa"])

        def make(tag, backend_type=SqlcmdBackend):
            backend = backend_type(credentials, "master", observer_credentials=credentials,
                                    host_tag=tag, stop_latch=None, startup_timeout=5,
                                    observer_timeout=5, query_timeout=5,
                                    popen_factory=RecordingProcess)
            backends.append(backend)
            return backend

        observer = make("q-go-fixture-observer")
        closed = observer.observe_closed("q-go-fixture-observer", timeout=5)
        if not closed:
            # These bytes are from the synthetic fixture's fixed control SQL.
            # Production diagnostics continue to withhold arbitrary output.
            for stdout, stderr in captured:
                print(json.dumps({"fixture_stdout": lab.clean(stdout.decode("utf-8", "replace"))[:512],
                                  "fixture_stderr": lab.clean(stderr.decode("utf-8", "replace"))[:512]}))
        lab.record("host Go observer accepts real control result", closed)

        worker = make("q-go-fixture-worker")
        worker.start("fixture")
        worker.dispatch("SELECT 1 AS connection_ok;", {"timeout": 5, "max_rows": 1, "max_bytes": 1024})
        deadline = time.monotonic() + 7
        result = worker.poll()
        while result is None and time.monotonic() < deadline:
            time.sleep(0.02)
            result = worker.poll()
        closed = worker.closed()
        if result is not True or not closed or worker.output_bytes().strip() != b"1":
            print(json.dumps({"fixture_worker_result": result, "session_closed": closed,
                              "diagnostics": worker.diagnostics(),
                              "fixture_stdout": lab.clean(bytes(worker._result).decode("utf-8", "replace"))[:512]}))
        lab.record("host Go worker returns only one approved result row",
                   result is True and closed and worker.output_bytes().strip() == b"1")

        # Reproduce delayed server removal: the observed session exists when
        # observation begins, then disappears while that same batch is open.
        delayed = make("q-go-fixture-delayed")
        delayed.start("delayed")
        delayed_observer = make("q-go-fixture-delayed")
        timer = threading.Timer(1.5, delayed.cancel)
        timer.start()
        try:
            before_calls = len(captured)
            closed = delayed_observer.observe_closed("q-go-fixture-delayed", timeout=5)
            lab.record("single observer batch waits for delayed session removal", closed)
            lab.record("delayed session observation launches exactly once", len(captured) == before_calls + 1)
        finally:
            timer.join(timeout=5)

        # Exercise the actual coordinator, including slot release/result gate.
        Store.initialize(lab.budget_path)
        store = Store(lab.budget_path)
        supervisor = Supervisor(store)
        assert supervisor.resume(lambda: True)

        def execute(backend, sql="SELECT 1;", timeout=5):
            spec = dict(owner="fixture", target="loopback", sql=sql,
                        timeout=timeout, max_rows=1, max_bytes=1024)
            prepared = store.prepare(**spec)
            store.approve(prepared["id"], prepared["digest"], operator="fixture")
            return supervisor.execute(**spec, backend=backend, approval_id=prepared["id"])

        before_calls = len(captured)
        auto = make("q-go-fixture-auto")
        outcome = execute(auto)
        lab.record("normal completion releases slot without an observer connection",
                   outcome["ok"] and outcome["session_closed"]
                   and auto.completion_basis == "normal_exit" and len(captured) == before_calls
                   and store.status()["active"] is None and store.status()["phase"] == "idle"
                   and auto.output_bytes().strip() == b"1")

        class StopDuringObservation(SqlcmdBackend):
            def _execute_observer_process(self, **kwargs):
                supervisor.stop()
                return super()._execute_observer_process(**kwargs)

        outcome = execute(make("q-go-fixture-stop", StopDuringObservation),
                          sql="WAITFOR DELAY '00:00:10';", timeout=2)
        lab.record("cleanup after stop releases slot but preserves halt and withholds results",
                   not outcome["ok"] and outcome["session_closed"]
                   and store.status()["active"] is None and store.status()["halted"])

        # Use the real gateway admission/finish path plus an independent
        # marker/store writer, without production runtime or Keychain access.
        gateway_path = lab.budget_path.parent / "gateway-control.sqlite3"
        markers = lab.budget_path.parent / "gateway-stop.d"
        Store.initialize(gateway_path)
        gateway_store = LatchStore(gateway_path, markers)
        assert Supervisor(gateway_store).resume(lambda: True)
        timers = []
        stop_enabled = [True]

        class FixtureVault:
            def profile(self, target):
                return dict(host=credentials.host, port=credentials.port, account=credentials.account)
            def credentials(self, target, expected):
                assert expected == self.profile(target)
                return credentials

        class FixtureAudit:
            def write(self, event, **detail): pass

        class FixtureBackend(SqlcmdBackend):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs, stop_latch=markers, popen_factory=RecordingProcess)
                backends.append(self)
            def dispatch(self, sql, limits):
                super().dispatch(sql, limits)
                if stop_enabled[0]:
                    def stop_independently():
                        create_stop_marker(markers, reason="operator_cancel")
                        Store(gateway_path).cancel()
                    timer = threading.Timer(0.2, stop_independently)
                    timers.append(timer)
                    timer.start()

        gateway = Gateway(gateway_store, FixtureVault(), FixtureAudit(),
                          {"lego-prod": dict(enabled=True, read_only_verified=True)},
                          allowed_uids=[os.getuid()], backend_type=FixtureBackend)

        def prepare_gateway(sql):
            return gateway.handle(dict(action="prepare", target="lego-prod", database="master",
                                       sql=sql, timeout=10, max_rows=1, max_bytes=1024), os.getuid())["review"]

        def approve_gateway(review):
            gateway.handle(dict(action="approve", request_id=review["request_id"], digest=review["digest"],
                                approval_source="explicit-user-chat"), os.getuid())

        old = prepare_gateway("SELECT 1;")
        approve_gateway(old)
        current = prepare_gateway("WAITFOR DELAY '00:00:03';\nSELECT 1;")
        approve_gateway(current)
        receipts = []
        try:
            outcome = gateway.handle(dict(action="execute", request_id=current["request_id"]),
                                     os.getuid(), publish=receipts.append)
        finally:
            for timer in timers:
                timer.join(timeout=5)
        state = gateway.handle(dict(action="status"), os.getuid())
        lab.record("independent cancellation proves closure then automatically accepts fresh work",
                   outcome["status"] == "stopped" and outcome["session_closed"]
                   and not receipts and not state["halted"] and state["active"] is None
                   and state["phase"] == "idle" and not state["stop_markers"])
        stop_enabled[0] = False
        stale = gateway.handle(dict(action="execute", request_id=old["request_id"]), os.getuid(), publish=receipts.append)
        lab.record("cancellation never revives an earlier approval", stale["status"] == "approval_required")
        fresh = prepare_gateway("SELECT 1;")
        approve_gateway(fresh)
        outcome = gateway.handle(dict(action="execute", request_id=fresh["request_id"]), os.getuid(), publish=receipts.append)
        lab.record("newly approved query runs without a manual resume", outcome["ok"] and outcome["session_closed"])

        remaining = make("q-go-fixture-remaining")
        remaining.start("remaining")
        remaining_observer = make("q-go-fixture-remaining")
        before_calls = len(captured)
        started = time.monotonic()
        lab.record("persistent session is never declared closed",
                   not remaining_observer.observe_closed("q-go-fixture-remaining", timeout=5))
        lab.record("persistent session check is bounded", time.monotonic() - started < 6)
        remaining.cancel()
        lab.record("failed observation requires new approval, never reconnects",
                   not remaining_observer.observe_closed("q-go-fixture-remaining", timeout=5)
                   and len(captured) == before_calls + 1)
    finally:
        for backend in backends:
            backend.cancel()
        lab.cleanup()
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(lab.report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
