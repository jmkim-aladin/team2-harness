"""Durable job metadata; SQL and result bytes never enter this ledger."""
import json
import os
import time

from db_query_control import Denied

SCHEMA_VERSION = 1
RETENTION_SECONDS = 30 * 86400
TERMINAL = frozenset(('completed', 'failed', 'unknown'))


def provision(store):
    with store.transaction() as c:
        existed = c.execute("SELECT 1 FROM sqlite_master WHERE name='query_job_schema' AND type='table'").fetchone()
        c.execute('CREATE TABLE IF NOT EXISTS query_job_schema (version INTEGER NOT NULL)')
        versions = [row[0] for row in c.execute('SELECT version FROM query_job_schema')]
        if not versions and not existed:
            c.execute('INSERT INTO query_job_schema VALUES (?)', (SCHEMA_VERSION,))
        elif versions != [SCHEMA_VERSION]:
            raise Denied('incompatible_job_schema')
        c.execute('''CREATE TABLE IF NOT EXISTS query_jobs_v2 (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, run_id TEXT UNIQUE NOT NULL,
            instance TEXT NOT NULL, epoch INTEGER NOT NULL, phase TEXT NOT NULL,
            outcome TEXT, result_state TEXT NOT NULL, result_digest TEXT,
            result_meta TEXT, updated REAL NOT NULL, terminal INTEGER NOT NULL)''')


def record_admission(c, request_id, owner, run, instance, epoch):
    c.execute('INSERT INTO query_jobs_v2 VALUES (?,?,?,?,?,?,NULL,?,NULL,NULL,?,0)',
              (request_id, owner, run, instance, epoch, 'admitting', 'none', time.time()))


class JobLedger:
    def __init__(self, store, instance):
        self.store, self.instance = store, instance
        provision(store)
        with store.transaction() as c:
            # A daemon instance owns its threads. A new instance never replays them.
            c.execute("UPDATE query_jobs_v2 SET result_state='lost_on_restart',updated=? WHERE instance<>? AND result_state='available'",
                      (time.time(), instance))
            c.execute("UPDATE query_jobs_v2 SET phase='recovery_required',updated=? WHERE instance<>? AND terminal=0",
                      (time.time(), instance))
            c.execute('DELETE FROM query_jobs_v2 WHERE terminal=1 AND updated<? AND run_id<>COALESCE((SELECT active FROM control WHERE id=1),\'\')',
                      (time.time()-RETENTION_SECONDS,))

    @staticmethod
    def owned(c, request_id, owner):
        row = c.execute('SELECT * FROM query_jobs_v2 WHERE id=?', (request_id,)).fetchone()
        if row is None or row['owner'] != owner or (row['terminal'] and row['updated'] < time.time()-RETENTION_SECONDS):
            raise Denied('job_unknown_or_expired')
        return dict(row)

    def status(self, request_id, owner):
        with self.store.transaction() as c:
            row = self.owned(c, request_id, owner)
            state = self.store._state(c)
            phase = state['phase'] if state['active'] == row['run_id'] else row['phase']
            if row['phase'] == 'recovery_required':
                phase = 'recovery_required'
            result = dict(ok=True, request_id=request_id, run_id=row['run_id'],
                          job_state=phase, result_state=row['result_state'], result_digest=row['result_digest'],
                          outcome=json.loads(row['outcome']) if row['outcome'] else None)
            if row['result_meta']:
                result.update(json.loads(row['result_meta']))
            return result

    def finish(self, c, request_id, result, receipt, available, memory_result=True):
        row = c.execute('SELECT * FROM query_jobs_v2 WHERE id=?', (request_id,)).fetchone()
        if row is None or row['instance'] != self.instance or row['terminal']:
            raise Denied('job_owner_changed')
        state = self.store._state(c)
        phase = 'completed' if result.get('ok') else 'recovery_required' if state['active'] == row['run_id'] else 'failed'
        summary = {k: result[k] for k in ('ok','status','run_id','session_closed','reason') if k in result}
        meta = {k: receipt[k] for k in ('epoch','output_bytes','output_sha256','completion_basis') if k in receipt}
        delivery = 'available' if result.get('ok') and available else 'superseded' if result.get('ok') else 'none'
        if state['halted'] or state['epoch'] != meta.get('epoch', state['epoch']):
            delivery = 'stopped' if result.get('ok') else 'none'
        if not memory_result:
            delivery = 'none'
        c.execute('''UPDATE query_jobs_v2 SET phase=?,outcome=?,result_state=?,result_digest=?,result_meta=?,
                     epoch=?,updated=?,terminal=? WHERE id=?''',
                  (phase, json.dumps(summary), delivery, receipt.get('result_digest'), json.dumps(meta),
                   meta.get('epoch', row['epoch']), time.time(), int(phase in TERMINAL), request_id))
        if available and result.get('ok'):
            c.execute("UPDATE query_jobs_v2 SET result_state='superseded',updated=? WHERE id<>? AND result_state='available'",
                      (time.time(), request_id))

    def fail(self, request_id):
        with self.store.transaction() as c:
            row = self.owned(c, request_id, 'uid:'+str(os.getuid()))
            state = self.store._state(c)
            phase = 'recovery_required' if state['active'] == row['run_id'] else 'unknown'
            c.execute("UPDATE query_jobs_v2 SET phase=?,result_state='none',updated=?,terminal=? WHERE id=?",
                      (phase, time.time(), int(phase in TERMINAL), request_id))
