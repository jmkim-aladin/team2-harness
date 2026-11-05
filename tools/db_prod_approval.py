"""Immutable v2 reviews and durable one-use admission, without DB transport."""
from dataclasses import dataclass
import hashlib
import json
import secrets
import time

from db_query_control import Denied, specification
from db_prod_jobs import provision, record_admission

MEMORY_MAX_BYTES = 32 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ReviewEnvelope:
    payload: str

    @classmethod
    def create(cls, review):
        return cls(canonical(review))

    def review(self):
        review = json.loads(self.payload)
        envelope_digest = digest(review)
        approval_digest = digest(dict(envelope_digest=envelope_digest, request_id=review['request_id'],
                                      selected_actions=review['selected_actions']))
        return dict(review, envelope_digest=envelope_digest, approval_digest=approval_digest, digest=approval_digest)


@dataclass(frozen=True)
class AdmissionTicket:
    ledger: object
    request_id: str
    run_id: str
    instance: str
    deadline: float


class ApprovalLedger:
    def __init__(self, store):
        self.store = store
        provision(store)
        with store.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS query_approval_v2 (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, target TEXT NOT NULL,
                envelope_digest TEXT NOT NULL, approval_digest TEXT NOT NULL,
                spec_digest TEXT NOT NULL, actions TEXT NOT NULL, snapshot TEXT NOT NULL,
                expires REAL NOT NULL, status TEXT NOT NULL, runtime TEXT NOT NULL, run_id TEXT UNIQUE,
                active_epoch INTEGER, instance TEXT, deadline REAL, source TEXT,
                recovery TEXT, result TEXT)''')

    def register(self, envelope, spec):
        review = envelope.review()
        _, spec_hash = specification(**spec)
        with self.store.transaction() as c:
            c.execute('''INSERT INTO query_approval_v2
                (id,owner,target,envelope_digest,approval_digest,spec_digest,actions,snapshot,expires,runtime,status)
                VALUES (?,?,?,?,?,?,?,?,?,?,'preview')''',
                (review['request_id'], spec['owner'], spec['target'], review['envelope_digest'],
                 review['approval_digest'], spec_hash, canonical(review['selected_actions']),
                 canonical(review['stop_snapshot']), review['expires_at'], review['runtime_fingerprint']))

    def lookup(self, request_id, owner):
        with self.store.transaction() as c:
            row = c.execute('SELECT * FROM query_approval_v2 WHERE id=?', (request_id,)).fetchone()
            if row is None or row['owner'] != owner:
                raise Denied('request_not_found')
            return dict(row)

    def admit(self, request_id, approval_digest, actions, source, spec, markers, instance, recovery):
        if source not in ('explicit-user-chat', 'human-terminal'):
            raise Denied('explicit_approval_source_required')
        if not isinstance(actions, list) or any(not isinstance(x, str) for x in actions):
            raise Denied('approval_actions_mismatch')
        _, spec_hash = specification(**spec)
        run = secrets.token_hex(16)
        deadline = time.monotonic() + spec['timeout']
        with self.store.transaction() as c:
            row = c.execute('SELECT * FROM query_approval_v2 WHERE id=?', (request_id,)).fetchone()
            if row is None or row['owner'] != spec['owner']:
                raise Denied('request_not_found')
            if row['approval_digest'] != approval_digest or row['actions'] != canonical(actions):
                raise Denied('approval_actions_or_digest_mismatch')
            if row['status'] != 'preview':
                return None
            if row['expires'] <= time.time() or row['spec_digest'] != spec_hash:
                raise Denied('review_expired_or_changed')
            expected = json.loads(row['snapshot'])
            state = self.store._state(c)
            if state != expected['state'] or list(markers) != expected['markers']:
                raise Denied('resume_confirmation_changed')
            if state['active'] is not None or state['phase'] != 'idle':
                raise Denied('busy')
            c.execute('''UPDATE query_approval_v2 SET status='admitting',run_id=?,instance=?,deadline=?,source=?,recovery=?
                         WHERE id=? AND status='preview' ''',
                      (run, instance, deadline, source, canonical(recovery), request_id))
            c.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?)",
                      (request_id, row['spec_digest'], state['epoch'], row['expires'], 'consumed', source))
            c.execute("UPDATE control SET active=?,owner=?,target=?,phase='admitting',identity=NULL WHERE id=1",
                      (run, spec['owner'], spec['target']))
            record_admission(c, request_id, spec['owner'], run, instance, state['epoch'])
        return AdmissionTicket(self, request_id, run, instance, deadline)

    def activate(self, ticket, marker_reader):
        with self.store.transaction() as c:
            row = c.execute('SELECT * FROM query_approval_v2 WHERE id=?', (ticket.request_id,)).fetchone()
            state = self.store._state(c)
            expected = json.loads(row['snapshot'])['state']
            if (row['status'] != 'admitting' or row['run_id'] != ticket.run_id
                    or row['instance'] != ticket.instance or row['deadline'] != ticket.deadline
                    or state['active'] != ticket.run_id or state['owner'] != row['owner']
                    or state['target'] != row['target']
                    or state['phase'] != 'admitting' or marker_reader()
                    or any(state[k] != expected[k] for k in ('epoch', 'halted', 'reason'))):
                raise Denied('resume_confirmation_changed')
            if time.monotonic() >= ticket.deadline:
                raise Denied('timeout')
            epoch = state['epoch'] + (1 if expected['halted'] else 0)
            if expected['halted']:
                c.execute("UPDATE control SET halted=0,epoch=?,phase='starting' WHERE id=1", (epoch,))
            else:
                c.execute("UPDATE control SET phase='starting' WHERE id=1")
            c.execute("UPDATE query_approval_v2 SET status='active',active_epoch=? WHERE id=?", (epoch, ticket.request_id))

    def claim_backend_start(self, ticket, spec):
        _, spec_hash = specification(**spec)
        with self.store.transaction() as c:
            row = c.execute('SELECT * FROM query_approval_v2 WHERE id=?', (ticket.request_id,)).fetchone()
            approval = c.execute('SELECT * FROM approvals WHERE id=?', (ticket.request_id,)).fetchone()
            state = self.store._state(c)
            if (row is None or approval is None or approval['status'] != 'consumed'
                    or approval['digest'] != row['spec_digest']
                    or approval['epoch'] != json.loads(row['snapshot'])['state']['epoch']
                    or approval['operator'] != row['source']
                    or row['status'] != 'active' or row['run_id'] != ticket.run_id
                    or row['instance'] != ticket.instance or row['deadline'] != ticket.deadline
                    or row['spec_digest'] != spec_hash or row['owner'] != spec['owner']
                    or state['active'] != ticket.run_id or state['owner'] != spec['owner']
                    or state['target'] != spec['target'] or state['epoch'] != row['active_epoch']
                    or state['halted'] or state['phase'] != 'starting'):
                raise Denied('admission_ticket_invalid_or_consumed')
            if time.monotonic() >= ticket.deadline:
                raise Denied('timeout')
            c.execute("UPDATE query_approval_v2 SET status='claimed' WHERE id=?", (ticket.request_id,))
        return ticket.run_id

    def complete(self, ticket, result):
        summary = {k: result[k] for k in ('ok', 'status', 'run_id', 'session_closed', 'reason') if k in result}
        with self.store.transaction() as c:
            c.execute("UPDATE query_approval_v2 SET status='finished',result=? WHERE id=? AND run_id=?",
                      (canonical(summary), ticket.request_id, ticket.run_id))

    def recovery_record(self, run_id):
        with self.store.transaction() as c:
            row = c.execute('SELECT recovery FROM query_approval_v2 WHERE run_id=?', (run_id,)).fetchone()
            return json.loads(row['recovery']) if row and row['recovery'] else None


class LedgerRecoveryJournal:
    """Use the original worker journal; pre-start crashes have a DB admission record."""
    def __init__(self, journal, ledger):
        self.journal, self.ledger = journal, ledger

    def __getattr__(self, name):
        return getattr(self.journal, name)

    def read(self, run_id):
        from db_prod_recovery import RecoveryDenied, RecoveryJournal
        try:
            return self.journal.read(run_id)
        except RecoveryDenied:
            path = self.journal.path_for(run_id)
            if path.exists() or path.is_symlink():
                raise
            metadata = self.ledger.recovery_record(run_id)
            if metadata is None:
                raise
            return RecoveryJournal.from_admission(run_id, metadata)
