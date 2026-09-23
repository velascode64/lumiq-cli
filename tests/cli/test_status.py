from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StatusCommandTest(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        with tempfile.TemporaryDirectory() as state_dir:
            env["LUMIQ_STATE_DIR"] = state_dir
            return subprocess.run(
                [sys.executable, "-m", "lumiq", *arguments],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_empty_status_is_valid_json(self):
        result = self.run_cli("status", "--json")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {"runs": [], "status": "success"})

    def test_empty_status_is_visible_to_humans(self):
        result = self.run_cli("status")

        self.assertEqual(result.returncode, 0)
        self.assertIn("No hay ejecuciones registradas.", result.stdout)


if __name__ == "__main__":
    unittest.main()