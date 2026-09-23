from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lumiq.api import LumiqApi


ROOT = Path(__file__).resolve().parents[2]


class LumiqApiTest(unittest.TestCase):
    def test_status_response_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as state_dir:
            response = LumiqApi(ROOT, state_dir).status()

        self.assertEqual(response, {"status": "success", "runs": []})
        json.dumps(response)

    def test_missing_run_is_structured_error(self):
        with tempfile.TemporaryDirectory() as state_dir:
            response = LumiqApi(ROOT, state_dir).stop_run("missing")

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["code"], "RUN_NOT_FOUND")

    def test_parameter_history_persists_human_changes(self):
        with tempfile.TemporaryDirectory() as state_dir:
            api = LumiqApi(ROOT, state_dir)
            strategy = api.list_strategies()["strategies"][0]
            if not strategy["parameters"]:
                self.skipTest("The discovered strategies have no configurable parameters.")
            key, value = next(iter(strategy["parameters"].items()))
            updated = api.update_parameters(strategy["id"], {key: value}, "human")
            self.assertEqual(updated["status"], "success")
            history = api.parameter_history(strategy["id"])
            self.assertEqual(history["status"], "success")


if __name__ == "__main__":
    unittest.main()