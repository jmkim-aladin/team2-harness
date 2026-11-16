"""Local MCP fixture protocol: discovery and calls, with no real DB access."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


FIXTURE = Path(__file__).resolve().parents[1] / 'docs/verification/harness-hook-context-audit/fixture_server.py'


class HookProbeFixtureTests(unittest.TestCase):
    def test_unknown_or_argument_bearing_calls_are_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            requests = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': '../escape', 'arguments': {}}},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'database_probe', 'arguments': {'sql': 'anything'}}},
            ]
            p = subprocess.run([sys.executable, str(FIXTURE), '--markers', temp],
                               input=''.join(json.dumps(x) + '\n' for x in requests),
                               text=True, capture_output=True, timeout=5)
            self.assertEqual(p.returncode, 0, p.stderr)
            replies = [json.loads(x) for x in p.stdout.splitlines()]
            self.assertEqual([x['error']['code'] for x in replies], [-32602, -32602])
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_discovered_echo_tool_calls_leave_only_their_own_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            requests = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'echo_probe', 'arguments': {}}},
            ]
            p = subprocess.run([sys.executable, str(FIXTURE), '--markers', temp],
                               input=''.join(json.dumps(x) + '\n' for x in requests),
                               text=True, capture_output=True, timeout=5)
            self.assertEqual(p.returncode, 0, p.stderr)
            replies = [json.loads(x) for x in p.stdout.splitlines()]
            self.assertEqual([x['id'] for x in replies], [1, 2, 3])
            self.assertEqual({x['name'] for x in replies[1]['result']['tools']}, {'database_probe', 'echo_probe'})
            self.assertEqual(replies[2]['result']['content'], [{'type': 'text', 'text': 'synthetic:echo_probe:ok'}])
            self.assertEqual([p.name for p in Path(temp).iterdir()], ['echo_probe.jsonl'])


if __name__ == '__main__':
    unittest.main()
