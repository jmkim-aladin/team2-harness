from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "evaluate_harness_behavior.py"
spec = importlib.util.spec_from_file_location("evaluate_harness_behavior", MODULE_PATH)
evaluator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(evaluator)


class HarnessBehaviorEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.suite_path = self.root / "suite.json"
        self.suite = {
            "schema_version": 1,
            "suite_id": "behavior-regression",
            "cases": [
                {
                    "id": "answer",
                    "task": "produce the requested answer",
                    "assertions": [
                        {
                            "type": "json_field_equals",
                            "path": "result.json",
                            "field": "status",
                            "expected": "ok",
                        },
                        {
                            "type": "text_contains",
                            "path": "report.md",
                            "literal": "## Evidence",
                        },
                        {"type": "file_absent", "path": "debug.log"},
                    ],
                }
            ],
        }
        self.write_json(self.suite_path, self.suite)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def make_run(
        self,
        name: str,
        label: str,
        *,
        status: str = "ok",
        report: str = "## Evidence\nobserved",
        exit_code: int = 0,
        timed_out: bool = False,
        artifact_dir: str = "cases/answer",
        conditions: dict | None = None,
        result_contents: object | None = None,
        include_result: bool = True,
    ) -> Path:
        run = self.root / name
        artifacts = run / artifact_dir if not artifact_dir.startswith("../") else run / "cases" / "answer"
        artifacts.mkdir(parents=True, exist_ok=True)
        if include_result:
            value = {"status": status} if result_contents is None else result_contents
            if isinstance(value, str):
                (artifacts / "result.json").write_text(value, encoding="utf-8")
            else:
                self.write_json(artifacts / "result.json", value)
        (artifacts / "report.md").write_text(report, encoding="utf-8")
        shared = {
            "confirmed": True,
            "fixture_digest": "sha256:fixture",
            "model": "gpt-test",
            "settings": {"temperature": 0},
            "budget": {"max_tokens": 1000},
            "skill_digest": "sha256:skill-" + label,
        }
        if conditions:
            shared.update(conditions)
        self.write_json(
            run / "receipt.json",
            {
                "schema_version": 1,
                "variant": label,
                # This is deliberately ignored by the evaluator.  A self
                # reported PASS cannot turn a false artifact into PASS.
                "status": "PASS",
                "conditions": shared,
                "cases": {
                    "answer": {
                        "exit_code": exit_code,
                        "timed_out": timed_out,
                        "artifact_dir": artifact_dir,
                    }
                },
            },
        )
        return run

    def evaluate_runs(self, run_a: Path, run_b: Path) -> dict:
        return evaluator.evaluate(evaluator.load_suite(self.suite_path), run_a, run_b)

    def test_success_uses_direct_json_text_and_absence_observations(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["status"], evaluator.STATUS_PASS)
        self.assertEqual(summary["runs"]["A"]["status"], evaluator.STATUS_PASS)
        self.assertEqual(summary["runs"]["B"]["status"], evaluator.STATUS_PASS)
        self.assertEqual(
            [item["status"] for item in summary["runs"]["A"]["cases"][0]["assertions"]],
            ["PASS", "PASS", "PASS"],
        )
        self.assertTrue(any("independent oracle" in item for item in summary["limitations"]))

    def test_self_reported_pass_cannot_hide_false_assertion(self) -> None:
        run_a = self.make_run("a", "A", status="wrong")
        run_b = self.make_run("b", "B", status="wrong")

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["status"], evaluator.STATUS_FAIL)
        self.assertEqual(summary["runs"]["A"]["status"], evaluator.STATUS_FAIL)
        self.assertEqual(summary["runs"]["B"]["status"], evaluator.STATUS_FAIL)
        self.assertEqual(summary["runs"]["A"]["cases"][0]["assertions"][0]["reason"], "assertion-false")

    def test_missing_artifact_is_inconclusive(self) -> None:
        run_a = self.make_run("a", "A", include_result=False)
        run_b = self.make_run("b", "B")

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["status"], evaluator.STATUS_INCONCLUSIVE)
        self.assertEqual(summary["runs"]["A"]["status"], evaluator.STATUS_INCONCLUSIVE)
        self.assertEqual(
            summary["runs"]["A"]["cases"][0]["assertions"][0]["reason"],
            "missing-evidence",
        )

    def test_timeout_and_nonzero_exit_are_inconclusive(self) -> None:
        run_timeout = self.make_run("timeout", "A", timed_out=True)
        run_nonzero = self.make_run("nonzero", "B", exit_code=7)

        summary = self.evaluate_runs(run_timeout, run_nonzero)

        self.assertEqual(summary["status"], evaluator.STATUS_INCONCLUSIVE)
        self.assertEqual(summary["runs"]["A"]["cases"][0]["reason"], "timeout")
        self.assertEqual(summary["runs"]["B"]["cases"][0]["reason"], "nonzero-exit")

    def test_unequal_shared_conditions_are_inconclusive(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B", conditions={"settings": {"temperature": 1}})

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["status"], evaluator.STATUS_INCONCLUSIVE)
        self.assertEqual(summary["conditions"]["reason"], "conditions-mismatch")
        self.assertEqual(summary["conditions"]["differing_keys"], ["settings"])

    def test_equal_but_unconfirmed_conditions_do_not_pass_comparison(self) -> None:
        shared = {"confirmed": False, "model": "unknown", "budget": {"actual_limit": "unknown"}}
        run_a = self.make_run("a", "A", conditions=shared)
        run_b = self.make_run("b", "B", conditions=shared)
        summary = self.evaluate_runs(run_a, run_b)
        self.assertEqual(summary["status"], "INCONCLUSIVE")
        self.assertEqual(summary["conditions"]["reason"], "conditions-unconfirmed")
        self.assertEqual(summary["runs"]["A"]["status"], "PASS")
        self.assertEqual(summary["runs"]["B"]["status"], "PASS")

    def test_same_policy_is_not_a_change_comparison(self) -> None:
        run_a = self.make_run("a", "A", conditions={"skill_digest": "sha256:same"})
        run_b = self.make_run("b", "B", conditions={"skill_digest": "sha256:same"})
        result = self.evaluate_runs(run_a, run_b)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["conditions"]["reason"], "same-skill-digest")

    def test_missing_condition_is_different_from_explicit_null(self) -> None:
        run_a = self.make_run("a", "A", conditions={"optional": None})
        run_b = self.make_run("b", "B")
        result = self.evaluate_runs(run_a, run_b)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["conditions"]["differing_keys"], ["optional"])

    def test_observed_failure_is_retained_when_other_evidence_is_missing(self) -> None:
        run_a = self.make_run("a", "A", status="wrong")
        run_b = self.make_run("b", "B")
        (run_a / "cases/answer/report.md").unlink()
        result = self.evaluate_runs(run_a, run_b)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["runs"]["A"]["status"], "FAIL")
        self.assertEqual([item["status"] for item in result["runs"]["A"]["cases"][0]["assertions"]],
                         ["FAIL", "INCONCLUSIVE", "PASS"])

    def test_baseline_fail_and_candidate_pass_are_visible_per_neutral_label(self) -> None:
        run_a = self.make_run("a", "A", status="wrong")
        run_b = self.make_run("b", "B", status="ok")

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["runs"]["A"]["status"], evaluator.STATUS_FAIL)
        self.assertEqual(summary["runs"]["B"]["status"], evaluator.STATUS_PASS)
        # Pair status stays strict: one observed false assertion is not a
        # claim that every compared observation passed.
        self.assertEqual(summary["status"], evaluator.STATUS_FAIL)
        self.assertEqual(set(summary["runs"]), {"A", "B"})

    def test_path_escape_is_inconclusive_and_external_artifact_is_untouched(self) -> None:
        outside = self.root / "outside.json"
        outside.write_text('{"status":"ok"}', encoding="utf-8")
        run_a = self.make_run("a", "A", artifact_dir="../outside")
        run_b = self.make_run("b", "B")
        before = outside.read_bytes()

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["status"], evaluator.STATUS_INCONCLUSIVE)
        self.assertEqual(summary["runs"]["A"]["cases"][0]["reason"], "path-escape")
        self.assertEqual(outside.read_bytes(), before)

    def test_symlink_escape_is_inconclusive(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        escaped = run_a / "escaped"
        escaped.symlink_to(outside, target_is_directory=True)
        receipt = json.loads((run_a / "receipt.json").read_text(encoding="utf-8"))
        receipt["cases"]["answer"]["artifact_dir"] = "escaped"
        self.write_json(run_a / "receipt.json", receipt)

        summary = self.evaluate_runs(run_a, run_b)

        self.assertEqual(summary["runs"]["A"]["cases"][0]["reason"], "path-escape")

    def test_repeated_evaluation_is_deterministic_and_preserves_raw_evidence(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        before_a = {path: path.read_bytes() for path in run_a.rglob("*") if path.is_file()}
        before_b = {path: path.read_bytes() for path in run_b.rglob("*") if path.is_file()}

        first = self.evaluate_runs(run_a, run_b)
        second = self.evaluate_runs(run_a, run_b)

        self.assertEqual(first, second)
        self.assertEqual(before_a, {path: path.read_bytes() for path in run_a.rglob("*") if path.is_file()})
        self.assertEqual(before_b, {path: path.read_bytes() for path in run_b.rglob("*") if path.is_file()})

    def test_cli_writes_json_and_stdout_without_overwriting_evidence(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        output = self.root / "evaluation.json"

        code = evaluator.main(
            [
                "--suite",
                str(self.suite_path),
                "--baseline",
                str(run_a),
                "--candidate",
                str(run_b),
                "--output",
                str(output),
            ]
        )

        self.assertEqual(code, 0)
        written = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(written["status"], "PASS")
        self.assertEqual(written, self.evaluate_runs(run_a, run_b))

    def test_output_inside_run_is_rejected(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")

        with self.assertRaises(evaluator.InputError):
            evaluator._assert_output_is_external(run_a / "result.json", self.suite_path, (run_a, run_b))

    def test_output_cannot_replace_evidence_symlink_pointing_outside(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        external = self.root / "external.json"
        external.write_text("original")
        output = run_a / "linked-output.json"
        output.symlink_to(external)
        with self.assertRaises(evaluator.InputError):
            evaluator._assert_output_is_external(output, self.suite_path, (run_a, run_b))
        self.assertTrue(output.is_symlink())
        self.assertEqual(external.read_text(), "original")

    def test_boolean_is_not_equal_to_number_even_when_nested(self) -> None:
        run_a = self.make_run("a", "A", result_contents={"status": {"value": True}})
        run_b = self.make_run("b", "B", result_contents={"status": {"value": 1}})
        self.suite["cases"][0]["assertions"][0]["expected"] = {"value": 1}
        self.write_json(self.suite_path, self.suite)
        result = self.evaluate_runs(run_a, run_b)
        self.assertEqual(result["runs"]["A"]["status"], "FAIL")
        self.assertEqual(result["runs"]["B"]["status"], "PASS")

    def test_dangling_symlink_is_present(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        (run_a / "cases/answer/debug.log").symlink_to("missing.log")
        self.assertEqual(self.evaluate_runs(run_a, run_b)["status"], "FAIL")

    def test_receipt_symlink_cannot_escape_run(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        receipt = run_a / "receipt.json"
        receipt.rename(self.root / "external-receipt.json")
        receipt.symlink_to(self.root / "external-receipt.json")
        result = self.evaluate_runs(run_a, run_b)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["runs"]["A"]["issues"][0]["reason"], "path-escape")

    def test_invalid_schema_and_assertion_type_are_input_errors(self) -> None:
        self.suite["schema_version"] = True
        self.write_json(self.suite_path, self.suite)
        with self.assertRaises(evaluator.InputError):
            evaluator.load_suite(self.suite_path)
        self.suite["schema_version"] = 1
        self.suite["cases"][0]["assertions"][0]["type"] = []
        self.write_json(self.suite_path, self.suite)
        with self.assertRaises(evaluator.InputError):
            evaluator.load_suite(self.suite_path)

    def test_output_hardlink_preserves_original_evidence(self) -> None:
        run_a = self.make_run("a", "A")
        run_b = self.make_run("b", "B")
        source = run_a / "cases/answer/result.json"
        before = source.read_bytes()
        output = self.root / "evaluation.json"
        os.link(source, output)
        evaluator._assert_output_is_external(output, self.suite_path, (run_a, run_b))
        evaluator._write_summary(output, self.evaluate_runs(run_a, run_b))
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(json.loads(output.read_text())["status"], "PASS")

    def test_cli_exit_status_distinguishes_failure_from_missing_evidence(self) -> None:
        run_a = self.make_run("a", "A", status="wrong")
        run_b = self.make_run("b", "B")
        argv = ["--suite", str(self.suite_path), "--baseline", str(run_a),
                "--candidate", str(run_b), "--output", str(self.root / "evaluation.json")]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluator.main(argv), 1)
            (run_a / "cases/answer/result.json").unlink()
            self.assertEqual(evaluator.main(argv), 2)


if __name__ == "__main__":
    unittest.main()
