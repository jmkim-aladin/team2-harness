#!/usr/bin/env python3
"""Audit the fixed attempt_id/scenario_id/status CSV evidence contract.

PASS/0 confirms the declared sample counts and rates, not production readiness.
FAIL/1 preserves observed failures or mismatched claims. INCONCLUSIVE/2 means
evidence is missing, invalid, or incomplete. Inputs are never modified.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys


EXIT_CODES = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}


def read_input(path):
    raw = path.read_bytes()
    return raw, {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}


def load_rows(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), strict=True)
    fields = reader.fieldnames or []
    if not {"attempt_id", "scenario_id", "status"}.issubset(fields) or len(set(fields)) != len(fields):
        raise ValueError("CSV requires distinct attempt_id, scenario_id, status headers")
    rows, attempts = [], set()
    for number, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"CSV row {number} has the wrong number of columns")
        for key in ("attempt_id", "scenario_id", "status"):
            row[key] = row[key].strip()
        if not row["attempt_id"] or row["attempt_id"] in attempts:
            raise ValueError(f"CSV row {number} has a missing or repeated attempt_id")
        if not row["scenario_id"] or row["status"] not in {"passed", "failed", "excluded"}:
            raise ValueError(f"CSV row {number} has a missing scenario_id or invalid status")
        attempts.add(row["attempt_id"])
        rows.append(row)
    return rows


def load_report(raw):
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("report contains a non-finite number")
        return number

    def invalid_constant(value):
        raise ValueError("report contains a non-JSON numeric constant")

    def distinct_keys(pairs):
        values = dict(pairs)
        if len(values) != len(pairs):
            raise ValueError("report contains duplicate JSON keys")
        return values

    claimed = json.loads(raw, parse_float=finite_float, parse_constant=invalid_constant,
                         object_pairs_hook=distinct_keys)
    if not isinstance(claimed, dict):
        raise ValueError("report must be a JSON object")
    unique, rate = claimed.get("claimed_unique_scenarios"), claimed.get("claimed_pass_rate")
    if type(unique) is not int or unique < 0:
        raise ValueError("claimed_unique_scenarios must be a nonnegative integer")
    if type(rate) not in (int, float) or not 0 <= rate <= 1:
        raise ValueError("claimed_pass_rate must be a number between zero and one")
    return claimed


def audit(samples, report):
    result = {"schema_version": 1, "status": "INCONCLUSIVE", "identity_key": "scenario_id",
              "inputs": {}, "counts": None, "rates": None, "reported_metadata": {}, "issues": []}
    try:
        sample_bytes, result["inputs"]["samples"] = read_input(samples)
        report_bytes, result["inputs"]["report"] = read_input(report)
        rows = load_rows(sample_bytes)
        claimed = load_report(report_bytes)
        if "data" in claimed:
            data = claimed["data"]
            if not isinstance(data, str) or (report.parent / data).resolve() != samples.resolve():
                raise ValueError("report data does not identify the supplied samples file")
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        result["issues"].append({"code": "invalid-input", "detail": str(error)})
        return result
    result["reported_metadata"] = claimed
    attempts = len(rows)
    unique = len({row["scenario_id"] for row in rows})
    passed = sum(row["status"] == "passed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    excluded = sum(row["status"] == "excluded" for row in rows)
    compared = passed + failed
    rate = passed / compared if compared else None
    result["counts"] = {"attempts": attempts, "unique_scenarios": unique,
                        "duplicate_attempts": attempts - unique, "passed": passed,
                        "failed": failed, "excluded": excluded, "compared": compared}
    result["rates"] = {"compared_denominator": compared, "compared_pass_rate": rate,
                       "all_attempts_denominator": attempts,
                       "all_attempts_pass_rate": passed / attempts if attempts else None}
    if not compared:
        result["issues"].append({"code": "no-comparable-samples"})
        return result
    if unique != claimed["claimed_unique_scenarios"]:
        result["issues"].append({"code": "unique-count-mismatch"})
    if abs(rate - claimed["claimed_pass_rate"]) > 1e-12:
        result["issues"].append({"code": "pass-rate-mismatch"})
    if failed:
        result["issues"].append({"code": "observed-failures"})
    result["status"] = "FAIL" if result["issues"] else "PASS"
    if excluded:
        result["issues"].append({"code": "excluded-samples"})
        if result["status"] != "FAIL":
            result["status"] = "INCONCLUSIVE"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        print(json.dumps({"schema_version": 1, "status": "INCONCLUSIVE", "counts": None,
                          "issues": [{"code": "output-unavailable", "detail": str(error)}]}))
        return 2
    result = audit(args.samples, args.report)
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (args.output / "result.json").write_text(payload, encoding="utf-8")
    receipt = {"argv": sys.argv[1:] if argv is None else argv,
               "cwd": str(Path.cwd()), "tool_path": str(Path(__file__).resolve()),
               "python_executable": sys.executable,
               "recorded_at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
               "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(payload, end="")
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
