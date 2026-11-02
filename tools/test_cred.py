#!/usr/bin/env python3
"""Focused safety tests for the OS credential boundary."""

import importlib.util
import contextlib
import io
import pathlib
import sys
import types
import unittest
from unittest import mock


CRED_PATH = pathlib.Path(__file__).with_name("cred.py")
SPEC = importlib.util.spec_from_file_location("team2_cred_under_test", CRED_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CredBoundaryTest(unittest.TestCase):
    def test_macos_get_defaults_to_service_only_for_compatibility(self):
        with mock.patch.object(MODULE, "IS_MAC", True), \
             mock.patch.object(
                 MODULE.subprocess,
                 "run",
                 return_value=mock.Mock(returncode=0, stdout="value\n"),
             ) as run:
            self.assertEqual("value", MODULE.get("review-workload@1"))
        self.assertEqual(
            ["security", "find-generic-password", "-s", "review-workload@1", "-w"],
            run.call_args.args[0],
        )

    def test_macos_get_explicit_account_is_scoped(self):
        with mock.patch.object(MODULE, "IS_MAC", True), \
             mock.patch.object(
                 MODULE.subprocess,
                 "run",
                 return_value=mock.Mock(returncode=0, stdout="value\n"),
             ) as run:
            self.assertEqual("value", MODULE.get("review-workload@1", "jm"))
        self.assertEqual(
            ["security", "find-generic-password", "-s", "review-workload@1",
             "-a", "jm", "-w"],
            run.call_args.args[0],
        )

    def test_macos_set_prompts_security_without_secret_in_argv(self):
        with mock.patch.object(MODULE, "IS_MAC", True), \
             mock.patch.object(MODULE.getpass, "getuser", return_value="jm"), \
             mock.patch.object(MODULE.getpass, "getpass", side_effect=AssertionError("must not read secret")), \
             mock.patch.object(MODULE.subprocess, "run", return_value=mock.Mock(returncode=0)) as run, \
             mock.patch("builtins.print"):
            MODULE.set_("review-workload@1")
        argv = run.call_args.args[0]
        self.assertEqual(
            ["security", "add-generic-password", "-U", "-s", "review-workload@1",
             "-a", "jm", "-w"],
            argv,
        )
        self.assertEqual("-w", argv[-1])

    def test_stdin_hex_uses_security_i_and_keeps_secret_out_of_argv(self):
        secret = "ab" * 1704
        stdin = types.SimpleNamespace(buffer=io.BytesIO((secret + "\n").encode("ascii")))
        with mock.patch.object(MODULE, "IS_MAC", True), \
             mock.patch.object(MODULE.getpass, "getuser", return_value="jm"), \
             mock.patch.object(MODULE.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            with mock.patch.object(MODULE.sys, "stdin", stdin):
                MODULE.set_stdin_hex("review-workload@1")
        self.assertEqual(["security", "-i"], run.call_args.args[0])
        self.assertNotIn(secret, run.call_args.args[0])
        command = run.call_args.kwargs["input"]
        self.assertIn(f"-w {secret}\n".encode("ascii"), command)
        self.assertNotIn(b" -U ", command)

    def test_stdin_hex_rejects_invalid_or_oversize_input(self):
        for value in ("abc\n", "not-hex\n", "a" * 3801):
            stdin = types.SimpleNamespace(buffer=io.BytesIO(value.encode("ascii")))
            with self.subTest(value_length=len(value)), \
                 mock.patch.object(MODULE, "IS_MAC", True), \
                 mock.patch.object(MODULE.getpass, "getuser", return_value="jm"), \
                 mock.patch.object(MODULE.sys, "stdin", stdin), \
                 self.assertRaises(ValueError):
                MODULE.set_stdin_hex("review-workload@1")

    def test_stdin_hex_failure_has_nonsecret_cleanup_hint(self):
        stdin = types.SimpleNamespace(buffer=io.BytesIO(("ab" * 4).encode("ascii")))
        with mock.patch.object(MODULE, "IS_MAC", True), \
             mock.patch.object(MODULE.getpass, "getuser", return_value="jm"), \
             mock.patch.object(MODULE.subprocess, "run", return_value=mock.Mock(returncode=1)), \
             mock.patch.object(MODULE.sys, "stdin", stdin), \
             self.assertRaisesRegex(ValueError, r"partial item.*delete-generic-password.*review-workload@1.*jm"):
            MODULE.set_stdin_hex("review-workload@1")

    def test_cli_rejects_stdin_hex_for_non_set_command(self):
        with mock.patch.object(sys, "argv", ["cred.py", "get", "service", "--stdin-hex"]), \
             self.assertRaises(SystemExit) as raised:
            MODULE.main()
        self.assertEqual(2, raised.exception.code)

    def test_cli_explicit_account_is_forwarded(self):
        with mock.patch.object(MODULE, "get", return_value="value") as get, \
             mock.patch.object(sys, "argv", ["cred.py", "get", "service", "--account", "jm"]), \
             contextlib.redirect_stdout(io.StringIO()):
            MODULE.main()
        get.assert_called_once_with("service", "jm")

    def test_cli_rejects_duplicate_account_option(self):
        with mock.patch.object(sys, "argv", ["cred.py", "get", "service", "--account", "jm", "--account", "other"]), \
             self.assertRaises(SystemExit) as raised:
            MODULE.main()
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
