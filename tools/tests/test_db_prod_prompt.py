"""Real PTY input and client admission checks; no DB connections."""
import io
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import db_prod_client as client
from db_prod_prompt import confirm_operator


class TerminalMenuTests(unittest.TestCase):
    def menu(self, keys, *, approved, interrupt=False, first_keys=None):
        master, slave = pty.openpty()
        script = '''import json,select,sys,termios
sys.path.insert(0,sys.argv[1])
from db_prod_prompt import confirm_operator
before=termios.tcgetattr(0)
try:
    answer=confirm_operator("SYNTHETIC REVIEW — no DB")
except KeyboardInterrupt:
    answer=False
after=termios.tcgetattr(0)
# macOS marks pending canonical input on ICANON restoration. This is a
# transient kernel flag, not an unrestored terminal preference.
before[3] &= ~getattr(termios, 'PENDIN', 0)
after[3] &= ~getattr(termios, 'PENDIN', 0)
pending=bool(select.select([0], [], [], 0)[0])
print("RESULT="+json.dumps(dict(approved=answer,restored=before==after,pending=pending)))
'''
        process = subprocess.Popen([sys.executable, '-I', '-c', script, str(TOOLS)],
                                   stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        output = bytearray()
        sent = False
        deadline = time.monotonic() + 5
        try:
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output.extend(chunk)
                    if not sent and b'> 1 ' in output:
                        if first_keys is not None:
                            os.write(master, first_keys)
                            # Choosing an item alone must leave the prompt open.
                            time.sleep(0.05)
                            self.assertIsNone(process.poll(), bytes(output))
                        if interrupt:
                            os.kill(process.pid, signal.SIGINT)
                        else:
                            os.write(master, keys)
                        sent = True
                if process.poll() is not None:
                    # Read until PTY EOF rather than dropping the final result.
                    if not select.select([master], [], [], 0.1)[0]:
                        break
            process.wait(timeout=1)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
        decoded = output.decode(errors='replace')
        self.assertEqual(process.returncode, 0, decoded)
        marker = decoded.rsplit('RESULT=', 1)
        self.assertEqual(len(marker), 2, decoded)
        self.assertEqual(json.loads(marker[1].strip()), dict(approved=approved, restored=True, pending=False))
        return decoded

    def test_enter_explicitly_confirms_default_approval(self):
        self.menu(b'\r', approved=True)

    def test_numeric_selection_requires_enter_and_maps_all_choices(self):
        for keys, approved in [(b'1', True), (b'2', False), (b'3', False)]:
            with self.subTest(keys=keys):
                self.menu(b'\r', first_keys=keys, approved=approved)

    def test_keyboard_interrupt_restores_terminal_without_approval(self):
        self.menu(b'', approved=False, interrupt=True)

    def test_arrow_selection_and_wrap(self):
        for keys, approved in [(b'\x1b[B\r', False), (b'\x1b[A\r', False),
                               (b'\x1b[B\x1b[A\r', True)]:
            with self.subTest(keys=keys):
                self.menu(keys, approved=approved)

    def test_escape_eof_and_unknown_escape_cancel(self):
        for keys in (b'\x1b', b'\x04', b'\x1b[200~pasted\r'):
            with self.subTest(keys=keys):
                self.menu(keys, approved=False)

    def test_unknown_text_then_enter_does_not_approve(self):
        self.menu(b'bad\r3\r', approved=False)

    def test_pipes_and_unseen_redirected_output_are_rejected(self):
        for stdin_tty, stdout_tty in [(False, True), (True, False), (False, False)]:
            with self.subTest(stdin_tty=stdin_tty, stdout_tty=stdout_tty), \
                 patch.object(sys.stdin, 'isatty', return_value=stdin_tty), \
                 patch.object(sys.stdout, 'isatty', return_value=stdout_tty):
                with self.assertRaisesRegex(RuntimeError, 'operator_terminal_required'):
                    confirm_operator('review')


class ClientMenuGateTests(unittest.TestCase):
    def invoke(self, action, answer, *, digest=None):
        calls = []
        review = dict(api_version=2, digest='a' * 64, approval_digest='b' * 64,
                      selected_actions=['execute_once'], request_id='synthetic')

        def rpc(request):
            calls.append(request)
            if request['action'] == 'status':
                return dict(ok=True, active=None, phase='idle', epoch=7,
                            stop_generation=2, stop_markers=['synthetic-nonce'])
            if request['action'] in ('review', 'recovery_review'):
                return dict(ok=True, review=review)
            return dict(ok=True)

        argv = ['client', action] + ([] if action == 'resume' else ['synthetic'])
        if digest is not None:
            argv += ['--from-chat-digest', digest]
        with patch.object(sys, 'argv', argv), patch.object(sys.stdin, 'isatty', return_value=True), \
             patch.object(client, 'require_current_gateway'), patch.object(client, 'rpc', side_effect=rpc), \
             patch.object(client, 'display_review'), patch.object(client, 'display_recovery_review'), \
             patch.object(client, 'receive_job', return_value=dict(ok=True)), \
             patch.object(client, 'confirm_operator', return_value=answer) as menu, \
             redirect_stdout(io.StringIO()):
            code = client.main()
        return code, calls, menu

    def test_declined_menu_never_sends_admission_or_resume(self):
        for action in ('approve', 'run', 'recovery-approve', 'resume'):
            with self.subTest(action=action):
                code, calls, menu = self.invoke(action, False)
                self.assertEqual(code, 1)
                self.assertEqual(len(calls), 1)
                self.assertIn(calls[0]['action'], ('review', 'recovery_review', 'status'))
                menu.assert_called_once()

    def test_approval_preserves_exact_digest_actions_and_resume_snapshot(self):
        for action, admission in [('approve', 'approve'), ('run', 'approve_submit'),
                                  ('recovery-approve', 'recovery_approve'), ('resume', 'resume')]:
            with self.subTest(action=action):
                code, calls, menu = self.invoke(action, True)
                self.assertEqual(code, 0)
                self.assertEqual(calls[1]['action'], admission)
                self.assertEqual(len(calls), 2)
                menu.assert_called_once()
                if action == 'run':
                    self.assertEqual(calls[1]['approval_digest'], 'b' * 64)
                    self.assertEqual(calls[1]['selected_actions'], ['execute_once'])
                elif action == 'resume':
                    self.assertEqual(calls[1]['expected_epoch'], 7)
                    self.assertEqual(calls[1]['expected_stop_generation'], 2)
                    self.assertEqual(calls[1]['expected_stop_markers'], ['synthetic-nonce'])
                else:
                    self.assertEqual(calls[1]['digest'], 'a' * 64)

    def test_chat_approval_uses_full_digest_and_bypasses_terminal_menu(self):
        code, calls, menu = self.invoke('run', False, digest='b' * 64)
        self.assertEqual(code, 0)
        self.assertEqual(calls[1]['approval_source'], 'explicit-user-chat')
        menu.assert_not_called()
        code, calls, menu = self.invoke('run', True, digest='a' * 64)
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 1)
        menu.assert_not_called()


if __name__ == '__main__':
    unittest.main()
