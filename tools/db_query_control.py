#!/usr/bin/env python3
"""Trusted central coordinator core; no production SQL transport or authentication.

All agents must use ONE service/store, held outside agent-writable storage.
Operator methods need authentication by that service. This module alone is not
a network security boundary. CLI exposes stop/status only, never SQL execution.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time


class Denied(Exception):
    pass


def specification(owner, target, sql, timeout=60, max_rows=None, max_bytes=None):
    if not all(isinstance(value, str) and value.strip() for value in (owner, target, sql)):
        raise ValueError("owner, target and complete SQL are required")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError("Query timeout must be greater than zero and at most 60 seconds")
    for value in (max_rows, max_bytes):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError("Result bounds must be positive integers or explicitly unlimited")
    payload = dict(owner=owner, target=target, sql=sql, timeout=timeout,
                   max_rows=max_rows, max_bytes=max_bytes)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return payload, digest


class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()

    @classmethod
    def initialize(cls, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Explicit provisioning only; never recreate a missing live control DB.
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(descriptor)
        with sqlite3.connect(path) as connection:
            connection.executescript("""
CREATE TABLE control (id INTEGER PRIMARY KEY CHECK(id=1), halted INTEGER NOT NULL,
 epoch INTEGER NOT NULL, reason TEXT, active TEXT, owner TEXT, target TEXT,
 phase TEXT, identity TEXT);
INSERT INTO control VALUES (1,1,0,'not_armed',NULL,NULL,NULL,'idle',NULL);
CREATE TABLE approvals (id TEXT PRIMARY KEY, digest TEXT, epoch INTEGER,
 expires REAL, status TEXT, operator TEXT);
""")

    @contextmanager
    def transaction(self):
        # mode=rw is essential: lost state must fail closed, not start unlocked.
        connection = sqlite3.connect(self.path.as_uri()+"?mode=rw", uri=True, timeout=1)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _state(connection):
        row = connection.execute("SELECT * FROM control WHERE id=1").fetchone()
        if row is None:
            raise Denied("control_state_missing")
        return dict(row)

    def status(self):
        with self.transaction() as connection:
            return self._state(connection)

    def stop(self, reason="operator_stop", *, preserve_halt=False):
        with self.transaction() as connection:
            state = self._state(connection)
            if not (preserve_halt and state["halted"]):
                connection.execute("UPDATE control SET halted=1,epoch=epoch+1,reason=? WHERE id=1", (reason,))
        return self.status()

    def cancel(self):
        """Revoke approvals and cancel this run without weakening a fault halt."""
        with self.transaction() as connection:
            state = self._state(connection)
            reason = (state["reason"] if state["halted"] and state["reason"] != "operator_cancel"
                      else "operator_cancel")
            connection.execute("UPDATE control SET halted=1,epoch=epoch+1,reason=? WHERE id=1", (reason,))
        return self.status()

    def prepare(self, *, owner, target, sql, timeout=60, max_rows=None, max_bytes=None):
        payload, digest = specification(owner, target, sql, timeout, max_rows, max_bytes)
        request = secrets.token_hex(16)
        with self.transaction() as connection:
            state = self._state(connection)
            if state["halted"]:
                raise Denied("halted")
            connection.execute("INSERT INTO approvals VALUES (?,?,?,?,?,NULL)",
                               (request, digest, state["epoch"], time.time()+1800, "pending"))
        # The trusted approval UI must render THIS full payload, not an agent's
        # summary. Only a digest is kept in the central ledger (no SQL literals).
        return dict(id=request, digest=digest, review=payload)

    def approve(self, request, reviewed_digest, *, operator):
        """Operator-only entry point; caller authenticates the human reviewer."""
        if not isinstance(operator, str) or not operator.strip():
            raise Denied("operator_identity_required")
        with self.transaction() as connection:
            state = self._state(connection)
            changed = connection.execute("""UPDATE approvals SET status='approved',operator=?
WHERE id=? AND digest=? AND status='pending' AND expires>? AND epoch=?""",
                                         (operator, request, reviewed_digest, time.time(), state["epoch"])).rowcount
            if state["halted"] or changed != 1:
                raise Denied("approval_invalid")

    def reserve(self, owner, target, sql, approval_id, timeout=60, max_rows=None, max_bytes=None):
        _, digest = specification(owner, target, sql, timeout, max_rows, max_bytes)
        with self.transaction() as connection:
            state = self._state(connection)
            if state["halted"]:
                raise Denied("halted")
            if state["active"]:
                raise Denied("busy")
            approval = connection.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if (approval is None or approval["status"] != "approved" or approval["digest"] != digest
                    or approval["epoch"] != state["epoch"] or approval["expires"] <= time.time()):
                raise Denied("approval_required")
            run = secrets.token_hex(16)
            connection.execute("UPDATE approvals SET status='consumed' WHERE id=?", (approval_id,))
            connection.execute("""UPDATE control SET active=?,owner=?,target=?,phase='starting',identity=NULL
WHERE id=1""", (run, owner, target))
            return run

    def dispatch(self, run, identity, submit):
        # Persist intent before any SQL submission. A crash or a submit error
        # must never make this one-use approval dispatchable a second time.
        with self.transaction() as connection:
            state = self._state(connection)
            if state["active"] != run or state["phase"] != "starting":
                raise Denied("dispatch_already_attempted")
            connection.execute("UPDATE control SET phase='dispatching',identity=? WHERE id=1", (json.dumps(identity),))
        # submit must only enqueue to the owned process, never wait for a query.
        # The same transaction serializes stop vs. final SQL submission.
        with self.transaction() as connection:
            state = self._state(connection)
            if state["active"] != run or state["halted"]:
                raise Denied("halted")
            connection.execute("UPDATE control SET phase='running',identity=? WHERE id=1", (json.dumps(identity),))
            submit()

    def finish(self, run, *, closed, successful, publish=None, normal_exit=False):
        # Publishing can have an external effect before its acknowledgement is
        # lost. Persist a one-use finish intent, just like dispatch intent.
        with self.transaction() as connection:
            state = self._state(connection)
            if state["active"] != run or state["phase"] not in {"starting", "dispatching", "running"}:
                raise Denied("completion_already_attempted")
            connection.execute("UPDATE control SET phase='finishing' WHERE id=1")
        try:
            return self._finish_once(run, closed=closed, successful=successful,
                                     publish=publish, normal_exit=normal_exit)
        except Exception:
            try:
                self.stop("completion_unconfirmed")
                with self.transaction() as connection:
                    connection.execute("UPDATE control SET phase='unconfirmed' WHERE active=? AND phase='finishing'", (run,))
            except Exception:
                pass  # Durable finishing intent prevents replay even if unavailable.
            raise

    def _finish_once(self, run, *, closed, successful, publish, normal_exit=False):
        with self.transaction() as connection:
            state = self._state(connection)
            if state["active"] != run or state["phase"] != "finishing":
                raise Denied("execution_identity_mismatch")
            observer_required = normal_exit and state["halted"]
            if observer_required:
                closed = False
            accepted = bool(closed and successful and not state["halted"])
            # Linearization point for result delivery vs. stop. The core returns
            # no SQL data; a gateway must emit its held result here, using a
            # bounded nonblocking sink. Unfenced async queues are not supported.
            if accepted and publish is not None:
                publish(dict(run_id=run, epoch=state["epoch"]))
            if observer_required:
                # A stop won after poll/closed. Keep ownership until observation;
                # perform that network operation outside this transaction.
                connection.execute("UPDATE control SET phase='unconfirmed' WHERE id=1")
            elif not closed:
                connection.execute("""UPDATE control SET halted=1,epoch=epoch+1,
reason='session_cleanup_unconfirmed',phase='unconfirmed' WHERE id=1""")
            else:
                if not accepted and not state["halted"]:
                    connection.execute("UPDATE control SET halted=1,epoch=epoch+1,reason='query_failed' WHERE id=1")
                connection.execute("UPDATE control SET active=NULL,owner=NULL,target=NULL,phase='idle',identity=NULL WHERE id=1")
            return accepted

    def clear(self, snapshot, *, resume, reason=None):
        with self.transaction() as connection:
            state = self._state(connection)
            if state != snapshot or not state["halted"]:
                return False
            if resume and state["active"]:
                return False
            if not resume and state["phase"] != "unconfirmed":
                return False
            connection.execute("""UPDATE control SET active=NULL,owner=NULL,target=NULL,identity=NULL,
phase='idle',halted=?,epoch=epoch+1,reason=? WHERE id=1""", (0 if resume else 1, reason or ("operator_resumed" if resume else "reconciled_still_stopped")))
            return True


class Supervisor:
    def __init__(self, store, *, cleanup_timeout=5, poll_interval=0.05):
        self.store = store
        self.cleanup_timeout = cleanup_timeout
        self.poll_interval = poll_interval

    def stop(self):
        # Separate processes can stop the active supervisor via the shared store.
        return self.store.stop()

    def _operator_clear(self, all_sessions_closed, *, resume):
        try:
            snapshot = self.store.status()
            if not snapshot["halted"] or (resume and snapshot["active"]):
                return False
            if all_sessions_closed() is not True:
                return False
            return self.store.clear(snapshot, resume=resume)
        except Exception:
            return False

    def resume(self, all_sessions_closed):
        """Operator-only: fresh DB observer must prove ALL owned sessions gone."""
        return self._operator_clear(all_sessions_closed, resume=True)

    def reconcile(self, all_sessions_closed):
        """Clear a finished worker's unconfirmed slot; keep stop latched.

        A starting/running orphan never clears this way: a paused worker could
        still submit SQL. An external supervisor must first fence that worker.
        """
        return self._operator_clear(all_sessions_closed, resume=False)

    def execute(self, *, owner, target, backend, sql="SELECT 1;", approval_id=None,
                timeout=60, max_rows=None, max_bytes=None, publish=None):
        try:
            run = self.store.reserve(owner, target, sql, approval_id, timeout, max_rows, max_bytes)
        except Denied as error:
            return dict(ok=False, status=str(error))
        except Exception:
            return dict(ok=False, status="control_unavailable")
        successful, closed = False, False
        error = "query_failed"
        try:
            # Backend.start performs bounded connection setup only, never user
            # SQL. Backend methods must be bounded and dispatch nonblocking.
            deadline = time.monotonic()+timeout
            identity = backend.start(run)
            if time.monotonic() >= deadline:
                raise Denied("timeout")
            self.store.dispatch(run, identity, lambda: backend.dispatch(sql, dict(
                timeout=timeout, max_rows=max_rows, max_bytes=max_bytes)))
            while True:
                state = self.store.status()
                if state["halted"] or state["active"] != run:
                    raise Denied("operator_stop")
                if time.monotonic() >= deadline:
                    raise Denied("timeout")
                outcome = backend.poll()
                if outcome is not None:
                    if outcome is not True:
                        raise Denied("query_failed")
                    successful = True
                    break
                time.sleep(self.poll_interval)
        except (Exception, KeyboardInterrupt) as failure:
            error = str(failure) if isinstance(failure, Denied) else "worker_error"
            try:
                self.store.stop(error, preserve_halt=error == "operator_stop")
            except Exception:
                pass  # Persisted active slot still blocks new admission.
        finally:
            try:
                state = self.store.status()
                if state["halted"] or state["active"] != run:
                    successful = False
                if not successful:
                    backend.cancel()
                deadline = time.monotonic()+self.cleanup_timeout
                while True:
                    if backend.closed() is True:
                        closed = True
                        break
                    if time.monotonic() >= deadline:
                        break
                    if successful:
                        backend.cancel()
                    time.sleep(self.poll_interval)
            except (Exception, KeyboardInterrupt):
                closed = False
        try:
            normal_exit = getattr(backend, "completion_basis", None) == "normal_exit"
            accepted = self.store.finish(run, closed=closed, successful=successful,
                                         publish=publish, normal_exit=normal_exit)
        except Exception:
            closed = self._observe_failed_finish(run, backend)
            return dict(ok=False, status="control_unavailable", run_id=run, session_closed=closed)
        if not accepted and normal_exit:
            closed = self._observe_failed_finish(run, backend)
        return dict(ok=accepted, status="completed" if accepted else ("stopped" if closed else "unconfirmed"),
                    run_id=run, session_closed=closed, **({} if accepted else {"reason": error}))

    def _observe_failed_finish(self, run, backend):
        """A late stop or failed receipt revokes normal completion evidence."""
        try:
            backend.cancel()
            closed = backend.closed() is True
            if closed:
                state = self.store.status()
                if state["active"] == run and state["halted"] and state["phase"] == "unconfirmed":
                    self.store.clear(state, resume=False, reason=state["reason"])
            return closed
        except Exception:
            return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True, help="Existing central service state file")
    parser.add_argument("action", choices=("status", "stop"))
    args = parser.parse_args()
    try:
        store = Store(args.state)
        result = store.stop() if args.action == "stop" else store.status()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        print(json.dumps(dict(ok=False, status="control_unavailable")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
