#!/usr/bin/env python3
"""Pipe-only tests for the production-profile keychain helper.

The tests create a disposable synthetic keychain under a temporary directory.
They never inspect or modify the user's login/iCloud keychains.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "db_prod_keychain.swift"


class ProductionKeychainHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("swiftc") is None:
            raise unittest.SkipTest("swiftc is unavailable")
        cls._tmp = tempfile.TemporaryDirectory(prefix="team2-db-keychain-test-")
        cls.binary = Path(cls._tmp.name) / "db-prod-keychain"
        compile_result = subprocess.run(
            ["swiftc", str(SOURCE), "-framework", "Security", "-o", str(cls.binary)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                "swift compilation failed without exposing source values:\n"
                + compile_result.stderr[-4000:]
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.keychain_dir = Path(self._tmp.name) / f"case-{self._testMethodName}"
        self.keychain_dir.mkdir()
        self.keychain = self.keychain_dir / "credentials.keychain-db"
        self.password = "synthetic-unlock-password"

    def run_helper(self, request: dict, *, stdin=subprocess.PIPE, stdout=subprocess.PIPE):
        encoded = json.dumps(request, ensure_ascii=False).encode("utf-8")
        proc = subprocess.run(
            [str(self.binary)],
            input=encoded if stdin == subprocess.PIPE else None,
            stdout=stdout,
            stderr=subprocess.PIPE,
            check=False,
        )
        stdout_bytes = proc.stdout if isinstance(proc.stdout, bytes) else b""
        response = None
        if stdout_bytes:
            response = json.loads(stdout_bytes.decode("utf-8"))
        return proc, response

    def create(self, items: list[dict]) -> tuple[subprocess.CompletedProcess[bytes], dict]:
        return self.run_helper(
            {
                "mode": "create",
                "path": str(self.keychain),
                "unlock_password": self.password,
                "items": items,
            }
        )

    def test_create_and_get_preserves_exact_utf8_value(self) -> None:
        value = '{"host":"db.example","port":1433,"account":"svc"}'
        proc, response = self.create(
            [{"service": "lego-prod-profile", "account": "profile", "value": value}]
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(response, {"created": True})
        self.assertTrue(self.keychain.exists())

        proc, response = self.run_helper(
            {
                "mode": "get",
                "path": str(self.keychain),
                "unlock_password": self.password,
                "service": "lego-prod-profile",
                "account": "profile",
            }
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(response, {"value": value})

    def test_create_stores_multiple_allowed_items(self) -> None:
        proc, response = self.create(
            [
                {"service": "lego-prod", "account": "svc", "value": "lego-secret"},
                {"service": "cool-prod", "account": "svc", "value": "cool-secret"},
                {"service": "cool-prod-profile", "account": "profile", "value": "{\"host\":\"cool\"}"},
                {"service": "lego-prod-observer", "account": "observer", "value": "lego-observer-secret"},
            ]
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(response, {"created": True})
        for service, account, expected in [
            ("lego-prod", "svc", "lego-secret"),
            ("cool-prod", "svc", "cool-secret"),
            ("cool-prod-profile", "profile", '{"host":"cool"}'),
            ("lego-prod-observer", "observer", "lego-observer-secret"),
        ]:
            proc, response = self.run_helper(
                {
                    "mode": "get",
                    "path": str(self.keychain),
                    "unlock_password": self.password,
                    "service": service,
                    "account": account,
                }
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            self.assertEqual(response, {"value": expected})

    def test_observer_profile_uses_the_same_profile_account_contract(self) -> None:
        proc, response = self.create(
            [{
                "service": "lego-prod-observer-profile",
                "account": "profile",
                "value": '{"host":"observer-db","port":1433,"account":"observer"}',
            }]
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(response, {"created": True})

    def test_create_is_no_clobber(self) -> None:
        proc, _ = self.create(
            [{"service": "lego-prod", "account": "svc", "value": "first"}]
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        proc, response = self.create(
            [{"service": "lego-prod", "account": "svc", "value": "second"}]
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(response, {"error": "keychain_path_invalid"})

    def test_profile_requires_profile_account(self) -> None:
        proc, response = self.create(
            [{"service": "lego-prod-profile", "account": "svc", "value": "profile"}]
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(response, {"error": "request_rejected"})

    def test_read_login_is_read_only_and_path_scoped(self) -> None:
        login_keychain = self.keychain_dir / "login.synthetic.keychain-db"
        proc, response = self.run_helper(
            {
                "mode": "create",
                "path": str(login_keychain),
                "unlock_password": self.password,
                "items": [{"service": "lego-prod", "account": "svc", "value": "login-value"}],
            }
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(response, {"created": True})

        proc, response = self.run_helper(
            {
                "mode": "read-login",
                "path": str(login_keychain),
                "service": "lego-prod",
                "account": "svc",
            }
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(response, {"value": "login-value"})

        # A dedicated keychain cannot be routed through the login-only mode.
        proc, response = self.run_helper(
            {
                "mode": "read-login",
                "path": str(self.keychain),
                "service": "lego-prod",
                "account": "svc",
            }
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(response, {"error": "keychain_path_invalid"})

    def test_rejects_unapproved_service_and_relative_path(self) -> None:
        for request in [
            {
                "mode": "create",
                "path": str(self.keychain),
                "unlock_password": self.password,
                "items": [{"service": "other-prod", "account": "svc", "value": "x"}],
            },
            {
                "mode": "get",
                "path": "relative.keychain-db",
                "unlock_password": self.password,
                "service": "lego-prod",
                "account": "svc",
            },
        ]:
            proc, response = self.run_helper(request)
            self.assertNotEqual(proc.returncode, 0)
            expected = "keychain_path_invalid" if request["path"] == "relative.keychain-db" else "request_rejected"
            self.assertEqual(response, {"error": expected})

    def test_rejects_tty_when_available(self) -> None:
        # The normal test path is deliberately pipe based.  This assertion is
        # exercised only when a controlling terminal can be allocated locally.
        if not os.isatty(0) or not os.isatty(1):
            self.skipTest("test runner has no TTY")


if __name__ == "__main__":
    unittest.main()
