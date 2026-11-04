from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/audit_sample_evidence.py"
FIXTURE = ROOT / "docs/verification/harness-verification-quality/inputs/repeated-samples"


class AuditSampleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def invoke(self, samples=None, report=None, name="evidence"):
        output = self.directory / name
        command = [sys.executable, str(CLI), "--samples", str(samples or FIXTURE / "samples.csv"),
                   "--report", str(report or FIXTURE / "report.json"), "--output", str(output)]
        process = subprocess.run(command, text=True, capture_output=True)
        return process, output

    def inputs(self, text, unique, rate):
        samples = self.directory / "samples.csv"
        samples.write_text(text)
        report = self.directory / "report.json"
        report.write_text(json.dumps({"claimed_unique_scenarios": unique, "claimed_pass_rate": rate}))
        return samples, report

    def test_original_evidence_exposes_repeated_scenarios_and_wrong_denominator(self):
        process, output = self.invoke()
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["counts"], {
            "attempts": 2000, "unique_scenarios": 381, "duplicate_attempts": 1619,
            "passed": 1800, "failed": 100, "excluded": 100, "compared": 1900,
        })
        self.assertEqual(result["rates"]["compared_denominator"], 1900)
        self.assertAlmostEqual(result["rates"]["compared_pass_rate"], 18 / 19)
        self.assertEqual(result["rates"]["all_attempts_pass_rate"], 0.9)
        self.assertEqual(result["identity_key"], "scenario_id")
        self.assertEqual(result["reported_metadata"]["seed"], 20261104)
        self.assertEqual(json.loads((output / "result.json").read_text()), result)

    def test_two_thousand_distinct_passes_and_replay_preserves_inputs_and_evidence(self):
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(["attempt_id", "scenario_id", "status"])
        writer.writerows((i, f"S{i:04}", "passed") for i in range(2000))
        samples, report = self.inputs(text.getvalue(), 2000, 1)
        original = samples.read_bytes(), report.read_bytes()
        first, first_dir = self.invoke(samples, report, name="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        result = json.loads(first.stdout)
        self.assertEqual(result["counts"]["unique_scenarios"], 2000)
        self.assertEqual(result["counts"]["duplicate_attempts"], 0)
        self.assertEqual(result["rates"]["compared_pass_rate"], 1)
        self.assertEqual(result["inputs"]["samples"]["sha256"], hashlib.sha256(original[0]).hexdigest())
        prior_result = (first_dir / "result.json").read_bytes()
        second, _ = self.invoke(samples, report, name="second")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout), result)
        self.assertEqual((first_dir / "result.json").read_bytes(), prior_result)
        self.assertEqual((samples.read_bytes(), report.read_bytes()), original)

    def test_empty_sample_is_inconclusive_without_a_fabricated_success_rate(self):
        samples, report = self.inputs("attempt_id,scenario_id,status\n", 0, 0)
        process, output = self.invoke(samples, report)
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        result = json.loads((output / "result.json").read_text())
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["counts"]["attempts"], 0)
        self.assertIsNone(result["rates"]["compared_pass_rate"])

    def test_exclusions_and_failures_remain_visible_even_when_claimed_rate_matches(self):
        for excluded_status, expected_code, expected_status in [
            ("excluded", 2, "INCONCLUSIVE"), ("failed", 1, "FAIL")
        ]:
            with self.subTest(status=excluded_status):
                samples, report = self.inputs(
                    "attempt_id,scenario_id,status\n1,A,passed\n2,B," + excluded_status + "\n",
                    2, 1 if excluded_status == "excluded" else 0.5)
                process, _ = self.invoke(samples, report, name=excluded_status)
                self.assertEqual(process.returncode, expected_code, process.stdout + process.stderr)
                result = json.loads(process.stdout)
                self.assertEqual(result["status"], expected_status)
                self.assertEqual(result["counts"][excluded_status], 1)
                self.assertEqual(result["rates"]["all_attempts_pass_rate"], 0.5)

    def test_missing_or_malformed_inputs_are_inconclusive_not_a_partial_pass(self):
        cases = [
            ("missing-file", None),
            ("missing-key", "attempt_id,status\n1,passed\n"),
            ("empty-key", "attempt_id,scenario_id,status\n1,,passed\n"),
            ("unknown-status", "attempt_id,scenario_id,status\n1,A,unknown\n"),
            ("duplicate-attempt", "attempt_id,scenario_id,status\n1,A,passed\n1,B,passed\n"),
            ("too-many-columns", "attempt_id,scenario_id,status\n1,A,passed,extra\n"),
            ("too-few-columns", "attempt_id,scenario_id,status\n1,A\n"),
        ]
        for name, text in cases:
            with self.subTest(case=name):
                samples, report = self.inputs(text or "", 1, 1)
                if text is None:
                    samples.unlink()
                process, output = self.invoke(samples, report, name=name)
                self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
                result = json.loads(process.stdout)
                self.assertEqual(result["status"], "INCONCLUSIVE")
                self.assertIsNone(result["counts"])
                self.assertEqual(json.loads((output / "result.json").read_text()), result)

    def test_invalid_claims_cannot_be_accepted_as_matching_numbers(self):
        reports = [
            "[]", "{}", "{",
            '{"claimed_unique_scenarios": true, "claimed_pass_rate": 1}',
            '{"claimed_unique_scenarios": 1, "claimed_pass_rate": true}',
            '{"claimed_unique_scenarios": 1, "claimed_pass_rate": NaN}',
            '{"claimed_unique_scenarios": 1, "claimed_pass_rate": 2}',
            '{"claimed_unique_scenarios": 2, "claimed_unique_scenarios": 1, "claimed_pass_rate": 1}',
        ]
        for index, text in enumerate(reports):
            with self.subTest(report=text):
                samples, report = self.inputs("attempt_id,scenario_id,status\n1,A,passed\n", 1, 1)
                report.write_text(text)
                process, _ = self.invoke(samples, report, name=f"invalid-claim-{index}")
                self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
                self.assertEqual(json.loads(process.stdout)["status"], "INCONCLUSIVE")

    def test_existing_evidence_is_never_overwritten(self):
        output = self.directory / "evidence"
        output.mkdir()
        prior = output / "result.json"
        prior.write_text("previous evidence")
        process, _ = self.invoke()
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertEqual(prior.read_text(), "previous evidence")
        self.assertEqual(json.loads(process.stdout)["status"], "INCONCLUSIVE")

    def test_declared_repeats_and_id_whitespace_are_not_confused_with_distinct_scenarios(self):
        samples, report = self.inputs(
            "attempt_id,scenario_id,status\n1,A,passed\n2, A ,passed\n3,B,passed\n", 2, 1)
        process, _ = self.invoke(samples, report)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["counts"]["unique_scenarios"], 2)
        self.assertEqual(result["counts"]["duplicate_attempts"], 1)

    def test_each_false_claim_fails_even_when_every_attempt_passes(self):
        for unique, rate, code in [(2, 1, "unique-count-mismatch"), (1, 0.5, "pass-rate-mismatch")]:
            with self.subTest(code=code):
                samples, report = self.inputs("attempt_id,scenario_id,status\n1,A,passed\n", unique, rate)
                process, _ = self.invoke(samples, report, name=code)
                self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
                self.assertIn(code, [x["code"] for x in json.loads(process.stdout)["issues"]])

    def test_report_cannot_name_a_different_dataset(self):
        samples, report = self.inputs("attempt_id,scenario_id,status\n1,A,passed\n", 1, 1)
        claims = json.loads(report.read_text())
        claims["data"] = "another-samples.csv"
        report.write_text(json.dumps(claims))
        process, _ = self.invoke(samples, report)
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"], "INCONCLUSIVE")

    def test_all_excluded_preserves_counts_without_claiming_a_success_rate(self):
        samples, report = self.inputs("attempt_id,scenario_id,status\n1,A,excluded\n", 1, 0)
        process, _ = self.invoke(samples, report)
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["counts"]["excluded"], 1)
        self.assertEqual(result["rates"]["compared_denominator"], 0)
        self.assertIsNone(result["rates"]["compared_pass_rate"])


if __name__ == "__main__":
    unittest.main()
