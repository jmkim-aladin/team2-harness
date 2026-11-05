"""Structured CSV export codec for approved production queries (development-csv-v1).

The reviewed batch turns one SELECT into ``FOR JSON PATH, INCLUDE_NULL_VALUES``
and returns the UTF-16LE bytes as hex frames in a single ``varchar(8000)``
column.  Host go-sqlcmd truncates ``(max)`` types at 256 characters without an
error (measured 2026-11-05), so frames are fixed, non-max, and every non-final
frame must be full: a short frame is truncation, never data.

``CsvExport`` consumes raw stdout in arbitrary pieces with bounded buffers
(one frame line, one partial UTF-16 code unit, one JSON record) and writes CSV
bytes to a caller-owned binary stream.  It never parses the whitespace-aligned
plain text output and never re-runs SQL.  Any doubt raises ``ExportDenied``;
the caller must then discard the staging file.
"""
import codecs
import csv
import hashlib
import io
import json
import re

FORMAT = "development-csv-v1"
FRAME_PROTOCOL = "for-json-utf16le-hex-varchar8000-v1"
FRAME_BYTES = 3999           # 7998 hex chars + 'H' = 7999 <= varchar(8000)
FRAME_WIDTH = 8000           # sqlcmd pads every row to the column width
MAX_FILE_BYTES = 1 << 30
MAX_RECORD_BYTES = 16 << 20
MAX_ROWS = 10 ** 9
MAX_SOURCE_BYTES = 1 << 33
NULL_TOKEN = "\\N"
COLUMN_TYPES = ("string", "number", "boolean")
_COLUMN_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_HEX = re.compile(rb"[0-9A-F]*\Z")
_HEADER = re.compile(rb"L(0|[1-9][0-9]{0,11})\Z")


class ExportDenied(Exception):
    """A structural, limit or protocol violation. ``str()`` is a fixed reason code."""


class _Number(str):
    """JSON number text kept verbatim (no float rounding)."""


def _reject_constant(_):
    raise ExportDenied("json_invalid")


def _positive(value, upper, reason, *, allow_none=False):
    if value is None and allow_none:
        return None
    if type(value) is not int or not 0 < value <= upper:
        raise ExportDenied(reason)
    return value


def canonical_spec(columns, *, purpose, max_file_bytes, max_record_bytes, max_rows,
                   max_source_bytes=None, artifact_directory=None):
    """Return ``dict(spec=..., digest=...)``; the digest binds every field."""
    if not isinstance(columns, list) or not columns:
        raise ExportDenied("export_columns_required")
    names = []
    normalized = []
    for column in columns:
        if not isinstance(column, dict) or set(column) != {"name", "type"}:
            raise ExportDenied("export_column_invalid")
        name, kind = column["name"], column["type"]
        if not isinstance(name, str) or not _COLUMN_NAME.match(name) or kind not in COLUMN_TYPES:
            raise ExportDenied("export_column_invalid")
        if name in names:
            raise ExportDenied("export_column_duplicate")
        names.append(name)
        normalized.append(dict(name=name, type=kind))
    if not isinstance(purpose, str) or not purpose.strip() or len(purpose) > 200 \
            or any(ord(c) < 32 for c in purpose):
        raise ExportDenied("export_purpose_invalid")
    spec = dict(
        format=FORMAT,
        frame_protocol=FRAME_PROTOCOL,
        encoding="utf-8",
        line_terminator="\r\n",
        header=True,
        null_token=NULL_TOKEN,
        leading_backslash="doubled",
        columns=normalized,
        purpose=purpose,
        max_file_bytes=_positive(max_file_bytes, MAX_FILE_BYTES, "export_file_limit_invalid"),
        max_record_bytes=_positive(max_record_bytes, MAX_RECORD_BYTES, "export_record_limit_invalid"),
        max_rows=_positive(max_rows, MAX_ROWS, "export_row_limit_invalid", allow_none=True),
    )
    # sqlcmd stdout (hex frames + padding) bound; shown in the review like every other limit.
    spec["max_source_bytes"] = _positive(
        max_source_bytes if max_source_bytes is not None else min(8 * spec["max_file_bytes"] + (1 << 20), MAX_SOURCE_BYTES),
        MAX_SOURCE_BYTES, "export_source_limit_invalid")
    if artifact_directory is not None:
        if not isinstance(artifact_directory, str) or not artifact_directory.startswith("/"):
            raise ExportDenied("export_directory_invalid")
        spec["artifact_directory"] = artifact_directory
    return dict(spec=spec, digest=spec_digest(spec))


def spec_digest(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def build_batch(select_sql, spec):
    """The complete batch the reviewer approves; nothing is added after approval."""
    if not isinstance(select_sql, str) or not select_sql.strip():
        raise ExportDenied("export_select_required")
    if ";" in select_sql or re.search(r"\bFOR\s+(JSON|XML|BROWSE)\b", select_sql, re.I) \
            or re.search(r"^\s*GO\s*$", select_sql, re.I | re.M) or "\x00" in select_sql:
        raise ExportDenied("export_select_single_statement")
    spec = spec["spec"] if "spec" in spec else spec
    if spec.get("frame_protocol") != FRAME_PROTOCOL:
        raise ExportDenied("export_protocol_unsupported")
    return (
        "SET NOCOUNT ON;\n"
        "DECLARE @j nvarchar(max) = (\n"
        + select_sql.strip() + "\n"
        "FOR JSON PATH, INCLUDE_NULL_VALUES);\n"
        "DECLARE @b varbinary(max) = CAST(COALESCE(@j, N'[]') AS varbinary(max));\n"
        "DECLARE @n bigint = DATALENGTH(@b);\n"
        "WITH d AS (SELECT v FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS t(v)),\n"
        "f AS (SELECT TOP (CAST((@n + %d) / %d AS bigint)) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i\n"
        "      FROM d a CROSS JOIN d b CROSS JOIN d c CROSS JOIN d e CROSS JOIN d g CROSS JOIN d h)\n"
        "SELECT x.frame FROM (\n"
        "  SELECT CAST(0 AS bigint) AS i, CAST('L' + CAST(@n AS varchar(20)) AS varchar(8000)) AS frame\n"
        "  UNION ALL\n"
        "  SELECT i, CAST('H' + CONVERT(varchar(8000), SUBSTRING(@b, (i - 1) * %d + 1, %d), 2) AS varchar(8000)) FROM f\n"
        ") AS x ORDER BY x.i;\n"
    ) % (FRAME_BYTES - 1, FRAME_BYTES, FRAME_BYTES, FRAME_BYTES)


class CsvExport:
    """stdout pieces -> frames -> UTF-16LE -> JSON records -> CSV bytes."""

    def __init__(self, export_spec, sink):
        spec = export_spec["spec"] if "spec" in export_spec else export_spec
        if spec.get("format") != FORMAT or spec.get("frame_protocol") != FRAME_PROTOCOL:
            raise ExportDenied("export_protocol_unsupported")
        self.spec = spec
        self.names = [c["name"] for c in spec["columns"]]
        self.types = [c["type"] for c in spec["columns"]]
        self.sink = sink
        self.frame_hex = FRAME_BYTES * 2
        self.failed = None
        self.finished = False
        # frame layer
        self.line = bytearray()
        self.expected = None
        self.decoded = 0
        self.short_seen = False
        self.blank_seen = False
        self.source_hash = hashlib.sha256()
        self.decoder = codecs.getincrementaldecoder("utf-16-le")("strict")
        # json layer
        self.stage = "start"        # start -> items -> after_item -> end
        self.record = []
        self.record_bytes = 0
        self.depth = 0
        self.in_string = False
        self.escape = False
        # csv layer
        self.csv_hash = hashlib.sha256()
        self.csv_bytes = 0
        self.records = 0
        self._write_row(self.names)

    # -- public -----------------------------------------------------------
    def feed(self, chunk):
        self._alive()
        try:
            for byte_line in self._lines(bytes(chunk)):
                self._frame(byte_line)
        except ExportDenied as error:
            self.failed = str(error)
            raise

    def finish(self):
        self._alive()
        try:
            if self.line.strip(b" \r"):
                self._frame(bytes(self.line))
            self.line.clear()
            if self.expected is None:
                raise ExportDenied("frame_missing_header")
            if self.decoded != self.expected:
                raise ExportDenied("frame_length_mismatch")
            try:
                tail = self.decoder.decode(b"", final=True)
            except UnicodeDecodeError:
                raise ExportDenied("source_encoding_invalid") from None
            self._text(tail)
            if self.stage != "end":
                raise ExportDenied("json_structure_invalid")
        except ExportDenied as error:
            self.failed = str(error)
            raise
        self.finished = True
        return dict(records=self.records, csv_bytes=self.csv_bytes, csv_sha256=self.csv_hash.hexdigest(),
                    source_bytes=self.decoded, source_sha256=self.source_hash.hexdigest())

    # -- frame layer ------------------------------------------------------
    def _alive(self):
        if self.failed is not None or self.finished:
            raise ExportDenied(self.failed or "export_already_finished")

    def _lines(self, chunk):
        start = 0
        while True:
            newline = chunk.find(b"\n", start)
            if newline < 0:
                self.line.extend(chunk[start:])
                if len(self.line) > FRAME_WIDTH + 1:
                    raise ExportDenied("frame_line_too_long")
                return
            self.line.extend(chunk[start:newline])
            if len(self.line) > FRAME_WIDTH + 1:
                raise ExportDenied("frame_line_too_long")
            yield bytes(self.line)
            self.line.clear()
            start = newline + 1

    def _frame(self, raw):
        line = raw.rstrip(b"\r").rstrip(b" ")
        complete = self.expected is not None and self.decoded == self.expected
        if not line:
            if self.expected is not None and not complete:
                self.blank_seen = True
            return
        if complete and self.expected is not None and (self.decoded > 0 or self.expected == 0):
            raise ExportDenied("frame_after_end")
        if self.blank_seen:
            raise ExportDenied("frame_unexpected_blank")
        if self.expected is None:
            match = _HEADER.match(line)
            if not match:
                raise ExportDenied("frame_missing_header" if not line.startswith(b"H") else "frame_invalid")
            self.expected = int(match.group(1))
            return
        if line[:1] != b"H" or not _HEX.match(line[1:]) or len(line) % 2 == 0 or len(line) == 1:
            raise ExportDenied("frame_invalid")
        if self.short_seen:
            raise ExportDenied("frame_truncated")
        size = len(line) - 1
        if size > self.frame_hex:
            raise ExportDenied("frame_invalid")
        if size < self.frame_hex:
            self.short_seen = True
        data = bytes.fromhex(line[1:].decode("ascii"))
        if self.decoded + len(data) > self.expected:
            raise ExportDenied("frame_length_mismatch")
        self.decoded += len(data)
        self.source_hash.update(data)
        try:
            text = self.decoder.decode(data)
        except UnicodeDecodeError:
            raise ExportDenied("source_encoding_invalid") from None
        self._text(text)

    # -- json layer -------------------------------------------------------
    def _text(self, text):
        for char in text:
            if self.stage == "start":
                if char in " \t\r\n":
                    continue
                if char != "[":
                    raise ExportDenied("json_structure_invalid")
                self.stage = "items"
            elif self.stage in ("items", "after_item"):
                if self.depth == 0:
                    if char in " \t\r\n":
                        continue
                    if char == "]":
                        self.stage = "end"
                    elif char == "," and self.stage == "after_item":
                        self.stage = "items"
                    elif char == "{" and self.stage == "items":
                        self.depth = 1
                        self._append(char)
                    else:
                        raise ExportDenied("json_structure_invalid")
                    continue
                self._append(char)
                if self.in_string:
                    if self.escape:
                        self.escape = False
                    elif char == "\\":
                        self.escape = True
                    elif char == '"':
                        self.in_string = False
                elif char == '"':
                    self.in_string = True
                elif char in "{[":
                    raise ExportDenied("json_nested_value")
                elif char == "}":
                    self.depth = 0
                    self._emit("".join(self.record))
                    self.record.clear()
                    self.record_bytes = 0
                    self.stage = "after_item"
            elif self.stage == "end":
                if char not in " \t\r\n":
                    raise ExportDenied("json_trailing_data")

    def _append(self, char):
        self.record_bytes += len(char.encode("utf-8"))
        if self.record_bytes > self.spec["max_record_bytes"]:
            raise ExportDenied("export_record_bytes_exceeded")
        self.record.append(char)

    def _emit(self, text):
        try:
            pairs = json.loads(text, object_pairs_hook=lambda p: p, parse_int=_Number,
                               parse_float=_Number, parse_constant=_reject_constant)
        except ExportDenied:
            raise
        except ValueError:
            raise ExportDenied("json_invalid") from None
        keys = [key for key, _ in pairs]
        if len(set(keys)) != len(keys):
            raise ExportDenied("json_duplicate_key")
        if keys != self.names:
            if set(keys) < set(self.names):
                raise ExportDenied("json_key_missing")
            raise ExportDenied("json_key_mismatch")
        row = []
        for (_, value), kind in zip(pairs, self.types):
            if value is None:
                row.append(NULL_TOKEN)
            elif kind == "boolean" and isinstance(value, bool):
                row.append("true" if value else "false")
            elif kind == "number" and isinstance(value, _Number):
                row.append(str(value))
            elif kind == "string" and type(value) is str:
                row.append("\\" + value if value.startswith("\\") else value)
            else:
                raise ExportDenied("json_type_mismatch")
        self.records += 1
        if self.spec["max_rows"] is not None and self.records > self.spec["max_rows"]:
            raise ExportDenied("export_rows_exceeded")
        self._write_row(row)

    # -- csv layer --------------------------------------------------------
    def _write_row(self, row):
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL).writerow(row)
        data = buffer.getvalue().encode("utf-8")
        if self.csv_bytes + len(data) > self.spec["max_file_bytes"]:
            raise ExportDenied("export_file_bytes_exceeded")
        self.sink.write(data)
        self.csv_hash.update(data)
        self.csv_bytes += len(data)


# ---------------------------------------------------------------------------
# Staging, durable completion, publication and reconciliation
# ---------------------------------------------------------------------------
import ctypes  # noqa: E402
import ctypes.util  # noqa: E402
import datetime  # noqa: E402
import errno as _errno  # noqa: E402
import os  # noqa: E402
import stat as _stat  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

RENAME_EXCL = 0x00000004
OPEN_STATES = ("exporting", "complete", "export_unknown")
_libc = None


def rename_no_replace(source, destination):
    """Atomic directory rename that fails with FileExistsError instead of replacing."""
    global _libc
    if sys.platform != "darwin":
        raise ExportDenied("no_replace_rename_unavailable")
    if _libc is None:
        _libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        _libc.renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    if _libc.renamex_np(os.fsencode(str(source)), os.fsencode(str(destination)), RENAME_EXCL) != 0:
        code = ctypes.get_errno()
        if code == _errno.EEXIST:
            raise FileExistsError(code, os.strerror(code), str(destination))
        raise OSError(code, os.strerror(code), str(destination))


def _fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _private_root(root, *, create):
    root = Path(root)
    if create and not os.path.lexists(root):
        os.mkdir(root, 0o700)
    info = os.lstat(root)
    if (not _stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ExportDenied("export_root_untrusted")
    return root


def _remove_owned_dir(path):
    """Remove only a real directory holding our two regular files (never follows links)."""
    if not os.path.lexists(path):
        return
    info = os.lstat(path)
    if not _stat.S_ISDIR(info.st_mode):
        raise ExportDenied("export_staging_untrusted")
    for name in os.listdir(path):
        child = Path(path) / name
        if name not in ("data.csv", "manifest.json") or not _stat.S_ISREG(os.lstat(child).st_mode):
            raise ExportDenied("export_staging_untrusted")
        os.unlink(child)
    os.rmdir(path)


class ExportLedger:
    """Export lineage and state. Holds digests and counts, never result values or SQL."""

    def __init__(self, store, exports_root):
        self.store, self.root = store, Path(exports_root)
        with store.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS query_exports_v1 (
                request_id TEXT PRIMARY KEY, owner TEXT NOT NULL, run_id TEXT NOT NULL, epoch INTEGER NOT NULL,
                spec_digest TEXT NOT NULL, final TEXT NOT NULL, staging TEXT NOT NULL, state TEXT NOT NULL,
                reason TEXT, source_sha256 TEXT, source_bytes INTEGER, csv_sha256 TEXT, csv_bytes INTEGER,
                records INTEGER, updated REAL NOT NULL)''')
        self.reconcile()

    def status(self, request_id):
        with self.store.transaction() as c:
            row = c.execute("SELECT * FROM query_exports_v1 WHERE request_id=?", (request_id,)).fetchone()
        return dict(row) if row else None

    def intent(self, request_id, owner, run_id, epoch, spec_digest_value, final, staging):
        with self.store.transaction() as c:
            c.execute("INSERT INTO query_exports_v1 (request_id,owner,run_id,epoch,spec_digest,final,staging,state,updated)"
                      " VALUES (?,?,?,?,?,?,?,'exporting',?)",
                      (request_id, owner, run_id, epoch, spec_digest_value, str(final), str(staging), time.time()))

    def complete(self, request_id, stats):
        with self.store.transaction() as c:
            changed = c.execute("UPDATE query_exports_v1 SET state='complete',source_sha256=?,source_bytes=?,"
                                "csv_sha256=?,csv_bytes=?,records=?,updated=? WHERE request_id=? AND state='exporting'",
                                (stats["source_sha256"], stats["source_bytes"], stats["csv_sha256"], stats["csv_bytes"],
                                 stats["records"], time.time(), request_id)).rowcount
        if changed != 1:
            raise ExportDenied("export_completion_state_invalid")

    def mark(self, request_id, state, reason):
        with self.store.transaction() as c:
            c.execute("UPDATE query_exports_v1 SET state=?,reason=?,updated=? WHERE request_id=?",
                      (state, reason, time.time(), request_id))

    def reconcile(self):
        """After a restart nothing is published anew; only already-published artifacts are classified."""
        with self.store.transaction() as c:
            rows = [dict(r) for r in c.execute(
                "SELECT * FROM query_exports_v1 WHERE state IN (%s)" % ",".join("?" * len(OPEN_STATES)), OPEN_STATES)]
        if not rows:
            return
        _private_root(self.root, create=False)
        for row in rows:
            final, staging = Path(row["final"]), Path(row["staging"])
            if os.path.lexists(final):
                verified = row["state"] != "exporting" and self._verify(final, row)
                self.mark(row["request_id"], "exported" if verified else "export_unknown",
                          "reconciled" if verified else "published_contents_unverified")
                continue
            try:
                _remove_owned_dir(staging)
                reason = "gateway_restarted"
            except ExportDenied:
                reason = "gateway_restarted_staging_untrusted"
            self.mark(row["request_id"], "not_published" if row["state"] != "exporting" else "failed", reason)

    @staticmethod
    def _verify(final, row):
        try:
            info = os.lstat(final)
            names = sorted(os.listdir(final))
            if not _stat.S_ISDIR(info.st_mode) or names != ["data.csv", "manifest.json"]:
                return False
            for name in names:
                if not _stat.S_ISREG(os.lstat(final / name).st_mode):
                    return False
            manifest = json.loads((final / "manifest.json").read_text(encoding="utf-8"))
            return (manifest.get("spec_digest") == row["spec_digest"] == spec_digest(manifest.get("spec", {}))
                    and manifest.get("csv_sha256") == row["csv_sha256"] == _sha256_file(final / "data.csv")
                    and manifest.get("request_id") == row["request_id"])
        except (OSError, ValueError):
            return False


class ExportSession:
    """One approved export: private staging -> completion -> no-replace publication."""

    def __init__(self, ledger, export_spec, *, request_id, run_id, owner, epoch):
        self.ledger = ledger
        self.spec = export_spec["spec"] if "spec" in export_spec else export_spec
        self.digest = spec_digest(self.spec)
        self.request_id, self.run_id, self.owner, self.epoch = request_id, run_id, owner, epoch
        self.root = ledger.root
        self.final = self.root / request_id
        if Path(self.spec.get("artifact_directory", "")) != self.final:
            raise ExportDenied("export_directory_mismatch")
        self.staging = self.root / (".staging-" + request_id)
        self.file = None
        self.codec = None
        self.stats = None

    def open(self):
        _private_root(self.root, create=True)
        self.ledger.intent(self.request_id, self.owner, self.run_id, self.epoch, self.digest, self.final, self.staging)
        try:
            os.mkdir(self.staging, 0o700)
        except FileExistsError:
            self.ledger.mark(self.request_id, "failed", "export_staging_exists")
            raise ExportDenied("export_staging_exists") from None
        fd = os.open(str(self.staging / "data.csv"),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        self.file = os.fdopen(fd, "wb")
        self.codec = CsvExport(self.spec, self.file)
        return self

    def feed(self, chunk):
        self.codec.feed(chunk)

    def finish(self):
        stats = self.codec.finish()
        self.file.flush()
        os.fsync(self.file.fileno())
        self.file.close()
        self.file = None
        self.stats = stats
        return stats

    def commit_completion(self):
        if self.stats is None:
            raise ExportDenied("export_incomplete")
        self.ledger.complete(self.request_id, self.stats)

    def write_manifest(self):
        if self.stats is None:
            raise ExportDenied("export_incomplete")
        path = self.staging / "manifest.json"
        if os.path.lexists(path):
            return
        manifest = dict(format=FORMAT, spec=self.spec, spec_digest=self.digest, request_id=self.request_id,
                        run_id=self.run_id, owner=self.owner, epoch=self.epoch,
                        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), **self.stats)
        data = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_dir(self.staging)

    def publish(self, gate):
        row = self.ledger.status(self.request_id)
        if self.stats is None or row is None or row["state"] != "complete":
            raise ExportDenied("export_incomplete")
        self.write_manifest()
        if not gate():
            return self._discard("stopped_before_publish")
        if os.path.lexists(self.final):
            return self._discard("destination_exists")
        try:
            rename_no_replace(self.staging, self.final)
        except FileExistsError:
            return self._discard("destination_exists")
        except OSError:
            self.ledger.mark(self.request_id, "export_unknown", "publish_rename_failed")
            return self.ledger.status(self.request_id)
        try:
            _fsync_dir(self.root)
            self.ledger.mark(self.request_id, "exported", None)
        except Exception:
            try:
                self.ledger.mark(self.request_id, "export_unknown", "publish_state_unrecorded")
            except Exception:
                pass
        return self.ledger.status(self.request_id)

    def abort(self, reason):
        if self.file is not None:
            try:
                self.file.close()
            except OSError:
                pass
            self.file = None
        row = self.ledger.status(self.request_id)
        try:
            _remove_owned_dir(self.staging)
        except ExportDenied:
            reason = reason + "_staging_untrusted"
        if row is not None and row["state"] in ("exporting", "complete"):
            self.ledger.mark(self.request_id, "failed", reason)

    def _discard(self, reason):
        _remove_owned_dir(self.staging)
        self.ledger.mark(self.request_id, "not_published", reason)
        return self.ledger.status(self.request_id)
