"""CSV mode routes approved query stdout to a bounded sink instead of memory (Q3b slice 2)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_prod_transport import TransportError  # noqa: E402
from test_db_prod_transport import backend  # noqa: E402


class Sink:
    def __init__(self, fail_after=None):
        self.chunks, self.fail_after = [], fail_after

    def feed(self, chunk):
        if self.fail_after is not None and len(self.chunks) >= self.fail_after:
            raise ValueError("frame_invalid")
        self.chunks.append(bytes(chunk))


def collecting(sink, max_bytes=None):
    worker, _ = backend()
    worker.attach_stream_sink(sink)
    worker._ready.set()
    worker._query_collecting = True
    worker._max_bytes = max_bytes
    return worker


class StreamTests(unittest.TestCase):
    def test_stdout_goes_to_sink_not_memory(self):
        sink = Sink()
        worker = collecting(sink)
        worker._record_stdout(b"L4" + b" " * 10 + b"\n")
        worker._record_stdout(b"H5B005D00\n")
        self.assertEqual(b"".join(sink.chunks), b"L4" + b" " * 10 + b"\nH5B005D00\n")
        self.assertEqual(bytes(worker._result), b"")
        self.assertIsNone(worker.failure_reason)

    def test_startup_output_never_reaches_sink(self):
        sink = Sink()
        worker, _ = backend()
        worker.attach_stream_sink(sink)
        worker._record_stdout(b"SQLCMD_READY\n")
        self.assertEqual(sink.chunks, [])

    def test_source_byte_cap_fails_closed_and_stops_feeding(self):
        sink = Sink()
        worker = collecting(sink, max_bytes=8)
        worker._record_stdout(b"12345")
        worker._record_stdout(b"6789")
        self.assertEqual(worker.failure_reason, "output_bytes_exceeded")
        worker._record_stdout(b"more")
        self.assertEqual(b"".join(sink.chunks), b"12345")

    def test_sink_rejection_fails_the_query(self):
        sink = Sink(fail_after=1)
        worker = collecting(sink)
        worker._record_stdout(b"L4\n")
        worker._record_stdout(b"Hzz\n")
        self.assertEqual(worker.failure_reason, "export_stream_rejected")
        self.assertEqual(worker.stream_failure, "frame_invalid")
        worker._record_stdout(b"H00\n")
        self.assertEqual(len(sink.chunks), 1)

    def test_sink_must_be_attached_before_dispatch(self):
        worker, _ = backend()
        worker._dispatch_started = True
        with self.assertRaises(TransportError):
            worker.attach_stream_sink(Sink())


if __name__ == "__main__":
    unittest.main()
