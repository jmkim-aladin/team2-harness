#!/usr/bin/env python3
"""Record a worked synthetic example; this does not run application code."""
from decimal import Decimal, ROUND_DOWN
import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def source(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data_path = ROOT.parent / "inputs/expectation-source/evidence.json"
    data = json.loads(data_path.read_text())
    policy = ROOT / "synthetic-policy-v1.txt"
    discounted_unit = Decimal(data["unit_price_won"]) * (100 - Decimal(data["discount_percent"])) / 100
    per_item = int(discounted_unit.quantize(Decimal("1"), rounding=ROUND_DOWN)) * data["quantity"]
    aggregate = int((discounted_unit * data["quantity"]).quantize(Decimal("1"), rounding=ROUND_DOWN))
    assert (per_item, aggregate) == (1700, 1701), "fixture changed; reassess the worked example"
    trace = {
        "schema_version": 1, "task_id": "TASK-20261104-4560e95349bc",
        "input": source(data_path), "synthetic_policy": source(policy),
        "synthetic_policy_version": "synthetic-discount-v1",
        "method": "hand-worked 1001*85/100=850.85 -> floor 850 -> times 2=1700, corroborated with Decimal",
        "python": sys.version, "verifier": source(Path(__file__)),
        "cases": [
            {"id": "original-policy-missing", "expected_amount_won": None,
             "source_status": "unverified", "observed_amount_won": data["implementation_output_won"],
             "existing_test_exit_code": data["test_exit_code"], "status": "INCONCLUSIVE",
             "reason": "source_documents is empty; 1700 and 1701 are possible under different policies"},
            {"id": "synthetic-policy-with-copied-expectation", "expected_amount_won": per_item,
             "source_status": "verified-synthetic-fixture", "observed_amount_won": data["implementation_output_won"],
             "status": "FAIL" if per_item != data["implementation_output_won"] else "PASS",
             "reason": "apply the separately supplied synthetic policy; the copied 1701 test value is not its oracle"},
            {"id": "known-worked-example", "expected_amount_won": per_item,
             "source_status": "verified-synthetic-fixture", "observed_amount_won": 1700,
             "status": "PASS" if per_item == 1700 else "FAIL",
             "reason": "a known-correct literal supplied for this worked example; not an application output"},
        ],
        "limitations": ["No production policy or application execution was verified.",
                        "The original fixture remains unverified; the synthetic policy does not resolve its real-world policy."],
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(trace, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({x["id"]: x["status"] for x in trace["cases"]}))


if __name__ == "__main__":
    main()
