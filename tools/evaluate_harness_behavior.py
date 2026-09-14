#!/usr/bin/env python3
"""Compare two harness runs using only pre-declared, observable artifacts.

The evaluator is intentionally small.  It does not launch an agent and it does
not trust a status field written by the agent.  A suite describes the same
task/cases and expected observations for both runs.  Each run directory must
contain ``receipt.json`` with the following shape::

    {
      "schema_version": 1,
      "variant": "A",
      "conditions": {
        "confirmed": true,
        "fixture_digest": "sha256:...",
        "model": "...",
        "settings": {"temperature": 0},
        "budget": {"max_tokens": 1000},
        "skill_digest": "sha256:..."
      },
      "cases": {
        "case-id": {
          "exit_code": 0,
          "timed_out": false,
          "artifact_dir": "cases/case-id"
        }
      }
    }

The suite has this shape::

    {
      "schema_version": 1,
      "suite_id": "skill-change-2026-09-14",
      "cases": [
        {
          "id": "case-id",
          "task": "the same user request used for both runs",
          "assertions": [
            {"type": "json_field_equals", "path": "result.json",
             "field": "status", "expected": "ok"},
            {"type": "text_contains", "path": "report.md",
             "literal": "## Evidence"},
            {"type": "file_absent", "path": "debug.log"}
          ]
        }
      ]
    }

Paths in receipts and assertions are relative to their run/case artifact
directory.  Absolute paths, ``..`` components, and symlink escapes are
rejected.  A missing or malformed receipt/artifact, unequal shared conditions,
timeout, or non-zero execution is ``INCONCLUSIVE``.  A present artifact that
does not satisfy an assertion is ``FAIL``.  A run is ``PASS`` only when every
case completed and every assertion was directly observed to pass.

The evaluator preserves the input run directories byte-for-byte.  The output
file must be outside both run directories and the suite file.  ``PASS`` fields
in receipts or artifacts are never used as evidence; only the assertion types
above are evaluated.  JSON assertions inspect the user-requested artifact, so
they do not establish that the artifact contents are an independent oracle.

Usage::

    python3 tools/evaluate_harness_behavior.py \
      --suite suite.json --baseline run-a --candidate run-b \
      --output evaluation.json

The labels in the result are neutral ``A`` and ``B``.  The command-line names
are only convenience names for selecting the two input directories.
"""

from __future__ import annotations

import argparse
import json
import ntpath
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
RECEIPT_NAME = "receipt.json"
CONDITION_KEYS = ("fixture_digest", "model", "settings", "budget", "skill_digest", "confirmed")
SHARED_CONDITION_KEYS = tuple(k for k in CONDITION_KEYS if k != "skill_digest")
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_INCONCLUSIVE = "INCONCLUSIVE"

ASSERTION_TYPES = {
    "json_field_equals": "json_field_equals",
    "json_field_equality": "json_field_equals",
    "file_text_contains": "text_contains",
    "file_text_literal": "text_contains",
    "text_contains": "text_contains",
    "file_absent": "file_absent",
}

LIMITATIONS = [
    "JSON assertions inspect the user-requested artifact; they do not prove that the artifact contents are an independent oracle.",
    "The evaluator compares recorded runs and preserves raw artifacts; it does not reproduce the agent or infer hidden reasoning.",
]


class InputError(ValueError):
    """The suite or command-line input is not a supported evaluation input."""


class EvidenceError(ValueError):
    """A receipt or artifact cannot be safely or reliably observed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _json_load(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise EvidenceError("missing-evidence", "file is missing: %s" % path) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("malformed-evidence", "cannot read JSON file: %s" % path) from exc


def _json_dump(value: Any) -> str:
    """Return the canonical representation used for condition comparison."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _relative_path_error(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return "path must be a non-empty string"
    if "\x00" in value:
        return "path contains NUL"
    # Treat both POSIX and Windows spellings as untrusted even on macOS/Linux.
    if value.startswith(("/", "\\")) or os.path.isabs(value) or ntpath.isabs(value):
        return "path must be relative"
    drive, _ = ntpath.splitdrive(value)
    if drive:
        return "path must not contain a drive prefix"
    parts = value.replace("\\", "/").split("/")
    if ".." in parts:
        return "path must not contain '..'"
    return None


def _safe_join(root: Path, relative: str, *, allow_root: bool = True) -> Path:
    """Resolve *relative* below *root*, rejecting traversal and symlink escape."""

    error = _relative_path_error(relative)
    if error:
        raise EvidenceError("path-escape", "%s: %s" % (error, relative))
    root_real = Path(os.path.realpath(str(root)))
    candidate = Path(os.path.realpath(os.path.join(str(root_real), relative)))
    try:
        common = os.path.commonpath((str(root_real), str(candidate)))
    except ValueError as exc:
        raise EvidenceError("path-escape", "path is on another filesystem: %s" % relative) from exc
    if common != str(root_real) or (not allow_root and candidate == root_real):
        raise EvidenceError("path-escape", "path escapes run directory: %s" % relative)
    # Keep the lexical final component so absence checks see dangling links.
    return root_real / relative


def _validate_schema_version(value: Any, where: str) -> None:
    if type(value) is not int or value != SCHEMA_VERSION:
        raise InputError("%s schema_version must be %d" % (where, SCHEMA_VERSION))


def _case_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError("case id must be a non-empty string")
    # IDs are identifiers, not paths.  Keeping them path-free prevents a case
    # identifier from becoming an accidental path component in future callers.
    if any(c in value for c in ("/", "\\", "\x00")) or value in (".", ".."):
        raise InputError("case id must not contain path separators: %s" % value)
    return value


def _normalise_assertion(raw: Any, case_id: str, index: int) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise InputError("case %s assertion %d must be an object" % (case_id, index))
    raw_type = raw.get("type")
    assertion_type = ASSERTION_TYPES.get(raw_type) if isinstance(raw_type, str) else None
    if assertion_type is None:
        raise InputError("case %s assertion %d has unsupported type" % (case_id, index))
    path = raw.get("path")
    path_error = _relative_path_error(path)
    if path_error:
        raise InputError("case %s assertion %d path: %s" % (case_id, index, path_error))
    normalised: Dict[str, Any] = {"type": assertion_type, "path": path}
    if assertion_type == "json_field_equals":
        if "field" not in raw or not isinstance(raw.get("field"), (str, list)):
            raise InputError("case %s assertion %d needs a string/list field" % (case_id, index))
        field = raw["field"]
        if isinstance(field, str) and not field:
            raise InputError("case %s assertion %d field must not be empty" % (case_id, index))
        if isinstance(field, list) and any(type(part) not in (str, int) for part in field):
            raise InputError("case %s assertion %d field parts must be strings or integers" % (case_id, index))
        if "expected" not in raw:
            raise InputError("case %s assertion %d needs expected" % (case_id, index))
        normalised["field"] = field
        normalised["expected"] = raw["expected"]
    elif assertion_type == "text_contains":
        if not isinstance(raw.get("literal"), str) or not raw.get("literal"):
            raise InputError("case %s assertion %d needs a non-empty literal" % (case_id, index))
        normalised["literal"] = raw["literal"]
    return normalised


def load_suite(path: Path) -> Dict[str, Any]:
    """Load and validate a suite, returning a deterministic internal shape."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError("cannot read suite JSON: %s" % path) from exc
    if not isinstance(raw, dict):
        raise InputError("suite must be a JSON object")
    version = raw.get("schema_version", raw.get("version"))
    _validate_schema_version(version, "suite")
    suite_id = raw.get("suite_id")
    if not isinstance(suite_id, str) or not suite_id.strip():
        raise InputError("suite_id must be a non-empty string")
    raw_cases = raw.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise InputError("suite cases must be a non-empty list")

    cases: List[Dict[str, Any]] = []
    seen = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise InputError("each suite case must be an object")
        case_id = _case_id(raw_case.get("id"))
        if case_id in seen:
            raise InputError("duplicate suite case: %s" % case_id)
        seen.add(case_id)
        raw_assertions = raw_case.get("assertions")
        if not isinstance(raw_assertions, list) or not raw_assertions:
            raise InputError("case %s needs at least one assertion" % case_id)
        assertions = [
            _normalise_assertion(assertion, case_id, index)
            for index, assertion in enumerate(raw_assertions)
        ]
        case: Dict[str, Any] = {"id": case_id, "assertions": assertions}
        if "task" in raw_case:
            case["task"] = raw_case["task"]
        cases.append(case)
    return {"schema_version": SCHEMA_VERSION, "suite_id": suite_id, "cases": cases}


def _field_parts(field: Any) -> List[Any]:
    if isinstance(field, list):
        return list(field)
    if field.startswith("/"):
        if field == "/":
            return [""]
        return [part.replace("~1", "/").replace("~0", "~") for part in field[1:].split("/")]
    return field.split(".")


def _get_field(document: Any, field: Any) -> Tuple[bool, Any]:
    current = document
    for part in _field_parts(field):
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int):
            if part < 0 or part >= len(current):
                return False, None
            current = current[part]
        elif isinstance(current, list) and isinstance(part, str) and part.isdigit():
            index = int(part)
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current


def _assertion_result(
    assertion: Mapping[str, Any], artifact_root: Path, index: int
) -> Dict[str, Any]:
    assertion_type = assertion["type"]
    relative = assertion["path"]
    base: Dict[str, Any] = {"index": index, "type": assertion_type, "path": relative}
    try:
        target = _safe_join(artifact_root, relative)
    except EvidenceError as exc:
        base.update({"status": STATUS_INCONCLUSIVE, "reason": exc.code, "detail": exc.message})
        return base

    if assertion_type == "file_absent":
        # lexists observes dangling symlinks too.  _safe_join already rejected
        # a symlink whose resolved target escapes the artifact root.
        if os.path.lexists(str(target)):
            base.update({"status": STATUS_FAIL, "reason": "assertion-false", "observed": "present"})
        else:
            base.update({"status": STATUS_PASS, "observed": "absent"})
        return base

    if not os.path.lexists(str(target)):
        base.update({"status": STATUS_INCONCLUSIVE, "reason": "missing-evidence"})
        return base
    if not target.is_file():
        base.update({"status": STATUS_INCONCLUSIVE, "reason": "malformed-evidence", "detail": "artifact is not a file"})
        return base

    if assertion_type == "text_contains":
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            base.update({"status": STATUS_INCONCLUSIVE, "reason": "malformed-evidence", "detail": str(exc)})
            return base
        literal = assertion["literal"]
        if literal in text:
            base.update({"status": STATUS_PASS, "literal": literal})
        else:
            base.update({"status": STATUS_FAIL, "reason": "assertion-false", "literal": literal})
        return base

    # json_field_equals
    try:
        with target.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        base.update({"status": STATUS_INCONCLUSIVE, "reason": "malformed-evidence", "detail": str(exc)})
        return base
    found, observed = _get_field(document, assertion["field"])
    base["field"] = assertion["field"]
    base["expected"] = assertion["expected"]
    if not found:
        base.update({"status": STATUS_FAIL, "reason": "assertion-false", "observed": "<missing-field>"})
    elif _json_dump(observed) == _json_dump(assertion["expected"]):
        base.update({"status": STATUS_PASS, "observed": observed})
    else:
        base.update({"status": STATUS_FAIL, "reason": "assertion-false", "observed": observed})
    return base


def _run_issue(status: str, code: str, detail: Optional[str] = None) -> Dict[str, Any]:
    issue: Dict[str, Any] = {"status": status, "reason": code}
    if detail:
        issue["detail"] = detail
    return issue


def _validate_conditions(raw: Any) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    if not isinstance(raw, dict):
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "conditions must be an object")]
    missing = [key for key in CONDITION_KEYS if key not in raw]
    if missing:
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "missing conditions: " + ", ".join(missing))]
    if type(raw["confirmed"]) is not bool:
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "conditions.confirmed must be boolean")]
    for key in ("fixture_digest", "model", "skill_digest"):
        if not isinstance(raw.get(key), str) or not raw.get(key):
            return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "%s must be a non-empty string" % key)]
    for key in ("settings", "budget"):
        if not isinstance(raw.get(key), dict):
            return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "%s must be an object" % key)]
    # Keep additional condition fields in the comparison.  The contract is
    # that the skill digest is the only field allowed to differ; silently
    # dropping an unrecognised field would make that guarantee unenforceable.
    return dict(raw), []


def _load_receipt(run_dir: Path, expected_variant: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    try:
        receipt_path = _safe_join(run_dir, RECEIPT_NAME)
        raw = _json_load(receipt_path)
    except EvidenceError as exc:
        return None, [_run_issue(STATUS_INCONCLUSIVE, exc.code, exc.message)]
    if not isinstance(raw, dict):
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "receipt must be an object")]
    try:
        _validate_schema_version(raw.get("schema_version", raw.get("version")), "receipt")
    except InputError as exc:
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", str(exc))]
    if raw.get("variant") != expected_variant:
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "receipt variant must be %s" % expected_variant)]
    conditions, condition_issues = _validate_conditions(raw.get("conditions"))
    if condition_issues:
        return None, condition_issues
    cases = raw.get("cases")
    if not isinstance(cases, dict):
        return None, [_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "receipt cases must be an object")]
    return {"conditions": conditions, "cases": cases}, []


def _evaluate_run(suite: Mapping[str, Any], run_dir: Path, label: str) -> Dict[str, Any]:
    run: Dict[str, Any] = {
        "label": label,
        "run_dir": str(run_dir),
        "status": STATUS_INCONCLUSIVE,
        "cases": [],
        "issues": [],
    }
    if not run_dir.exists() or not run_dir.is_dir():
        run["issues"].append(_run_issue(STATUS_INCONCLUSIVE, "missing-evidence", "run directory is missing"))
        return run

    receipt, receipt_issues = _load_receipt(run_dir, label)
    if receipt_issues or receipt is None:
        run["issues"].extend(receipt_issues)
        return run
    run["conditions"] = receipt["conditions"]
    receipt_cases = receipt["cases"]
    suite_cases = suite["cases"]
    expected_ids = [case["id"] for case in suite_cases]
    extras = sorted(set(receipt_cases) - set(expected_ids))
    if extras:
        run["issues"].append(_run_issue(STATUS_INCONCLUSIVE, "malformed-evidence", "unexpected cases: " + ", ".join(extras)))
    missing = [case_id for case_id in expected_ids if case_id not in receipt_cases]
    if missing:
        run["issues"].append(_run_issue(STATUS_INCONCLUSIVE, "missing-evidence", "missing cases: " + ", ".join(missing)))

    for suite_case in suite_cases:
        case_id = suite_case["id"]
        record = receipt_cases.get(case_id)
        case_result: Dict[str, Any] = {"id": case_id, "status": STATUS_INCONCLUSIVE, "assertions": []}
        if not isinstance(record, dict):
            case_result["reason"] = "missing-evidence" if record is None else "malformed-evidence"
            run["cases"].append(case_result)
            continue
        case_result["exit_code"] = record.get("exit_code")
        case_result["timed_out"] = record.get("timed_out")
        artifact_dir = record.get("artifact_dir")
        case_result["artifact_dir"] = artifact_dir
        if isinstance(record.get("exit_code"), bool) or not isinstance(record.get("exit_code"), int):
            case_result["reason"] = "malformed-evidence"
            run["cases"].append(case_result)
            continue
        if not isinstance(record.get("timed_out"), bool):
            case_result["reason"] = "malformed-evidence"
            run["cases"].append(case_result)
            continue
        if record["timed_out"]:
            case_result["reason"] = "timeout"
            run["cases"].append(case_result)
            continue
        if record["exit_code"] != 0:
            case_result["reason"] = "nonzero-exit"
            run["cases"].append(case_result)
            continue
        if not isinstance(artifact_dir, str):
            case_result["reason"] = "malformed-evidence"
            run["cases"].append(case_result)
            continue
        try:
            artifact_root = _safe_join(run_dir, artifact_dir, allow_root=False)
        except EvidenceError as exc:
            case_result["reason"] = exc.code
            case_result["detail"] = exc.message
            run["cases"].append(case_result)
            continue
        if not artifact_root.exists():
            case_result["reason"] = "missing-evidence"
            run["cases"].append(case_result)
            continue
        if not artifact_root.is_dir():
            case_result["reason"] = "malformed-evidence"
            case_result["detail"] = "artifact_dir is not a directory"
            run["cases"].append(case_result)
            continue

        assertions = [
            _assertion_result(assertion, artifact_root, index)
            for index, assertion in enumerate(suite_case["assertions"])
        ]
        case_result["assertions"] = assertions
        statuses = {assertion["status"] for assertion in assertions}
        if STATUS_FAIL in statuses:
            case_result["status"] = STATUS_FAIL
            case_result["reason"] = "assertion-false"
        elif STATUS_INCONCLUSIVE in statuses:
            case_result["status"] = STATUS_INCONCLUSIVE
            case_result["reason"] = "assertion-evidence-inconclusive"
        else:
            case_result["status"] = STATUS_PASS
        run["cases"].append(case_result)

    case_statuses = [case["status"] for case in run["cases"]]
    if STATUS_FAIL in case_statuses:
        run["status"] = STATUS_FAIL
    elif run["issues"] or not case_statuses or STATUS_INCONCLUSIVE in case_statuses:
        run["status"] = STATUS_INCONCLUSIVE
    else:
        run["status"] = STATUS_PASS
    return run


def _compare_conditions(run_a: Mapping[str, Any], run_b: Mapping[str, Any]) -> Dict[str, Any]:
    conditions_a = run_a.get("conditions")
    conditions_b = run_b.get("conditions")
    if not isinstance(conditions_a, dict) or not isinstance(conditions_b, dict):
        return {"status": STATUS_INCONCLUSIVE, "reason": "conditions-unavailable"}
    if not conditions_a["confirmed"] or not conditions_b["confirmed"]:
        return {"status": STATUS_INCONCLUSIVE, "reason": "conditions-unconfirmed"}
    if conditions_a["skill_digest"] == conditions_b["skill_digest"]:
        return {"status": STATUS_INCONCLUSIVE, "reason": "same-skill-digest"}
    shared_keys = sorted((set(conditions_a) | set(conditions_b)) - {"skill_digest"})
    shared_a = {key: value for key, value in conditions_a.items() if key != "skill_digest"}
    shared_b = {key: value for key, value in conditions_b.items() if key != "skill_digest"}
    if _json_dump(shared_a) != _json_dump(shared_b):
        differing = [key for key in shared_keys if key not in shared_a or key not in shared_b
                     or _json_dump(shared_a[key]) != _json_dump(shared_b[key])]
        return {"status": STATUS_INCONCLUSIVE, "reason": "conditions-mismatch", "differing_keys": differing}
    return {
        "status": STATUS_PASS,
        "shared_equal": True,
        "skill_digest_differs": conditions_a.get("skill_digest") != conditions_b.get("skill_digest"),
    }


def evaluate(suite: Mapping[str, Any], baseline_dir: Path, candidate_dir: Path) -> Dict[str, Any]:
    """Evaluate two already-recorded runs and return the JSON summary.

    ``baseline_dir`` is emitted as neutral label ``A`` and ``candidate_dir`` as
    ``B``.  The pair status is strict: any observed false assertion is FAIL;
    missing/untrusted evidence or unequal shared conditions is INCONCLUSIVE.
    Per-run statuses make a baseline-fail/candidate-pass improvement visible
    without allowing the pair to claim every observation passed.
    """

    suite_cases = suite.get("cases") if isinstance(suite, Mapping) else None
    if not isinstance(suite_cases, list) or not suite_cases:
        raise InputError("evaluate expects a validated suite")
    root_a = Path(os.path.realpath(str(baseline_dir)))
    root_b = Path(os.path.realpath(str(candidate_dir)))
    run_a = _evaluate_run(suite, root_a, "A")
    run_b = _evaluate_run(suite, root_b, "B")
    conditions = _compare_conditions(run_a, run_b)
    issues: List[Dict[str, Any]] = []
    if conditions["status"] == STATUS_INCONCLUSIVE:
        issues.append(_run_issue(STATUS_INCONCLUSIVE, conditions["reason"], ", ".join(conditions.get("differing_keys", [])) or None))
    if root_a == root_b:
        conditions = {"status": STATUS_INCONCLUSIVE, "reason": "same-run-directory"}
        issues.append(_run_issue(STATUS_INCONCLUSIVE, "same-run-directory"))
    if run_a["status"] == STATUS_INCONCLUSIVE or run_b["status"] == STATUS_INCONCLUSIVE:
        issues.append(_run_issue(STATUS_INCONCLUSIVE, "run-evidence-inconclusive"))
    if conditions["status"] == STATUS_INCONCLUSIVE:
        pair_status = STATUS_INCONCLUSIVE
    elif run_a["status"] == STATUS_FAIL or run_b["status"] == STATUS_FAIL:
        pair_status = STATUS_FAIL
    elif issues:
        pair_status = STATUS_INCONCLUSIVE
    else:
        pair_status = STATUS_PASS
    return {
        "schema_version": SCHEMA_VERSION,
        "suite_id": suite["suite_id"],
        "status": pair_status,
        "conditions": conditions,
        "runs": {"A": run_a, "B": run_b},
        "issues": issues,
        "limitations": list(LIMITATIONS),
    }


def _resolved_output(path: Path) -> Path:
    # resolve(strict=False) follows an existing output symlink, which lets us
    # apply the same no-overwrite check to its actual target.
    return Path(os.path.realpath(str(path)))


def _assert_output_is_external(output: Path, suite_path: Path, run_dirs: Iterable[Path]) -> None:
    output_real = _resolved_output(output)
    suite_real = _resolved_output(suite_path)
    output_lexical = Path(os.path.abspath(output))
    if output_real == suite_real or output_lexical == Path(os.path.abspath(suite_path)):
        raise InputError("output must not overwrite the suite")
    for run_dir in run_dirs:
        for root in {Path(os.path.realpath(run_dir)), Path(os.path.abspath(run_dir))}:
            for destination in (output_real, output_lexical):
                try:
                    common = os.path.commonpath((str(root), str(destination)))
                except ValueError:
                    common = ""
                if common == str(root):
                    raise InputError("output must be outside run directory: %s" % root)


def _write_summary(path: Path, summary: Mapping[str, Any]) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(summary, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        # Replace the directory entry, never truncate an input through a hardlink.
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError("cannot write output: %s" % path) from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare two recorded harness runs using direct artifact assertions."
    )
    parser.add_argument("--suite", required=True, type=Path, help="suite JSON with pre-declared cases/assertions")
    parser.add_argument("--baseline", required=True, type=Path, help="run directory for neutral label A")
    parser.add_argument("--candidate", required=True, type=Path, help="run directory for neutral label B")
    parser.add_argument("--output", required=True, type=Path, help="JSON result path outside the input evidence")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        suite = load_suite(args.suite)
        _assert_output_is_external(args.output, args.suite, (args.baseline, args.candidate))
        summary = evaluate(suite, args.baseline, args.candidate)
        _write_summary(args.output, summary)
    except InputError as exc:
        parser.error(str(exc))
    rendered = json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2)
    print(rendered)
    return {STATUS_PASS: 0, STATUS_FAIL: 1, STATUS_INCONCLUSIVE: 2}[summary["status"]]


if __name__ == "__main__":
    sys.exit(main())
