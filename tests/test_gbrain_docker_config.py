from __future__ import annotations

import unittest
from pathlib import Path


COMPOSE = Path("/Users/jm/.hermes-team2/docker-compose.yml")


class GBrainDockerConfigTests(unittest.TestCase):
    def test_gbrain_serves_vault_source_by_default(self) -> None:
        compose = COMPOSE.read_text(encoding="utf-8")

        self.assertIn("GBRAIN_SOURCE: team2-vault", compose)


if __name__ == "__main__":
    unittest.main()
