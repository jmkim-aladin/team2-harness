#!/usr/bin/env python3
"""Probe existing Store phase/slot gates in isolated SQLite; never connect to DB.

Fixture phase changes below are setup, NOT an implementation of v2 admission.
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from db_query_control import Store, Denied


def fixture(base, name):
    path = base / (name + '.sqlite3')
    Store.initialize(path)
    store = Store(path)
    with store.transaction() as c:
        c.execute("UPDATE control SET halted=0,epoch=7,active='fixture-run',phase='admitting'")
    return store


def denied(call):
    try:
        call()
    except Denied as error:
        return str(error)
    raise AssertionError('Expected rejection')


def probe():
    observations = {}
    with tempfile.TemporaryDirectory(prefix='q1-gate-probe-') as tmp:
        base = Path(tmp)
        store = fixture(base, 'admitting')
        sent = []
        observations['other_reserve_while_admitting'] = denied(
            lambda: store.reserve('fixture-other', 'fixture-target', 'SELECT 1;', None))
        assert observations['other_reserve_while_admitting'] == 'busy'
        observations['dispatch_while_admitting'] = denied(
            lambda: store.dispatch('fixture-run', {}, lambda: sent.append('sent')))
        assert not sent and store.status()['halted'] == 0

        store = fixture(base, 'ready-activation')
        # Simulate the planned ready C state as a FIXTURE, without clearing halt.
        with store.transaction() as c:
            c.execute("UPDATE control SET phase='starting' WHERE active='fixture-run' AND halted=0")
        sent = []
        store.dispatch('fixture-run', {}, lambda: sent.append('sent'))
        observations['ready_fixture_single_dispatch'] = len(sent)
        assert sent == ['sent'] and store.status()['halted'] == 0
        observations['second_dispatch'] = denied(
            lambda: store.dispatch('fixture-run', {}, lambda: sent.append('sent')))
        assert sent == ['sent']

        store = fixture(base, 'stop-before-dispatch')
        with store.transaction() as c:
            c.execute("UPDATE control SET phase='starting'")
        store.stop('fixture-new-stop')
        sent = []
        observations['new_stop_before_dispatch'] = denied(
            lambda: store.dispatch('fixture-run', {}, lambda: sent.append('sent')))
        assert not sent and store.status()['halted'] == 1 and store.status()['epoch'] == 8
    return {'status': 'PASS', 'scope': 'existing Store phase/slot/dispatch behavior only',
            'v2_admission_implemented': False, 'observations': observations}


if __name__ == '__main__':
    print(json.dumps(probe(), ensure_ascii=False, indent=2))
