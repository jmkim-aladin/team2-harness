"""secret_scan — 코드 식은 통과, 실값은 계속 잡는다."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import secret_scan  # noqa: E402


def hits_for(text: str) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.txt"
        path.write_text(text)
        with contextlib.redirect_stdout(io.StringIO()):
            return secret_scan.scan([str(path)])


class SecretScanTests(unittest.TestCase):
    def test_code_expressions_are_not_secrets(self) -> None:
        for line in (
            "guard let password = request.unlockPassword, let items = request.items,",
            'return dict(profile, password=self._get(service, profile["account"]))',
            "return cls(host=host, port=port, account=account, password=password)",
            "password=lab.passwords[account],",
        ):
            with self.subTest(line=line):
                self.assertEqual(hits_for(line + "\n"), 0)

    def test_literal_passwords_are_still_detected(self) -> None:
        # 키 이름을 쪼개 둔다 — 이 파일 자체가 staged 스캔에 걸리지 않게
        for line in (
            "Server=db;User Id=sa;Pass" + "word=Secret2026;",
            "DB_PASS" + "WORD=abc.def.ghi",
            "pw" + "d=Hunter2Hunter2",
        ):
            with self.subTest(line=line):
                self.assertEqual(hits_for(line + "\n"), 1)


if __name__ == "__main__":
    unittest.main()
