#!/usr/bin/env python3
"""Independent watchdog for an owned production sqlcmd process group.

The gateway process creates :class:`OwnedProcessWatchdog` after spawning an
owned, new-session worker.  A heartbeat writer stays in the gateway process;
the watchdog is a separate process with only the heartbeat read end.  A
gateway crash, SIGSTOP, or heartbeat EOF therefore causes the watchdog to
interrupt and then kill the worker process group.  It never sends SQL or a
SQL Server KILL command.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import secrets
import select
import signal
import stat
import subprocess
import sys
import threading
import time
from typing import Iterable, Optional


DEFAULT_HEARTBEAT_INTERVAL = 0.5
DEFAULT_HEARTBEAT_TIMEOUT = 2.0
DEFAULT_KILL_GRACE = 1.0
# The current-user gateway and its independent stop client share this marker
# directory.  Creating a unique marker is deliberately lock-free: an operator
# can still stop the worker while the gateway is SIGSTOP'ed holding a lock.
DEFAULT_STOP_MARKERS = Path.home() / "Library/Application Support/team2-db/stop.d"
# Keep the public name used by the transport and older callers.  The value is
# now a directory; ``stop_latched`` still accepts a legacy regular-file path in
# tests and during a user-scoped migration.
DEFAULT_STOP_LATCH = DEFAULT_STOP_MARKERS
STOP_MARKER_RE = re.compile(r"^stop-[0-9a-f]{32}(?:-cancel)?\.marker$")
CANCEL_MARKER_RE = re.compile(r"^stop-[0-9a-f]{32}-cancel\.marker$")


class StopMarkerError(RuntimeError):
    """The independent stop marker path cannot be trusted or updated."""


def _marker_directory(path: Path, *, create: bool = False) -> Path:
    path = Path(path)
    if not path.is_absolute() or "\x00" in str(path):
        raise StopMarkerError("stop_marker_path_invalid")
    try:
        info = path.lstat()
    except FileNotFoundError:
        if not create:
            return path
        try:
            path.mkdir(mode=0o700)
            info = path.lstat()
        except FileExistsError:
            info = path.lstat()
        except OSError:
            raise StopMarkerError("stop_marker_directory_unavailable") from None
    except OSError:
        raise StopMarkerError("stop_marker_directory_unavailable") from None
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise StopMarkerError("stop_marker_directory_untrusted")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise StopMarkerError("stop_marker_directory_permissions")
    return path


def list_stop_markers(path: Optional[Path] = DEFAULT_STOP_MARKERS) -> tuple[str, ...]:
    """Return immutable marker names, with legacy-file compatibility."""

    if path is None:
        return ()
    path = Path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ()
    except OSError:
        raise StopMarkerError("stop_marker_read_failed") from None
    if path.is_symlink():
        raise StopMarkerError("stop_marker_untrusted")
    if stat.S_ISREG(info.st_mode):
        return (path.name,)
    if not stat.S_ISDIR(info.st_mode):
        raise StopMarkerError("stop_marker_untrusted")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise StopMarkerError("stop_marker_directory_permissions")
    try:
        names = sorted(entry.name for entry in path.iterdir())
    except OSError:
        raise StopMarkerError("stop_marker_read_failed") from None
    # Unexpected entries are still stop signals; exposing a bounded name list
    # prevents a damaged directory from turning status into an unbounded reply.
    if len(names) > 256:
        raise StopMarkerError("stop_marker_directory_overfull")
    return tuple(names)


def _fsync_parent(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_stop_marker(path: Path = DEFAULT_STOP_MARKERS, *, reason: str = "operator_stop") -> str:
    """Persist one unique stop marker before touching coordinator state."""

    path = Path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        info = None
    except OSError:
        raise StopMarkerError("stop_marker_unavailable") from None
    # A regular file is the pre-marker compatibility form.  Its existence is
    # already the immutable stop generation, so do not truncate or replace it.
    if info is not None:
        if path.is_symlink():
            raise StopMarkerError("stop_marker_untrusted")
        if stat.S_ISREG(info.st_mode):
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise StopMarkerError("stop_marker_permissions")
            return path.name
    directory = _marker_directory(path, create=True)
    for _ in range(8):
        # The kind is visible atomically with O_EXCL creation. Readers can
        # classify cancellation even before the diagnostic body is written.
        suffix = "-cancel" if reason == "operator_cancel" else ""
        name = f"stop-{secrets.token_hex(16)}{suffix}.marker"
        marker = directory / name
        try:
            descriptor = os.open(
                marker,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
        except FileExistsError:
            continue
        try:
            # The body is intentionally generic; the nonce in the filename is
            # the operator-visible generation and contains no SQL or secret.
            payload = (reason if isinstance(reason, str) and reason else "operator_stop").encode("utf-8")
            payload = payload[:128]
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _fsync_parent(directory)
        return name
    raise StopMarkerError("stop_marker_collision")


def cancel_markers_only(path: Path, expected=None) -> bool:
    """Recognize owned soft-cancel names atomically; unknown kinds stay halted."""
    path = Path(path)
    try:
        names = list_stop_markers(path)
        if expected is not None and names != tuple(expected):
            return False
        if not names:
            return True
        if not path.is_dir() or path.is_symlink():
            return False
        for name in names:
            if not CANCEL_MARKER_RE.fullmatch(name):
                return False
            descriptor = os.open(path / name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                                 | getattr(os, "O_NONBLOCK", 0))
            try:
                info = os.fstat(descriptor)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or stat.S_IMODE(info.st_mode) & 0o077):
                    return False
            finally:
                os.close(descriptor)
        return list_stop_markers(path) == names
    except (OSError, StopMarkerError):
        return False


def remove_stop_markers(path: Path, expected: Iterable[str]) -> None:
    """Remove exactly the names confirmed by the operator."""

    names = tuple(expected)
    if (len(set(names)) != len(names) or any(
        not isinstance(name, str) or not name or "/" in name or "\x00" in name
        or any(ord(char) < 32 for char in name) for name in names
    )):
        raise StopMarkerError("stop_marker_confirmation_invalid")
    path = Path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        if names:
            raise StopMarkerError("stop_marker_changed") from None
        return
    except OSError:
        raise StopMarkerError("stop_marker_read_failed") from None
    if path.is_symlink():
        raise StopMarkerError("stop_marker_untrusted")
    if stat.S_ISREG(info.st_mode):
        if names != (path.name,):
            raise StopMarkerError("stop_marker_changed")
        try:
            path.unlink()
            _fsync_parent(path.parent)
        except OSError:
            raise StopMarkerError("stop_marker_remove_failed") from None
        return
    directory = _marker_directory(path)
    if any(not STOP_MARKER_RE.fullmatch(name) for name in names):
        raise StopMarkerError("stop_marker_confirmation_invalid")
    current = list_stop_markers(directory)
    if current != tuple(sorted(names)):
        raise StopMarkerError("stop_marker_changed")
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        for name in names:
            try:
                os.unlink(name, dir_fd=descriptor)
            except FileNotFoundError:
                raise StopMarkerError("stop_marker_changed") from None
            except OSError:
                raise StopMarkerError("stop_marker_remove_failed") from None
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def stop_latched(path: Optional[Path] = DEFAULT_STOP_LATCH) -> bool:
    """Return the emergency-stop marker state without mutating it."""

    if path is None:
        return False
    try:
        return bool(list_stop_markers(path))
    except StopMarkerError:
        # An unreadable marker path is fail-closed for an emergency path.
        return True


def _positive(value: float, name: str) -> float:
    value = float(value)
    if value <= 0:
        raise ValueError(f"{name}_invalid")
    return value


def process_fingerprint(pid: int) -> Optional[str]:
    """Return a birth identity for a live process, or ``None``.

    Linux exposes a monotonic start tick in ``/proc/<pid>/stat``.  macOS does
    not expose that file, so the current-user runtime uses ``ps lstart`` as
    the platform fallback.  The watchdog refuses to fence a PID whose identity
    cannot be observed or no longer matches the identity captured at spawn.
    """

    if type(pid) is not int or pid <= 1:
        return None
    stat_path = Path(f"/proc/{pid}/stat")
    try:
        raw = stat_path.read_text()
        _, tail = raw.rsplit(")", 1)
        fields = tail.split()
        # tail begins with state (original field 3); starttime is field 22.
        return f"proc:{pid}:{fields[19]}"
    except (OSError, IndexError, ValueError):
        pass
    try:
        result = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "lstart="],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1,
            check=False,
        )
        value = result.stdout.strip()
        if result.returncode == 0 and value:
            return f"ps:{pid}:{value}"
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _group_alive(target_pgid: int) -> bool:
    try:
        # Workers are required to use start_new_session=True.  Refuse to act
        # on a pid that has been reused as a member of another process group.
        return os.getpgid(target_pgid) == target_pgid
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _target_matches(target_pgid: int, target_fingerprint: Optional[str]) -> bool:
    return bool(
        target_fingerprint
        and _group_alive(target_pgid)
        and process_fingerprint(target_pgid) == target_fingerprint
    )


def _signal_owned_group(target_pgid: int, sig: int, target_fingerprint: Optional[str]) -> None:
    if not _target_matches(target_pgid, target_fingerprint):
        return
    try:
        os.killpg(target_pgid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        return


def terminate_owned_group(
    target_pgid: int,
    grace: float = DEFAULT_KILL_GRACE,
    target_fingerprint: Optional[str] = None,
) -> None:
    """Interrupt then force-kill a verified process group, bounded in time."""

    grace = _positive(grace, "grace")
    if not _target_matches(target_pgid, target_fingerprint):
        return
    _signal_owned_group(
        target_pgid,
        getattr(signal, "SIGINT", signal.SIGTERM),
        target_fingerprint,
    )
    deadline = time.monotonic() + grace
    while _target_matches(target_pgid, target_fingerprint) and time.monotonic() < deadline:
        time.sleep(0.01)
    if _target_matches(target_pgid, target_fingerprint):
        _signal_owned_group(
            target_pgid,
            getattr(signal, "SIGKILL", signal.SIGTERM),
            target_fingerprint,
        )


def watch(
    target_pgid: int,
    parent_pid: int,
    heartbeat_fd: int,
    *,
    timeout: float = DEFAULT_HEARTBEAT_TIMEOUT,
    grace: float = DEFAULT_KILL_GRACE,
    stop_latch: Optional[Path] = DEFAULT_STOP_LATCH,
    target_fingerprint: Optional[str] = None,
) -> int:
    """Run in the independent process and return after fencing the worker."""

    if type(target_pgid) is not int or target_pgid <= 1:
        return 2
    if type(parent_pid) is not int or parent_pid <= 1:
        return 2
    if not target_fingerprint or process_fingerprint(target_pgid) != target_fingerprint:
        return 2
    timeout = _positive(timeout, "timeout")
    grace = _positive(grace, "grace")
    stop_latch = Path(stop_latch) if stop_latch else None
    try:
        os.set_blocking(heartbeat_fd, False)
    except (AttributeError, OSError):
        pass

    last_heartbeat = time.monotonic()
    reason = ""
    try:
        while True:
            # A dead/replaced parent is a fence even if the pipe has not yet
            # delivered EOF.  kill(pid, 0) performs no mutation.
            try:
                os.kill(parent_pid, 0)
            except (ProcessLookupError, PermissionError, OSError):
                reason = "parent_gone"
                break
            if not _target_matches(target_pgid, target_fingerprint):
                return 0
            if stop_latch is not None:
                if stop_latched(stop_latch):
                    reason = "stop_latch"
                    break
            now = time.monotonic()
            remaining = timeout - (now - last_heartbeat)
            if remaining <= 0:
                reason = "heartbeat_timeout"
                break
            try:
                readable, _, _ = select.select([heartbeat_fd], [], [], min(remaining, 0.1))
            except (OSError, ValueError):
                reason = "heartbeat_error"
                break
            if not readable:
                continue
            try:
                data = os.read(heartbeat_fd, 4096)
            except BlockingIOError:
                continue
            except OSError:
                reason = "heartbeat_error"
                break
            if not data:
                reason = "heartbeat_eof"
                break
            last_heartbeat = time.monotonic()
    finally:
        try:
            os.close(heartbeat_fd)
        except OSError:
            pass
    # ``reason`` is intentionally not printed: watchdog stdout/stderr are
    # redirected by the lease and no credential/query data belongs here.
    if reason:
        terminate_owned_group(target_pgid, grace, target_fingerprint)
    return 0


class OwnedProcessWatchdog:
    """Own the gateway-side heartbeat and independent watchdog process."""

    def __init__(
        self,
        target_pid: int,
        *,
        parent_pid: Optional[int] = None,
        target_fingerprint: Optional[str] = None,
        script: Optional[Path] = None,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        heartbeat_timeout: float = DEFAULT_HEARTBEAT_TIMEOUT,
        kill_grace: float = DEFAULT_KILL_GRACE,
        stop_latch: Optional[Path] = DEFAULT_STOP_LATCH,
        popen_factory=subprocess.Popen,
    ):
        if type(target_pid) is not int or target_pid <= 1:
            raise ValueError("target_pid_invalid")
        self.target_pid = target_pid
        self.parent_pid = os.getpid() if parent_pid is None else parent_pid
        if type(self.parent_pid) is not int or self.parent_pid <= 1:
            raise ValueError("parent_pid_invalid")
        self.target_fingerprint = target_fingerprint or process_fingerprint(target_pid)
        if not self.target_fingerprint:
            # A watcher without a birth identity could kill a later, unrelated
            # process after PID reuse.  Fail closed before creating the child.
            raise ValueError("target_identity_unavailable")
        self.script = Path(script or __file__).resolve()
        self.heartbeat_interval = _positive(heartbeat_interval, "heartbeat_interval")
        self.heartbeat_timeout = _positive(heartbeat_timeout, "heartbeat_timeout")
        self.kill_grace = _positive(kill_grace, "kill_grace")
        self.stop_latch = Path(stop_latch) if stop_latch else None
        self.popen_factory = popen_factory
        self.process = None
        self._read_fd: Optional[int] = None
        self._write_fd: Optional[int] = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> "OwnedProcessWatchdog":
        with self._lock:
            if self.process is not None:
                raise RuntimeError("watchdog_already_started")
            read_fd, write_fd = os.pipe()
            os.set_inheritable(read_fd, True)
            argv = [
                sys.executable,
                str(self.script),
                "--watch",
                str(self.target_pid),
                str(self.parent_pid),
                str(read_fd),
                str(self.heartbeat_timeout),
                str(self.kill_grace),
                self.target_fingerprint,
                str(self.stop_latch) if self.stop_latch is not None else "",
            ]
            try:
                process = self.popen_factory(
                    argv,
                    pass_fds=(read_fd,),
                    close_fds=True,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                os.close(read_fd)
                os.close(write_fd)
                raise RuntimeError("watchdog_start_failed") from None
            self._read_fd = read_fd
            self._write_fd = write_fd
            self.process = process
            os.close(read_fd)
            self._read_fd = None
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="team2-db-heartbeat",
            )
            self._heartbeat_thread.start()
            return self

    def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            if not self._pause.is_set():
                try:
                    if self._write_fd is None:
                        return
                    os.write(self._write_fd, b"\x01")
                except (BrokenPipeError, OSError):
                    return
            self._stop.wait(self.heartbeat_interval)

    def pause_heartbeat(self) -> None:
        self._pause.set()

    def resume_heartbeat(self) -> None:
        self._pause.clear()

    def close(self, *, wait_timeout: Optional[float] = None) -> None:
        """Close heartbeat; EOF intentionally fences a still-live worker."""

        with self._lock:
            if self.process is None:
                return
            self._stop.set()
            write_fd, self._write_fd = self._write_fd, None
            process = self.process
        if write_fd is not None:
            try:
                os.close(write_fd)
            except OSError:
                pass
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=1)
        if wait_timeout is None:
            wait_timeout = self.heartbeat_timeout + self.kill_grace + 1
        try:
            process.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired:
            try:
                process.terminate()
                process.wait(timeout=1)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    def __enter__(self) -> "OwnedProcessWatchdog":
        return self.start()

    def __exit__(self, *_args: object) -> None:
        self.close()


def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--watch",
        nargs=7,
        metavar=(
            "TARGET_PGID",
            "PARENT_PID",
            "HEARTBEAT_FD",
            "TIMEOUT",
            "GRACE",
            "TARGET_FINGERPRINT",
            "STOP_LATCH",
        ),
    )
    args = parser.parse_args(argv)
    if args.watch is None:
        return 2
    target, parent, fd, timeout, grace, fingerprint, stop_latch = args.watch
    try:
        return watch(
            int(target),
            int(parent),
            int(fd),
            timeout=float(timeout),
            grace=float(grace),
            target_fingerprint=fingerprint,
            stop_latch=stop_latch or None,
        )
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())

