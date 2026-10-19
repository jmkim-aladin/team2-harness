"""Bounded, allowlisted diagnostics. Raw driver text never leaves this object.

Driver errors can contain passwords, SQL, results, or server-authored messages.
Redaction alone is insufficient: exported messages are fixed strings, and only
known error numbers are extracted. Classification is evidence, not a diagnosis.
"""
import errno
import re
import subprocess
import threading


CAPTURE_BYTES = 8192
STAGES = frozenset(("startup", "query", "observer", "credentials", "journal"))
SAFE_CODES = frozenset("""
environment_failed process_start_failed watchdog_start_failed worker_stdin_unavailable
startup_write_failed startup_failed startup_timeout query_write_failed
worker_output_invalid worker_output_failed worker_output_unconfirmed worker_error_output output_rows_exceeded
output_bytes_exceeded resource_limit observer_not_ready observer_timeout_invalid
observer_stdin_unavailable observer_failed observer_permission_denied
observer_sessions_remaining observer_result_invalid worker_exit_failed
keychain_interaction_required keychain_access_cancelled keychain_item_not_found
keychain_path_invalid keychain_value_invalid keychain_status_-25293
service_keychain_unavailable profile_changed_new_approval_required
gateway_identity_unavailable recovery_journal_publish_failed
worker_identity_unavailable worker_journal_update_failed watchdog_close_failed
""".split())
# Only fixed labels/messages are exported, never regex captures from raw text.
SIGNATURES = (
    ("tls_certificate", "TLS certificate validation failed.", r"x509:|certificate verify failed|certificate signed by unknown authority|certificate chain was issued by an authority that is not trusted"),
    ("login_failed", "SQL Server rejected the login.", r"login failed for user|\bMsg 18456\b"),
    ("database_unavailable", "The requested database could not be opened.", r"cannot open database|\bMsg 4060\b"),
    ("permission_denied", "SQL Server denied permission.", r"permission was denied|\bMsg (?:229|297|300)\b"),
    ("timeout", "The client reported a connection or query timeout.", r"timeout expired|i/o timeout|context deadline exceeded|login timeout|query timeout"),
    ("connection_refused", "The network connection was refused.", r"connection refused|actively refused"),
    ("dns_failed", "The server name could not be resolved.", r"no such host|name or service not known|nodename nor servname"),
    ("unsupported_option", "sqlcmd rejected a command-line option.", r"unknown flag|unknown shorthand flag|unrecognized option|unknown option"),
)
KNOWN_SQL_CODES = (18456, 4060, 229, 297, 300, 1205, 1222)


class Diagnostics:
    def __init__(self):
        self._lock = threading.Lock()
        self._buffers = {}
        self._truncated = set()
        self._errors = {}
        self._exit_codes = {}

    def capture(self, stage, source, chunk):
        if stage not in STAGES or source not in ("stdout", "stderr"):
            return
        if not isinstance(chunk, (bytes, bytearray, str)):
            return
        # Slice before encoding to keep temporary allocations bounded as well.
        if isinstance(chunk, str):
            clipped = len(chunk) > CAPTURE_BYTES
            chunk = chunk[:CAPTURE_BYTES].encode("utf-8", "replace")
        else:
            clipped = False
        key = (stage, source)
        with self._lock:
            buffer = self._buffers.setdefault(key, bytearray())
            remaining = CAPTURE_BYTES - sum(len(value) for (phase, _), value in self._buffers.items()
                                            if phase == stage)
            buffer.extend(chunk[:remaining])
            if clipped or len(chunk) > remaining:
                self._truncated.add(key)

    def failure(self, stage, error=None, *, code=None):
        if stage not in STAGES:
            return
        # Callers pass known exception tokens; arbitrary exception strings are
        # never rendered, even if they look like SQL/driver error text.
        token = code if code is not None else (
            error.args[0] if isinstance(error, Exception) and error.args else None)
        item = {"code": token if isinstance(token, str) and token in SAFE_CODES else "internal_error"}
        if isinstance(error, subprocess.TimeoutExpired):
            item = {"code": "process_timeout"}
        elif isinstance(error, OSError) and type(error.errno) is int and error.errno in errno.errorcode:
            item.update(errno=error.errno, os_code=errno.errorcode[error.errno])
        with self._lock:
            # Keep the first error; cleanup exceptions must not overwrite it.
            self._errors.setdefault(stage, item)

    def exit_code(self, stage, value):
        if stage in STAGES and type(value) is int and -255 <= value <= 255:
            with self._lock:
                self._exit_codes[stage] = value

    def snapshot(self):
        result = []
        with self._lock:
            for stage in ("journal", "credentials", "startup", "query", "observer"):
                sources = {}
                for (phase, source), buffer in self._buffers.items():
                    if phase != stage or (not buffer and (phase, source) not in self._truncated):
                        continue
                    raw = bytes(buffer).decode("utf-8", "replace")
                    # The fixed successful handshake is not an error source.
                    if (stage == "startup" and source == "stdout"
                            and raw.strip() == "SQLCMD_READY"
                            and (phase, source) not in self._truncated):
                        continue
                    matches = [{"category": name, "message": message}
                               for name, message, pattern in SIGNATURES
                               if re.search(pattern, raw, re.IGNORECASE)]
                    numbers = [n for n in KNOWN_SQL_CODES
                               if re.search(r"\bMsg\s+" + str(n) + r"\b", raw, re.IGNORECASE)]
                    sources[source] = dict(signatures=matches, sql_error_numbers=numbers,
                                           truncated=(phase, source) in self._truncated,
                                           raw_message_withheld=True)
                if stage not in self._errors and not sources and not self._exit_codes.get(stage):
                    continue
                item = dict(stage=stage, **self._errors.get(stage, {}))
                if stage in self._exit_codes:
                    item["exit_code"] = self._exit_codes[stage]
                if sources:
                    item["sources"] = sources
                result.append(item)
        return result
