"""Synthetic process tests for the independent production watchdog."""

from pathlib import Path
import fcntl
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_prod_watchdog import (  # noqa: E402
    OwnedProcessWatchdog,
    StopMarkerError,
    create_stop_marker,
    cancel_markers_only,
    list_stop_markers,
    remove_stop_markers,
    stop_latched,
)


class WatchdogTests(unittest.TestCase):
    def test_cancel_kind_is_atomic_even_before_body_write_and_owned(self):
        with tempfile.TemporaryDirectory() as directory:
            markers = Path(directory) / "stop.d"
            self.assertTrue(cancel_markers_only(markers))
            name = create_stop_marker(markers, reason="operator_cancel")
            self.assertTrue(cancel_markers_only(markers, (name,)))
            marker = markers / name
            for content in (b"", b"operator_can", b"operator_cancel"):
                marker.write_bytes(content)
                self.assertTrue(cancel_markers_only(markers))
            marker.write_bytes(b"operator_cancel")
            marker.chmod(0o644)
            self.assertFalse(cancel_markers_only(markers))
            marker.chmod(0o600)
            marker.unlink()
            target = Path(directory) / "target"
            target.write_text("operator_cancel")
            marker.symlink_to(target)
            self.assertFalse(cancel_markers_only(markers))
            marker.unlink()
            create_stop_marker(markers, reason="independent_emergency_stop")
            self.assertFalse(cancel_markers_only(markers))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.latch = Path(self.directory.name) / "stop.latch"
        self.children = []

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except OSError:
                    child.kill()
                child.wait(timeout=2)
        self.directory.cleanup()

    def child(self):
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.children.append(child)
        return child

    @staticmethod
    def wait_for_exit(child, timeout=3):
        deadline = time.monotonic() + timeout
        while child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        return child.poll() is not None

    def make_watchdog(self, child, **kwargs):
        return OwnedProcessWatchdog(
            child.pid,
            parent_pid=os.getpid(),
            heartbeat_interval=0.05,
            heartbeat_timeout=0.3,
            kill_grace=0.1,
            stop_latch=self.latch,
            **kwargs,
        ).start()

    def test_unique_stop_marker_does_not_wait_for_gateway_lock(self):
        markers = Path(self.directory.name) / "stop.d"
        lock_path = Path(self.directory.name) / "stop.lock"
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            marker = create_stop_marker(markers, reason="independent_emergency_stop")
            self.assertTrue(marker.startswith("stop-"))
            self.assertTrue(stop_latched(markers))
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def test_resume_marker_removal_rejects_new_unconfirmed_marker(self):
        markers = Path(self.directory.name) / "stop.d"
        first = create_stop_marker(markers)
        second = create_stop_marker(markers)
        with self.assertRaises(StopMarkerError):
            remove_stop_markers(markers, [first])
        self.assertEqual(list_stop_markers(markers), tuple(sorted((first, second))))
        remove_stop_markers(markers, [first, second])
        self.assertFalse(stop_latched(markers))

    def test_heartbeat_keeps_owned_worker_alive_and_latch_fences_it(self):
        child = self.child()
        watchdog = self.make_watchdog(child)
        try:
            time.sleep(0.55)
            self.assertIsNone(child.poll())
            self.latch.touch()
            self.assertTrue(self.wait_for_exit(child))
        finally:
            watchdog.close()

    def test_heartbeat_pause_fences_worker_after_timeout(self):
        child = self.child()
        watchdog = self.make_watchdog(child)
        try:
            watchdog.pause_heartbeat()
            self.assertTrue(self.wait_for_exit(child))
        finally:
            watchdog.close()

    def test_eof_fences_worker_without_gateway_response(self):
        child = self.child()
        watchdog = self.make_watchdog(child)
        watchdog.close()
        self.assertTrue(self.wait_for_exit(child))

    def test_parent_death_fences_worker(self):
        child = self.child()
        parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        self.children.append(parent)
        watchdog = OwnedProcessWatchdog(
            child.pid,
            parent_pid=parent.pid,
            heartbeat_interval=0.05,
            heartbeat_timeout=2,
            kill_grace=0.1,
            stop_latch=self.latch,
        ).start()
        try:
            parent.kill()
            parent.wait(timeout=2)
            self.assertTrue(self.wait_for_exit(child))
        finally:
            watchdog.close()


if __name__ == "__main__":
    unittest.main()

