from __future__ import annotations

import unittest
from pathlib import Path


SCRIPT = Path("/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh")


class GBrainMaintenanceScriptTests(unittest.TestCase):
    def test_maintenance_runs_full_reinforcement_steps(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("docker run --rm -i", script)
        self.assertIn("clean_gbrain_lock", script)
        self.assertIn("run_gbrain_step sync", script)
        self.assertIn("sync --all --yes --no-pull", script)
        self.assertIn("run_gbrain_step extract", script)
        self.assertIn("extract --stale", script)
        self.assertIn("run_gbrain_step embed", script)
        self.assertIn("embed --stale", script)
        self.assertIn("run_gbrain_step dream-team2-harness", script)
        self.assertIn("dream --source team2-harness", script)
        self.assertIn("run_gbrain_step dream-team2-vault", script)
        self.assertIn("dream --source team2-vault", script)
        self.assertIn("gbrain doctor --json > /opt/data/gbrain-doctor-latest.json", script)
        self.assertIn('"steps": ${steps_json}', script)


if __name__ == "__main__":
    unittest.main()
