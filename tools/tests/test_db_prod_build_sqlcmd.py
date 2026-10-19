"""Offline checks for the pinned DataGrip-labelled sqlcmd builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "db_prod_build_sqlcmd", ROOT / "tools" / "db_prod_build_sqlcmd.py"
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class BuilderTests(unittest.TestCase):
    def test_patch_changes_only_application_name_line(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source_file = source / BUILDER.SOURCE_FILE
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                'package sqlcmd\n\n'
                'func setConnect() {\n'
                '\tconnect.ApplicationName = "sqlcmd"\n'
                '}\n',
                encoding="utf-8",
            )
            patched = root / "patched"
            result = BUILDER._patch_source(source, patched)
            self.assertEqual(result["changed_lines"], 1)
            self.assertIn('ApplicationName = "DataGrip"',
                          (patched / BUILDER.SOURCE_FILE).read_text(encoding="utf-8"))
            self.assertEqual(result["old"], '\tconnect.ApplicationName = "sqlcmd"')
            self.assertEqual(result["new"], '\tconnect.ApplicationName = "DataGrip"')

    def test_archive_path_traversal_is_rejected(self):
        with self.assertRaises(BUILDER.BuildError):
            BUILDER._safe_member_path("go-sqlcmd-dead/../escape", "go-sqlcmd-dead")

    def test_non_official_source_url_is_rejected(self):
        with self.assertRaises(BUILDER.BuildError):
            BUILDER._validate_source_url("https://example.invalid/source.tar.gz")


if __name__ == "__main__":
    unittest.main()
