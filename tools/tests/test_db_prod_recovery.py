#!/usr/bin/env python3
"""Synthetic recovery-journal and fail-closed coordinator tests."""

from __future__ import annotations

from pathlib import Path
import secrets
import tempfile
import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from db_prod_recovery import (  # noqa: E402
    RecoveryDenied,
    RecoveryJournal,
    approve_recovery_approval,
    create_recovery_approval,
    observer_recovery_digest,
    recover,
    current_user_sqlcmd_absent,
)
from db_query_control import Store, Supervisor  # noqa: E402
from db_prod_transport import control_sql


class RecoveryTests(unittest.TestCase):
    def test_real_multiline_observer_sql_is_digestible_and_whitespace_is_bound(self):
        args = dict(run_id="a" * 32, epoch=1, target="lego-prod", database="master",
                    host_tag="t2q-recovery", profile_digest="b" * 64)
        sql = control_sql(args["host_tag"])
        digest = observer_recovery_digest(observer_sql=sql, **args)
        self.assertNotEqual(digest, observer_recovery_digest(observer_sql=sql.replace("\n", " "), **args))
        for invalid in (sql + "\x00", sql + "\x1b", " \n\t", "x" * 16385):
            with self.assertRaises(RecoveryDenied):
                observer_recovery_digest(observer_sql=invalid, **args)

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="team2-recovery-")
        self.state_dir = Path(self.directory.name)
        self.store_path = self.state_dir / "control.sqlite3"
        Store.initialize(self.store_path)
        self.store = Store(self.store_path)
        Supervisor(self.store).resume(lambda: True)
        self.journal = RecoveryJournal(self.state_dir)
        self.gateway_pid = 200
        self.gateway_birth = "gateway-birth"
        self.worker_pid = 201
        self.worker_birth = "worker-birth"
        self.metadata = {
            "target": "lego-prod",
            "database": "WebCatalog",
            "host_tag": "t2q-recovery",
            "profile_digest": "a" * 64,
            "gateway_pid": self.gateway_pid,
            "gateway_birth": self.gateway_birth,
        }
        self.run_id = self._reserve()
        self.journal.write_before_start(self.run_id, self.metadata)
        self.journal.update_worker(self.run_id, self.worker_pid, self.worker_birth)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _reserve(self) -> str:
        request = self.store.prepare(
            owner="uid:501",
            target="lego-prod:binding",
            sql="SELECT 1 AS connection_ok;",
            timeout=60,
            max_rows=None,
            max_bytes=None,
        )
        self.store.approve(request["id"], request["digest"], operator="explicit-user-chat")
        return self.store.reserve(
            "uid:501",
            "lego-prod:binding",
            "SELECT 1 AS connection_ok;",
            request["id"],
            timeout=60,
            max_rows=None,
            max_bytes=None,
        )

    def _plan(self) -> dict:
        state = self.store.status()
        if not state["halted"]:
            state = self.store.stop("operator_stop")
        observer_sql = "SET NOCOUNT ON; SELECT 0 AS session_count;"
        digest = observer_recovery_digest(
            run_id=self.run_id,
            epoch=state["epoch"],
            target=self.metadata["target"],
            database=self.metadata["database"],
            host_tag=self.metadata["host_tag"],
            profile_digest=self.metadata["profile_digest"],
            observer_sql=observer_sql,
        )
        request_id = secrets.token_hex(16)
        create_recovery_approval(
            self.store,
            request_id=request_id,
            run_id=self.run_id,
            epoch=state["epoch"],
            target=self.metadata["target"],
            database=self.metadata["database"],
            host_tag=self.metadata["host_tag"],
            profile_digest=self.metadata["profile_digest"],
            digest=digest,
        )
        approve_recovery_approval(self.store, request_id, digest, operator="explicit-user-chat")
        return {
            "approved": True,
            "recovery_request_id": request_id,
            "run_id": self.run_id,
            "epoch": state["epoch"],
            "target": "lego-prod",
            "database": "WebCatalog",
            "host_tag": "t2q-recovery",
            "profile_digest": "a" * 64,
            "observer_sql": observer_sql,
            "timeout": 5.0,
            "max_rows": 1,
            "max_bytes": 256,
            "digest": digest,
        }

    def test_journal_is_atomic0600_and_has_no_sql_or_secret_fields(self) -> None:
        path = self.journal.path_for(self.run_id)
        info = path.stat()
        self.assertEqual(info.st_mode & 0o777, 0o600)
        record = self.journal.read(self.run_id)
        self.assertEqual(record.worker_pid, self.worker_pid)
        raw = path.read_text()
        self.assertNotIn("SELECT", raw)
        self.assertNotIn("password", raw.lower())
        self.assertNotIn("account", raw.lower())

    def test_live_worker_is_denied_without_mutating_store(self) -> None:
        before = self.store.status()
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: 0,
                lambda pid: self.worker_birth if pid == self.worker_pid else None,
                journal=self.journal,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "worker_alive")
        after = self.store.status()
        self.assertTrue(after["halted"])
        self.assertEqual(after["active"], before["active"])
        self.assertEqual(after["phase"], "unconfirmed")

    def test_unobservable_worker_identity_is_denied(self) -> None:
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: 0,
                lambda _pid: None,
                journal=self.journal,
                pid_presence_probe=lambda _pid: True,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "process_identity_unavailable")

    def test_mismatched_worker_birth_is_fenced_and_keeps_halt(self) -> None:
        result = recover(
            self._plan(),
            self.store,
            lambda _plan: 0,
            lambda _pid: "different-birth",
            journal=self.journal,
            sleep=lambda _: None,
        )
        self.assertTrue(result["ok"])
        state = self.store.status()
        self.assertTrue(state["halted"])
        self.assertIsNone(state["active"])
        self.assertEqual(state["phase"], "idle")

    def test_unknown_worker_requires_gateway_death_and_grace(self) -> None:
        self.journal = RecoveryJournal(self.state_dir)
        path = self.journal.path_for(self.run_id)
        path.unlink()
        self.journal.write_before_start(self.run_id, self.metadata)
        observed = []
        calls = []

        result = recover(
            self._plan(),
            self.store,
            lambda _plan: 0,
            lambda pid: calls.append(pid) or None,
            journal=self.journal,
            watchdog_grace=5,
            sleep=lambda seconds: observed.append(seconds),
            pid_presence_probe=lambda _pid: False,
            allow_unknown_worker=True,
            unknown_worker_absence_probe=lambda: True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(calls, [self.gateway_pid, self.gateway_pid])
        self.assertEqual(observed, [5])

    def test_unknown_worker_is_denied_by_default(self) -> None:
        self.journal = RecoveryJournal(self.state_dir)
        path = self.journal.path_for(self.run_id)
        path.unlink()
        self.journal.write_before_start(self.run_id, self.metadata)
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: 0,
                lambda _pid: None,
                journal=self.journal,
                pid_presence_probe=lambda _pid: False,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "worker_identity_missing")

    def test_unknown_worker_absence_is_required_and_checked_before_observer(self):
        self.journal.path_for(self.run_id).unlink()
        self.journal.write_before_start(self.run_id, self.metadata)
        for proof in (None, lambda: False, lambda: 1):
            with self.subTest(proof=proof), self.assertRaises(RecoveryDenied):
                recover(self._plan(), self.store,
                        lambda _: self.fail("observer must wait for local proof"),
                        lambda _: None, journal=self.journal, sleep=lambda _: None,
                        pid_presence_probe=lambda _: False, allow_unknown_worker=True,
                        unknown_worker_absence_probe=proof)
            state = self.store.status()
            self.assertTrue(state["halted"])
            self.assertEqual(state["active"], self.run_id)

    def test_unknown_worker_is_rechecked_after_single_observer(self):
        self.journal.path_for(self.run_id).unlink()
        self.journal.write_before_start(self.run_id, self.metadata)
        proofs = iter([True, False])
        observed = []
        with self.assertRaises(RecoveryDenied):
            recover(self._plan(), self.store, lambda _: observed.append(1) or True,
                    lambda _: None, journal=self.journal, sleep=lambda _: None,
                    pid_presence_probe=lambda _: False, allow_unknown_worker=True,
                    unknown_worker_absence_probe=lambda: next(proofs))
        self.assertEqual(observed, [1])
        self.assertEqual(self.store.status()["active"], self.run_id)

    def test_local_inventory_parsing_fails_closed(self):
        own = f"{os.getpid()} {os.getuid()} /Library/Path With Spaces/Python\n"
        with patch("db_prod_recovery.sys.platform", "darwin"):
            for output, error, expected in [
                (own, "", True),
                (own + f"987654 {os.getuid()} /opt/homebrew/bin/sqlcmd\n", "", False),
                (own + own, "", None), ("", "", None),
                (own + "bad row\n", "", None), (own, "warning", None),
                (own + "x" * (1024 * 1024), "", None),
            ]:
                with self.subTest(expected=expected), patch("db_prod_recovery.subprocess.run", return_value=SimpleNamespace(stdout=output, stderr=error)) as run:
                    if expected is None:
                        with self.assertRaises(RecoveryDenied): current_user_sqlcmd_absent()
                    else:
                        self.assertIs(current_user_sqlcmd_absent(), expected)
                    self.assertEqual(run.call_args[0][0], ["/bin/ps", "-ww", "-axo", "pid=,uid=,comm="])

    def test_unknown_gateway_alive_is_denied(self) -> None:
        self.journal = RecoveryJournal(self.state_dir)
        path = self.journal.path_for(self.run_id)
        path.unlink()
        self.journal.write_before_start(self.run_id, self.metadata)
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: 0,
                lambda pid: self.gateway_birth if pid == self.gateway_pid else None,
                journal=self.journal,
                sleep=lambda _: self.fail("live gateway must not reach grace"),
                pid_presence_probe=lambda _pid: False,
                allow_unknown_worker=True,
            )
        self.assertEqual(str(error.exception), "gateway_alive")

    def test_observer_nonzero_is_denied(self) -> None:
        before = self.store.status()
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: 1,
                lambda _pid: "different-birth",
                journal=self.journal,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "reconcile_failed")
        after = self.store.status()
        self.assertTrue(after["halted"])
        self.assertEqual(after["active"], before["active"])
        self.assertEqual(after["phase"], "unconfirmed")

    def test_observer_false_is_denied(self) -> None:
        before = self.store.status()
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: False,
                lambda _pid: "different-birth",
                journal=self.journal,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "reconcile_failed")
        after = self.store.status()
        self.assertTrue(after["halted"])
        self.assertEqual(after["active"], before["active"])
        self.assertEqual(after["phase"], "unconfirmed")

    def test_observer_permission_failure_is_denied(self) -> None:
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: {"permission_ok": False, "sessions": 0},
                lambda _pid: "different-birth",
                journal=self.journal,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "reconcile_failed")

    def test_failed_observer_consumes_old_approval_and_allows_fresh_approval(self) -> None:
        plan = self._plan()
        with self.assertRaises(RecoveryDenied):
            recover(
                plan,
                self.store,
                lambda _plan: False,
                lambda _pid: "different-birth",
                journal=self.journal,
                sleep=lambda _: None,
            )
        retry = self._plan()
        self.assertNotEqual(plan["recovery_request_id"], retry["recovery_request_id"])

    def test_new_prepare_supersedes_stale_pending_approval(self) -> None:
        first = self._plan()
        second = self._plan()
        self.assertNotEqual(first["recovery_request_id"], second["recovery_request_id"])
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT status FROM recovery_approvals WHERE id=?",
                (first["recovery_request_id"],),
            ).fetchone()
        self.assertEqual(row["status"], "superseded")

    def test_journal_rejects_extra_fields(self) -> None:
        path = self.journal.path_for(self.run_id)
        raw = path.read_text()
        path.write_text(raw.replace('"worker":', '"sql":"SELECT 1;","worker":'))
        with self.assertRaises(RecoveryDenied) as error:
            self.journal.read(self.run_id)
        self.assertEqual(str(error.exception), "journal_fields")

    def test_changed_store_snapshot_is_denied(self) -> None:
        def mutate_store(_plan):
            with self.store.transaction() as connection:
                connection.execute("UPDATE control SET identity=? WHERE id=1", ("tampered",))
            return 0

        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                mutate_store,
                lambda _pid: "different-birth",
                journal=self.journal,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "reconcile_failed")

    def test_restart_phase_is_reconciled_only_after_fencing(self) -> None:
        result = recover(
            self._plan(),
            self.store,
            lambda _plan: {"active_sessions": 0},
            lambda _pid: "different-birth",
            journal=self.journal,
            sleep=lambda _: None,
        )
        self.assertEqual(result["status"], "recovered")
        self.assertTrue(self.store.status()["halted"])

    def test_review_digest_or_approval_change_is_denied(self) -> None:
        plan = self._plan()
        plan["sql"] = "SELECT 2;"
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                plan,
                self.store,
                lambda _plan: 0,
                lambda _pid: "different-birth",
                journal=self.journal,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "observer_only_required")

    def test_short_grace_is_denied(self) -> None:
        with self.assertRaises(RecoveryDenied) as error:
            recover(
                self._plan(),
                self.store,
                lambda _plan: 0,
                lambda _pid: "different-birth",
                journal=self.journal,
                watchdog_grace=1,
                sleep=lambda _: None,
            )
        self.assertEqual(str(error.exception), "watchdog_grace_too_short")

    def test_stop_new_observer_approval_fences_and_keeps_halted_idle(self) -> None:
        stopped = self.store.stop("operator_stop")
        observer_sql = "SET NOCOUNT ON; SELECT 0 AS session_count;"
        digest = observer_recovery_digest(
            run_id=self.run_id,
            epoch=stopped["epoch"],
            target=self.metadata["target"],
            database=self.metadata["database"],
            host_tag=self.metadata["host_tag"],
            profile_digest=self.metadata["profile_digest"],
            observer_sql=observer_sql,
        )
        request_id = "b" * 32
        create_recovery_approval(
            self.store,
            request_id=request_id,
            run_id=self.run_id,
            epoch=stopped["epoch"],
            target=self.metadata["target"],
            database=self.metadata["database"],
            host_tag=self.metadata["host_tag"],
            profile_digest=self.metadata["profile_digest"],
            digest=digest,
        )
        approve_recovery_approval(self.store, request_id, digest, operator="explicit-user-chat")
        plan = {
            "approved": True,
            "recovery_request_id": request_id,
            "run_id": self.run_id,
            "epoch": stopped["epoch"],
            "target": self.metadata["target"],
            "database": self.metadata["database"],
            "host_tag": self.metadata["host_tag"],
            "profile_digest": self.metadata["profile_digest"],
            "observer_sql": observer_sql,
            "timeout": 5.0,
            "max_rows": 1,
            "max_bytes": 256,
            "digest": digest,
        }
        result = recover(
            plan,
            self.store,
            lambda _plan: True,
            lambda _pid: "different-birth",
            journal=self.journal,
            sleep=lambda _: None,
        )
        self.assertTrue(result["ok"])
        state = self.store.status()
        self.assertTrue(state["halted"])
        self.assertIsNone(state["active"])
        self.assertEqual(state["phase"], "idle")


if __name__ == "__main__":
    unittest.main()
