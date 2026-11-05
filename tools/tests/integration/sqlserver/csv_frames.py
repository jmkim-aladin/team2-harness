#!/usr/bin/env python3
"""Q3b release gate: structured CSV frames through real host sqlcmd.

Runs ``db_prod_export.build_batch`` output on an owned loopback SQL Server and
feeds the raw stdout to ``CsvExport`` in 4096-byte pieces (the transport read
size).  Values that plain-text output loses must survive exactly: NULL vs
empty vs literal backslash-N, CRLF inside a value, bigint max, decimal(38,6),
datetime2(7) via explicit CONVERT, 200k Hangul characters, ORDER BY, and an
empty result.  No production profile, Keychain, socket or database is used.
"""
import csv, io, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_transport import LoopbackLab
from verify import DEFAULT_IMAGE
from db_prod_transport import Credentials, SqlcmdBackend
from db_prod_gateway import validate_read_sql
import db_prod_export as ex

COLS = [dict(name=n, type=t) for n, t in [("id", "number"), ("s", "string"), ("n", "number"), ("e", "string"),
                                          ("d", "number"), ("flag", "boolean"), ("dt", "string"), ("longv", "string")]]
SPEC = ex.canonical_spec(COLS, purpose="probe", max_file_bytes=1 << 26, max_record_bytes=1 << 22, max_rows=None)
CASES = {
    "rows": """SELECT v.id, v.s, v.n, v.e, v.d, v.flag, CONVERT(varchar(33), v.dt, 126) AS dt, v.longv
FROM (VALUES
 (CAST(3 AS bigint), N'a,"b"', CAST(NULL AS int), N'', CAST(12345678901234567890.123456 AS decimal(38,6)), CAST(1 AS bit), CAST('2026-11-05T09:10:11.1234567' AS datetime2(7)), N'한글' + NCHAR(13) + NCHAR(10) + N'개행'),
 (CAST(1 AS bigint), N'\\N', 0, N'\\x', CAST(-0.000001 AS decimal(38,6)), CAST(0 AS bit), CAST(NULL AS datetime2(7)), REPLICATE(CAST(N'가' AS nvarchar(max)), 200000)),
 (CAST(9223372036854775807 AS bigint), NULL, -2147483648, NULL, NULL, NULL, CAST('0001-01-01' AS datetime2(7)), N'')
) AS v(id, s, n, e, d, flag, dt, longv)
ORDER BY v.id""",
    "empty": "SELECT CAST(1 AS bigint) AS id, N'' AS s, 1 AS n, N'' AS e, CAST(1 AS decimal(10,2)) AS d, CAST(1 AS bit) AS flag, N'' AS dt, N'' AS longv WHERE 1 = 0",
}


def run(lab, creds, inner):
    batch = ex.build_batch(inner, SPEC)
    validate_read_sql(batch)
    b = SqlcmdBackend(creds, "master", observer_credentials=creds, host_tag="q-probe2", stop_latch=None,
                      startup_timeout=10, observer_timeout=5, query_timeout=60)
    b.start("probe")
    b.dispatch(batch, {"timeout": 60, "max_rows": None, "max_bytes": None})
    deadline = time.monotonic() + 70
    r = b.poll()
    while r is None and time.monotonic() < deadline:
        time.sleep(0.05); r = b.poll()
    raw = bytes(b._result)
    print("poll", r, "failure", b.failure_reason, "stdout", len(raw))
    out = io.BytesIO()
    codec = ex.CsvExport(SPEC, out)
    for i in range(0, len(raw), 4096):
        codec.feed(raw[i:i + 4096])
    stats = codec.finish()
    b.cancel()
    csv.field_size_limit(1 << 24)
    return stats, list(csv.reader(io.StringIO(out.getvalue().decode("utf-8"), newline="")))


def main():
    lab = LoopbackLab(DEFAULT_IMAGE)
    try:
        lab.start()
        creds = Credentials("127.0.0.1", lab.host_port(), "sa", lab.passwords["sa"])
        stats, rows = run(lab, creds, CASES["rows"])
        print(stats)
        for row in rows:
            print([c if len(c) < 40 else ("<%d chars>" % len(c)) for c in row])
        assert rows[0] == [c["name"] for c in COLS]
        assert [r[0] for r in rows[1:]] == ["1", "3", "9223372036854775807"]
        r1, r3, r9 = rows[1], rows[2], rows[3]
        assert r3[1:6] == ['a,"b"', "\\N", "", "12345678901234567890.123456", "true"], r3
        assert r3[6] == "2026-11-05T09:10:11.1234567" and r3[7] == "한글\r\n개행", r3
        assert r1[1] == "\\\\N" and r1[3] == "\\\\x" and r1[4] == "-0.000001" and r1[6] == "\\N" and r1[7] == "가" * 200000, r1[:7]
        assert r9[1] == "\\N" and r9[2] == "-2147483648" and r9[3] == "\\N" and r9[5] == "\\N" and r9[7] == "", r9
        stats, rows = run(lab, creds, CASES["empty"])
        print(stats, rows)
        assert rows == [[c["name"] for c in COLS]] and stats["records"] == 0
        print("GATE PASS")
    finally:
        lab.cleanup()

if __name__ == "__main__":
    main()
