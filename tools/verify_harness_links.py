#!/usr/bin/env python3
"""실제 링크 동기화 CLI를 격리 fixture에서 검증하고 정리 후 증거를 보존한다."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SYNC_TOOL = Path(__file__).with_name("sync_harness_links.py")
INITIAL_NOTE = """---
title: 검증 서비스
updated_at: 2000-01-01
---
# 사람이 작성한 제목

이 본문은 동기화 후에도 보존한다.

<!-- generated:harness-link -->
예전 카탈로그 정보
<!-- /generated -->
"""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): digest(p.read_bytes())
            for p in sorted(root.rglob("*")) if p.is_file()}


class ObservedFailure(Exception):
    """실행 성공 후 기대한 산출물이 사라지거나 손상된 제품 동작."""


def read_note(path: Path, evidence: Path) -> bytes:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise ObservedFailure("expected note was deleted") from exc
    except IsADirectoryError as exc:
        raise ObservedFailure("expected note was replaced by a directory") from exc
    evidence.write_bytes(data)
    try:
        data.decode("utf-8")
    except UnicodeError as exc:
        raise ObservedFailure("expected UTF-8 note was corrupted") from exc
    return data


def verify(output: Path, sync_tool: Path = SYNC_TOOL) -> dict:
    """output은 새 디렉터리여야 한다. 기록은 남기고 이번 실행의 fixture만 정리한다."""
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report: dict = {"status": "INCONCLUSIVE", "checks": {}, "commands": [],
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "environment": {"python": platform.python_version(), "platform": platform.system()},
                    "source": {"path": str(sync_tool.resolve())}}
    scratch_path: Path | None = None

    def run(label: str, argv: list[str]) -> None:
        # 외부 GIT_DIR/GIT_INDEX_FILE 등이 개인 작업 공간으로 fixture 쓰기를 돌리지 않게 한다.
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30, env=env)
        (output / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (output / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        report["commands"].append({"step": label, "argv": argv, "exit_code": result.returncode})
        if result.returncode:
            raise RuntimeError(f"{label}: exit {result.returncode}")

    try:
        report["source"]["sha256"] = digest(sync_tool.read_bytes())
        with tempfile.TemporaryDirectory(prefix="team2-link-fixture-") as scratch:
            scratch_path = Path(scratch)
            harness, vault = scratch_path / "harness", scratch_path / "vault"
            (harness / "catalog").mkdir(parents=True)
            (harness / "policies").mkdir()
            (harness / "catalog/sample.yaml").write_text(
                'service_id: sample\nname: "검증 서비스"\ntype: new\n'
                'owners:\n  primary: sample\n', encoding="utf-8")
            (harness / "policies/team-members.md").write_text(
                "| 역할 | 이름 | 이메일 | 담당 |\n|---|---|---|---|\n"
                "| 개발 | 검증 담당 | sample@example.invalid | sample |\n", encoding="utf-8")
            note = vault / "wiki/services/sample/_index.md"
            note.parent.mkdir(parents=True)
            note.write_text(INITIAL_NOTE, encoding="utf-8")
            sentinel = vault / "user-note.txt"
            sentinel.write_text("사용자 작성 파일 보존\n", encoding="utf-8")
            run("init", ["git", "-C", str(vault), "init", "--quiet"])
            argv = [sys.executable, str(sync_tool.resolve()), "--vault", str(vault),
                    "--harness", str(harness), "--target", "services"]
            before = snapshot(vault)
            (output / "before.md").write_bytes(note.read_bytes())

            run("dry-run", argv)
            report["checks"]["dry_run_preserves_files_and_git"] = snapshot(vault) == before

            run("apply", argv + ["--apply"])
            first = read_note(note, output / "after.md")
            expected = ("- 이름: 검증 서비스", "- 분류: new", "- 오너: 검증 담당 (sample)",
                        "source=team2/catalog/sample.yaml")
            report["checks"]["catalog_values_visible"] = all(x in first.decode() for x in expected)
            report["checks"]["human_text_preserved"] = "이 본문은 동기화 후에도 보존한다." in first.decode()
            report["checks"]["old_value_removed"] = "예전 카탈로그 정보" not in first.decode()
            report["checks"]["single_generated_block"] = first.count(b"<!-- generated:harness-link") == 1
            report["checks"]["other_files_preserved"] = (
                read_note(sentinel, output / "other-file.txt").decode() == "사용자 작성 파일 보존\n")

            run("repeat", argv + ["--apply"])
            report["checks"]["repeat_is_idempotent"] = read_note(note, output / "repeat.md") == first

            # 생성 영역이 없는 문서는 사람이 소유한다. 이를 재개 시 덮어쓰지 않는다.
            without_marker = "# 사용자 문서\n생성 영역 없음\n"
            note.write_text(without_marker, encoding="utf-8")
            run("unmanaged", argv + ["--apply"])
            report["checks"]["unmanaged_note_preserved"] = read_note(note, output / "unmanaged.md").decode() == without_marker

            # 이미 한 번 실행한 작업을 초기 입력부터 재개해 같은 결과로 수렴하는지 관찰한다.
            note.write_text(INITIAL_NOTE, encoding="utf-8")
            run("resume", argv + ["--apply"])
            report["checks"]["resume_converges"] = read_note(note, output / "resume.md") == first
            report["source"]["unchanged_during_run"] = digest(sync_tool.read_bytes()) == report["source"]["sha256"]
            report["checks"]["source_unchanged"] = report["source"]["unchanged_during_run"]
        report["status"] = "PASS" if all(report["checks"].values()) else "FAIL"
    except ObservedFailure as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["cleanup"] = {"scratch_removed": scratch_path is None or not scratch_path.exists()}
        report["artifacts"] = {p.name: digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}
        (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="증거를 보관할 새 디렉터리 (기존 경로 거부)")
    args = parser.parse_args()
    try:
        report = verify(args.output)
    except OSError as exc:
        parser.error(str(exc))
    print(json.dumps({"status": report["status"], "evidence": str(args.output.resolve() / "result.json")}, ensure_ascii=False))
    return {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
