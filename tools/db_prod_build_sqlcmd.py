#!/usr/bin/env python3
"""Build the reviewed DataGrip-labelled Go sqlcmd binary in a temp staging dir.

The production transport uses the Homebrew Go sqlcmd binary.  Go sqlcmd 1.10.0
hard-codes ``ApplicationName`` to ``sqlcmd``; this builder makes the one-line
source change needed for ``sys.dm_exec_sessions.program_name`` to show
``DataGrip`` while keeping the rest of the CLI and transport unchanged.

This script deliberately has no database, Keychain, or SQL path.  It fetches a
tag reference and source archive only from the official Microsoft GitHub
repository, applies one exact source-line replacement, and builds into a
private temporary staging directory through one uniquely named Docker
container.  It never installs over Homebrew's binary.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Dict, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


REPOSITORY = "microsoft/go-sqlcmd"
TAG = "v1.10.0"
SOURCE_FILE = Path("cmd/sqlcmd/sqlcmd.go")
OLD_APPLICATION_LINE = 'connect.ApplicationName = "sqlcmd"'
NEW_APPLICATION_LINE = 'connect.ApplicationName = "DataGrip"'
GO_VERSION = "1.25.7"
DEFAULT_DOCKER_IMAGE = "golang:1.25.7-bookworm"
API_URL = "https://api.github.com/repos/microsoft/go-sqlcmd/git/ref/tags/v1.10.0"
ARCHIVE_URL_TEMPLATE = "https://codeload.github.com/microsoft/go-sqlcmd/tar.gz/{commit}"
ALLOWED_SOURCE_HOSTS = {"api.github.com", "codeload.github.com"}
MAX_API_BYTES = 1 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_EXTRACTED_BYTES = 768 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:-]*$")


class BuildError(RuntimeError):
    """An expected build/provenance failure safe to show to the operator."""


def _json_dump(path: Path, value: Any) -> None:
    """Write JSON atomically, keeping an incomplete provenance file out."""

    temporary = path.with_name(path.name + ".part")
    data = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _validate_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_SOURCE_HOSTS:
        raise BuildError("source_url_not_allowlisted")
    if parsed.username or parsed.password or parsed.port:
        raise BuildError("source_url_credentials_or_port_rejected")


def _download(url: str, destination: Path, max_bytes: int) -> Dict[str, Any]:
    """Download one official file without ever exposing a partial final file."""

    _validate_source_url(url)
    temporary = destination.with_name(destination.name + ".part")
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "team2-db-prod-sqlcmd-builder/1",
        },
    )
    total = 0
    try:
        with urlopen(request, timeout=30) as response:
            final_url = response.geturl()
            _validate_source_url(final_url)
            with temporary.open("wb") as handle:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise BuildError("source_download_too_large")
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(str(temporary), str(destination))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise BuildError("source_download_failed") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return {"url": url, "final_url": final_url, "bytes": total, "sha256": _sha256(destination)}


def _resolve_commit() -> Tuple[str, Dict[str, Any]]:
    metadata_fd, metadata_name = tempfile.mkstemp(prefix="team2-sqlcmd-ref-", suffix=".json", dir="/tmp")
    os.close(metadata_fd)
    metadata_path = Path(metadata_name)
    try:
        download = _download(API_URL, metadata_path, MAX_API_BYTES)
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise BuildError("source_ref_invalid_json") from exc
    finally:
        try:
            metadata_path.unlink()
        except FileNotFoundError:
            pass
    if payload.get("ref") != "refs/tags/" + TAG:
        raise BuildError("source_tag_mismatch")
    obj = payload.get("object")
    if not isinstance(obj, dict) or obj.get("type") != "commit":
        raise BuildError("source_tag_not_commit")
    commit = obj.get("sha")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise BuildError("source_commit_invalid")
    metadata = {
        "ref_url": API_URL,
        "ref_sha256": download["sha256"],
        "ref_bytes": download["bytes"],
        "ref": payload["ref"],
        "commit": commit,
    }
    return commit, metadata


def _safe_member_path(name: str, root_name: str) -> Path:
    """Return a safe relative archive path, rejecting traversal and escapes."""

    if "\\" in name:
        raise BuildError("source_archive_backslash_path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise BuildError("source_archive_path_traversal")
    if path.parts[0] != root_name:
        raise BuildError("source_archive_multiple_roots")
    return Path(*path.parts)


def _extract_archive(archive: Path, destination: Path, commit: str) -> Path:
    """Extract only regular files/directories from the pinned GitHub archive."""

    root_name: Optional[str] = None
    extracted_bytes = 0
    try:
        with tarfile.open(str(archive), mode="r:gz") as bundle:
            members = bundle.getmembers()
            if not members:
                raise BuildError("source_archive_empty")
            first_parts = PurePosixPath(members[0].name).parts
            if len(first_parts) < 1:
                raise BuildError("source_archive_root_missing")
            root_name = first_parts[0]
            if not re.fullmatch(r"go-sqlcmd-[0-9a-f]{40}", root_name):
                raise BuildError("source_archive_root_mismatch")
            if root_name != "go-sqlcmd-" + commit:
                raise BuildError("source_archive_commit_mismatch")
            source_root = destination / root_name
            source_root.mkdir(parents=True, exist_ok=False)
            for member in members:
                relative = _safe_member_path(member.name, root_name)
                target = destination / relative
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                # Reject links and special files.  The official source archive
                # is expected to contain regular source files only; rejecting
                # links also closes tar symlink/hardlink traversal paths.
                if not member.isfile() or member.issym() or member.islnk():
                    raise BuildError("source_archive_special_file")
                extracted_bytes += int(member.size)
                if extracted_bytes > MAX_EXTRACTED_BYTES:
                    raise BuildError("source_archive_expanded_too_large")
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as handle:
                    if source is None:
                        raise BuildError("source_archive_file_missing")
                    remaining = int(member.size)
                    while remaining:
                        chunk = source.read(min(CHUNK_SIZE, remaining))
                        if not chunk:
                            raise BuildError("source_archive_file_truncated")
                        handle.write(chunk)
                        remaining -= len(chunk)
                mode = stat.S_IMODE(member.mode) & 0o777
                target.chmod(mode or 0o644)
    except (tarfile.TarError, OSError) as exc:
        if isinstance(exc, BuildError):
            raise
        raise BuildError("source_archive_extract_failed") from exc
    if root_name is None:
        raise BuildError("source_archive_root_missing")
    source_root = destination / root_name
    if not (source_root / SOURCE_FILE).is_file():
        raise BuildError("source_file_missing")
    return source_root


def _patch_source(source_root: Path, patched_root: Path) -> Dict[str, Any]:
    """Copy the source and assert that exactly the requested line changes."""

    shutil.copytree(str(source_root), str(patched_root), symlinks=False)
    source_path = source_root / SOURCE_FILE
    patched_path = patched_root / SOURCE_FILE
    try:
        before = source_path.read_text(encoding="utf-8")
        after = patched_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BuildError("source_file_read_failed") from exc
    if before != after:
        raise BuildError("source_copy_changed_file")
    if before.count(OLD_APPLICATION_LINE) != 1:
        raise BuildError("application_line_count_unexpected")
    if NEW_APPLICATION_LINE in before:
        raise BuildError("application_line_already_patched")
    matching_lines = [
        line
        for line in before.splitlines(keepends=True)
        if line.rstrip("\r\n").strip() == OLD_APPLICATION_LINE
    ]
    if len(matching_lines) != 1:
        raise BuildError("application_line_boundary_unexpected")
    old_line = matching_lines[0]
    new_line = old_line.replace(OLD_APPLICATION_LINE, NEW_APPLICATION_LINE)
    after = before.replace(old_line, new_line, 1)
    if after.count(NEW_APPLICATION_LINE) != 1 or OLD_APPLICATION_LINE in after:
        raise BuildError("application_line_patch_invalid")
    _atomic_text_write(patched_path, after)
    diff_lines = list(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/" + str(SOURCE_FILE),
            tofile="b/" + str(SOURCE_FILE),
        )
    )
    changes = [line for line in diff_lines if (line.startswith("+") and not line.startswith("+++")) or (line.startswith("-") and not line.startswith("---"))]
    expected_changes = ["-" + old_line, "+" + new_line]
    if changes != expected_changes:
        raise BuildError("source_patch_scope_invalid")
    patch_text = "".join(diff_lines)
    return {
        "file": str(SOURCE_FILE),
        "old": old_line.rstrip("\r\n"),
        "new": new_line.rstrip("\r\n"),
        "changed_lines": 1,
        "diff": patch_text,
        "diff_sha256": hashlib.sha256(patch_text.encode("utf-8")).hexdigest(),
        "source_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
        "patched_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
    }


def _atomic_text_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _run_checked(command: Sequence[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            list(command),
            check=True,
            text=True,
            capture_output=capture,
            timeout=600,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise BuildError("docker_command_failed") from exc


def _docker_image_metadata(image: str) -> Dict[str, Any]:
    _run_checked(["docker", "pull", image])
    result = _run_checked(["docker", "image", "inspect", image])
    try:
        payload = json.loads(result.stdout)
        item = payload[0]
        return {
            "reference": image,
            "id": item.get("Id"),
            "repo_digests": item.get("RepoDigests", []),
            "architecture": item.get("Architecture"),
            "os": item.get("Os"),
        }
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise BuildError("docker_image_metadata_invalid") from exc


def _build_in_docker(source_root: Path, output_path: Path, image: str) -> Dict[str, Any]:
    container = "team2-db-prod-sqlcmd-build-" + os.urandom(6).hex()
    command_script = (
        "set -eu; "
        "test \"$(go env GOVERSION)\" = \"go" + GO_VERSION + "\"; "
        "go mod download; "
        "CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 GOTOOLCHAIN=local "
        "go build -mod=readonly -trimpath -buildvcs=false "
        "'-ldflags=-s -w -buildid=' -o /out/sqlcmd ./cmd/modern; "
        "test -s /out/sqlcmd"
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        container,
        "--label",
        "team2.db-prod-sqlcmd-builder=true",
        "-v",
        str(source_root) + ":/src:ro",
        "-v",
        str(output_path.parent) + ":/out:rw",
        "-w",
        "/src",
        image,
        "/bin/sh",
        "-c",
        command_script,
    ]
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=900)
        if result.returncode != 0:
            # Keep only a bounded tail.  The official build should not contain
            # credentials, but this avoids placing a large tool log in errors.
            tail = (result.stdout + "\n" + result.stderr)[-4000:]
            raise BuildError("docker_build_failed:" + tail)
    except subprocess.TimeoutExpired as exc:
        raise BuildError("docker_build_timeout") from exc
    except OSError as exc:
        raise BuildError("docker_build_unavailable") from exc
    finally:
        # --rm handles normal completion.  The name is generated solely by us,
        # so this cleanup cannot target another user's container.
        subprocess.run(
            ["docker", "rm", "-f", container],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise BuildError("build_artifact_missing")
    return {"container": container, "command": command_script}


def _verify_macho(path: Path) -> Dict[str, Any]:
    with path.open("rb") as handle:
        header = handle.read(8)
    if len(header) < 8 or header[:4] != b"\xcf\xfa\xed\xfe":
        raise BuildError("artifact_not_macho64")
    cputype = int.from_bytes(header[4:8], byteorder="little", signed=False)
    if cputype != 0x0100000C:
        raise BuildError("artifact_not_arm64")
    return {"format": "Mach-O 64-bit", "architecture": "arm64", "magic": header[:4].hex()}


def _new_staging(path_arg: Optional[str], commit: str) -> Path:
    if path_arg is None:
        return Path(tempfile.mkdtemp(prefix="team2-db-prod-sqlcmd-build-", dir="/tmp"))
    requested = Path(path_arg).expanduser()
    try:
        resolved_parent = requested.parent.resolve()
        tmp_root = Path("/tmp").resolve()
        if requested.is_absolute() is False or os.path.commonpath([str(resolved_parent), str(tmp_root)]) != str(tmp_root):
            raise BuildError("staging_path_must_be_under_tmp")
        if requested.exists():
            raise BuildError("staging_path_already_exists")
        requested.mkdir(mode=0o700, parents=False)
        return requested
    except OSError as exc:
        raise BuildError("staging_path_create_failed") from exc


def build(staging_arg: Optional[str], docker_image: str) -> Dict[str, Any]:
    if not IMAGE_RE.fullmatch(docker_image):
        raise BuildError("docker_image_invalid")
    commit, ref_metadata = _resolve_commit()
    staging = _new_staging(staging_arg, commit)
    archive = staging / "source.tar.gz"
    extracted = staging / "source"
    patched = staging / "patched"
    artifact_dir = staging / "artifact"
    artifact_dir.mkdir(mode=0o700)
    artifact = artifact_dir / "sqlcmd"
    try:
        archive_url = ARCHIVE_URL_TEMPLATE.format(commit=commit)
        source_metadata = _download(archive_url, archive, MAX_ARCHIVE_BYTES)
        source_root = _extract_archive(archive, extracted, commit)
        patch_metadata = _patch_source(source_root, patched / source_root.name)
        # Remove any stale output before invoking the builder.  The staging dir
        # is new, and this also guarantees an unsuccessful build is never
        # mistaken for a usable binary.
        try:
            artifact.unlink()
        except FileNotFoundError:
            pass
        image_metadata = _docker_image_metadata(docker_image)
        build_metadata = _build_in_docker(patched / source_root.name, artifact, docker_image)
        macho_metadata = _verify_macho(artifact)
        artifact_metadata = {
            "path": str(artifact),
            "bytes": artifact.stat().st_size,
            "sha256": _sha256(artifact),
            **macho_metadata,
        }
        provenance = {
            "schema": 1,
            "tool": "tools/db_prod_build_sqlcmd.py",
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": {
                "repository": REPOSITORY,
                "tag": TAG,
                "commit": commit,
                "ref": ref_metadata,
                "archive": source_metadata,
            },
            "patch": patch_metadata,
            "toolchain": {"go": GO_VERSION, "docker_image": image_metadata},
            "build": {
                "goos": "darwin",
                "goarch": "arm64",
                "cgo_enabled": False,
                "flags": ["-mod=readonly", "-trimpath", "-buildvcs=false", "-ldflags=-s -w -buildid="],
                "docker": build_metadata,
            },
            "artifact": artifact_metadata,
            "installation": {"performed": False, "target": None},
        }
        provenance_path = staging / "provenance.json"
        _json_dump(provenance_path, provenance)
        return {"staging": str(staging), "artifact": artifact_metadata, "provenance": str(provenance_path), "commit": commit}
    except Exception:
        # A failed build must not leave a file that an installation step could
        # accidentally pick up as a completed artifact.
        try:
            artifact.unlink()
        except FileNotFoundError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-dir", help="new private staging directory under /tmp")
    parser.add_argument("--docker-image", default=DEFAULT_DOCKER_IMAGE, help="official Go builder image")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    os.umask(0o077)
    args = _parser().parse_args(argv)
    try:
        result = build(args.staging_dir, args.docker_image)
    except BuildError as exc:
        print("build failed: " + str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("build interrupted", file=sys.stderr)
        return 130
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
