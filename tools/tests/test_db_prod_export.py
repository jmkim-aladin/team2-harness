"""Structured CSV export codec (Q3b slice 1).

Fixtures mirror the host go-sqlcmd output measured on 2026-11-05 against SQL
Server 2022: one varchar(8000) column, ``-h -1``, each row padded with spaces
to 8000 characters, ``L<bytes>`` header then ``H<hex>`` frames of 3999 bytes,
followed by blank lines.
"""
import csv
import hashlib
import io
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db_prod_export as ex  # noqa: E402


COLUMNS = [dict(name="s", type="string"), dict(name="n", type="number"),
           dict(name="e", type="string"), dict(name="flag", type="boolean")]


def spec(columns=COLUMNS, **limits):
    base = dict(max_file_bytes=1 << 20, max_record_bytes=1 << 16, max_rows=None)
    base.update(limits)
    return ex.canonical_spec(columns, purpose="개발 참고", **base)


def sqlcmd_stdout(json_text, *, frame_bytes=ex.FRAME_BYTES, width=ex.FRAME_WIDTH, length=None):
    data = json_text.encode("utf-16-le")
    lines = ["L%d" % (len(data) if length is None else length)]
    for offset in range(0, len(data), frame_bytes):
        lines.append("H" + data[offset:offset + frame_bytes].hex().upper())
    return ("".join(line.ljust(width) + "\n" for line in lines) + "\n\n").encode("ascii")


def run_codec(stdout, the_spec=None, *, pieces=None):
    out = io.BytesIO()
    codec = ex.CsvExport(the_spec or spec(), out)
    if pieces is None:
        codec.feed(stdout)
    else:
        for piece in pieces:
            codec.feed(piece)
    stats = codec.finish()
    return out.getvalue(), stats


def rows_of(csv_bytes):
    csv.field_size_limit(1 << 24)
    return list(csv.reader(io.StringIO(csv_bytes.decode("utf-8"), newline="")))


SAMPLE = json.dumps([
    {"s": 'a,"b"\n한글', "n": None, "e": "", "flag": True},
    {"s": "\\N", "n": 12345678901234567890.123456, "e": "\\x", "flag": False},
], ensure_ascii=False)
# json.dumps would round the decimal; FOR JSON emits exact text.
SAMPLE = SAMPLE.replace("1.2345678901234567e+19", "12345678901234567890.123456")


class SpecTests(unittest.TestCase):
    def test_spec_digest_is_canonical_and_binds_every_field(self):
        a, b = spec(), spec()
        self.assertEqual(a["digest"], b["digest"])
        self.assertNotEqual(a["digest"], spec(max_rows=10)["digest"])
        self.assertNotEqual(a["digest"], spec(columns=COLUMNS[:3])["digest"])
        self.assertEqual(a["spec"]["format"], "development-csv-v1")

    def test_spec_rejects_unsafe_columns_and_limits(self):
        for columns in ([], [dict(name="a.b", type="string")], [dict(name="a", type="string")] * 2,
                        [dict(name="a", type="date")], [dict(name="", type="string")]):
            with self.assertRaises(ex.ExportDenied):
                spec(columns=columns)
        for limits in (dict(max_file_bytes=None), dict(max_file_bytes=0), dict(max_file_bytes=ex.MAX_FILE_BYTES + 1),
                       dict(max_record_bytes=ex.MAX_RECORD_BYTES + 1), dict(max_rows=0)):
            with self.assertRaises(ex.ExportDenied):
                spec(**limits)

    def test_batch_wraps_reviewed_select_without_max_typed_frames(self):
        sql = ex.build_batch("SELECT N'x' AS s ORDER BY 1", spec())
        self.assertIn("FOR JSON PATH, INCLUDE_NULL_VALUES", sql)
        self.assertIn("SELECT N'x' AS s ORDER BY 1", sql)
        # go-sqlcmd truncates (max) types at 256 characters; frames must not use them.
        frame_select = sql[sql.index("SELECT x.frame"):]
        self.assertNotIn("varchar(max)", frame_select.lower())
        for inner in ("SELECT 1; SELECT 2", "SELECT 1 FOR JSON PATH", "SELECT 1\nGO\n", "", "   "):
            with self.assertRaises(ex.ExportDenied):
                ex.build_batch(inner, spec())


class CodecTests(unittest.TestCase):
    def test_values_survive_and_null_differs_from_empty(self):
        data, stats = run_codec(sqlcmd_stdout(SAMPLE))
        rows = rows_of(data)
        self.assertEqual(rows[0], ["s", "n", "e", "flag"])
        self.assertEqual(rows[1], ['a,"b"\n한글', "\\N", "", "true"])
        self.assertEqual(rows[2], ["\\\\N", "12345678901234567890.123456", "\\\\x", "false"])
        self.assertEqual(stats["records"], 2)
        self.assertEqual(stats["csv_bytes"], len(data))
        self.assertEqual(stats["csv_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(stats["source_sha256"], hashlib.sha256(SAMPLE.encode("utf-16-le")).hexdigest())
        self.assertTrue(data.endswith(b"\r\n"))

    def test_every_chunk_boundary_gives_identical_output(self):
        # Small padding keeps the exhaustive cut loop fast; the frame layout is unchanged.
        stdout = sqlcmd_stdout(SAMPLE, frame_bytes=7, width=24)  # many frames, split code units/points
        codec_frame = ex.FRAME_BYTES
        try:
            ex.FRAME_BYTES = 7
            expected, _ = run_codec(stdout)
            for cut in range(1, len(stdout)):
                got, _ = run_codec(stdout, pieces=[stdout[:cut], stdout[cut:]])
                self.assertEqual(got, expected, cut)
            got, _ = run_codec(stdout, pieces=[bytes([b]) for b in stdout])
            self.assertEqual(got, expected)
            rng = random.Random(7)
            for _ in range(50):
                cuts = sorted(rng.sample(range(1, len(stdout)), 6))
                parts = [stdout[i:j] for i, j in zip([0] + cuts, cuts + [len(stdout)])]
                self.assertEqual(run_codec(stdout, pieces=parts)[0], expected)
        finally:
            ex.FRAME_BYTES = codec_frame

    def test_large_value_across_many_frames(self):
        text = json.dumps([{"s": "가" * 300000, "n": 1, "e": "x", "flag": True}], ensure_ascii=False)
        data, stats = run_codec(sqlcmd_stdout(text), spec(max_record_bytes=1 << 21, max_file_bytes=1 << 21))
        self.assertEqual(rows_of(data)[1][0], "가" * 300000)

    def test_empty_result(self):
        data, stats = run_codec(sqlcmd_stdout("[]"))
        self.assertEqual(rows_of(data), [["s", "n", "e", "flag"]])
        self.assertEqual(stats["records"], 0)

    def assertDenied(self, stdout, the_spec=None, reason=None):
        with self.assertRaises(ex.ExportDenied) as caught:
            run_codec(stdout, the_spec)
        if reason:
            self.assertEqual(str(caught.exception), reason)

    def test_truncated_or_inconsistent_frames_are_refused(self):
        good = sqlcmd_stdout(SAMPLE, frame_bytes=7, width=24)
        lines = good.split(b"\n")
        try:
            saved, ex.FRAME_BYTES = ex.FRAME_BYTES, 7
            short_middle = lines[:2] + [lines[2].rstrip()[:-2]] + lines[3:]
            self.assertDenied(b"\n".join(short_middle), reason="frame_truncated")
            self.assertDenied(sqlcmd_stdout(SAMPLE, frame_bytes=7, width=24, length=10), reason="frame_length_mismatch")
            self.assertDenied(b"\n".join(lines[:-4]) + b"\n", reason="frame_length_mismatch")
            self.assertDenied(b"\n".join(lines[:3] + [b""] + lines[3:]), reason="frame_unexpected_blank")
            self.assertDenied(b"\n".join([lines[0], lines[1].replace(b"H", b"X", 1)] + lines[2:]), reason="frame_invalid")
            self.assertDenied(b"\n".join([lines[0], b"H5B0G" + lines[1][5:]] + lines[2:]), reason="frame_invalid")
            self.assertDenied(good + b"H00\n", reason="frame_after_end")
            self.assertDenied(b"", reason="frame_missing_header")
            self.assertDenied(b"x" * (ex.FRAME_WIDTH + 64), reason="frame_line_too_long")
        finally:
            ex.FRAME_BYTES = saved

    def test_json_structure_and_types_are_enforced(self):
        bad = {
            "json_key_mismatch": '[{"s":"a","e":"","n":1,"flag":true}]',
            "json_duplicate_key": '[{"s":"a","s":"b","n":1,"e":"","flag":true}]',
            "json_key_missing": '[{"s":"a","n":1,"e":""}]',
            "json_type_mismatch": '[{"s":1,"n":1,"e":"","flag":true}]',
            "json_nested_value": '[{"s":{"x":1},"n":1,"e":"","flag":true}]',
            "json_structure_invalid": '{"s":"a"}',
            "json_trailing_data": '[]x',
        }
        for reason, text in bad.items():
            self.assertDenied(sqlcmd_stdout(text), reason=reason)
        self.assertDenied(sqlcmd_stdout('[{"s":"a","n":"1","e":"","flag":true}]'), reason="json_type_mismatch")
        self.assertDenied(sqlcmd_stdout('[{"s":"a","n":NaN,"e":"","flag":true}]'), reason="json_invalid")

    def test_invalid_utf16_is_refused(self):
        raw = "[".encode("utf-16-le") + b"\x00\xd8" + "]".encode("utf-16-le")  # lone high surrogate
        lines = ["L%d" % len(raw), "H" + raw.hex().upper()]
        stdout = ("".join(l.ljust(ex.FRAME_WIDTH) + "\n" for l in lines) + "\n").encode()
        self.assertDenied(stdout, reason="source_encoding_invalid")

    def test_limits_stop_without_buffering_everything(self):
        many = json.dumps([{"s": "x" * 50, "n": i, "e": "", "flag": True} for i in range(100)])
        self.assertDenied(sqlcmd_stdout(many), spec(max_rows=99), reason="export_rows_exceeded")
        self.assertDenied(sqlcmd_stdout(many), spec(max_file_bytes=1000), reason="export_file_bytes_exceeded")
        big = json.dumps([{"s": "x" * 5000, "n": 1, "e": "", "flag": True}])
        self.assertDenied(sqlcmd_stdout(big), spec(max_record_bytes=1024), reason="export_record_bytes_exceeded")

    def test_failed_codec_reports_no_completion(self):
        out = io.BytesIO()
        codec = ex.CsvExport(spec(), out)
        codec.feed(sqlcmd_stdout(SAMPLE)[:100])
        with self.assertRaises(ex.ExportDenied):
            codec.finish()
        with self.assertRaises(ex.ExportDenied):
            codec.feed(b"H00\n")


if __name__ == "__main__":
    unittest.main()
