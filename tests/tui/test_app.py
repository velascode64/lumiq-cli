from __future__ import annotations

import unittest

from textual.widgets import Button, DataTable, Select, Static

from lumiq.tui.app import LumiqTui


class FakeApi:
    def __init__(self):
        self.run = None

    def list_strategies(self):
        return {
            "status": "success",
            "strategies": [
                {
                    "id": "paper_test_strategy",
                    "class": "PaperTestStrategy",
                    "module": "strategies/live/paper_test_strategy.py",
                    "parameters": {},
                }
            ],
        }

    def status(self):
        return {"status": "success", "runs": [self.run] if self.run else []}

    def start_strategy(self, strategy_id, mode, parameters, confirm_live=False):
        if mode == "live" and not confirm_live:
            return {"status": "error", "error": {"message": "Live confirmation is required."}}
        self.run = {
            "run_id": "run-001",
            "strategy_id": strategy_id,
            "mode": mode,
            "status": "running",
            "broker": "alpaca",
            "started_at": "2026-09-22T12:00:00+00:00",
            "parameters": parameters,
        }
        return {"status": "success", "run": self.run}

    def stop_run(self, run_id):
        self.run = {**self.run, "status": "stopped"}
        return {"status": "success", "run": self.run}

    def logs(self, run_id, lines=100):
        return {"status": "success", "run_id": run_id, "logs": "Paper strategy started\n"}


class LumiqTuiTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_and_stop_selected_strategy(self):
        api = FakeApi()
        app = LumiqTui(api=api)

        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.pause()
            table = app.query_one("#strategies", DataTable)
            self.assertEqual(table.get_row_at(0), ["paper_test_strategy", "-", "Stopped"])

            await pilot.click("#start")
            await pilot.pause()
            self.assertEqual(app.screen.query_one("#mode-select", Select).value, "paper")
            app.screen.query_one("#confirm-start", Button).press()
            await pilot.pause()
            self.assertEqual(api.run["status"], "running")
            self.assertEqual(table.get_row_at(0)[1:], ["Paper", "Running"])
            self.assertIn("1 active strategy | Paper", str(app.query_one("#system-status", Static).render()))
            self.assertFalse(app.query_one("#stop", Button).disabled)

            await pilot.click("#stop")
            await pilot.pause()
            self.assertEqual(api.run["status"], "stopped")
            self.assertEqual(table.get_row_at(0)[2:], ["Stopped"])
            self.assertIn("System: idle", str(app.query_one("#system-status", Static).render()))
            self.assertTrue(app.query_one("#stop", Button).disabled)

    async def test_live_run_requires_confirmation(self):
        api = FakeApi()
        app = LumiqTui(api=api)

        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            app.screen.action_run()
            await pilot.pause()
            mode_select = app.screen.query_one("#mode-select", Select)
            self.assertEqual(mode_select.value, "paper")
            mode_select.value = "live"

            app.screen.query_one("#confirm-start", Button).press()
            await pilot.pause()
            self.assertIsNone(api.run)
            self.assertIsNotNone(app.screen.query_one("#confirm-live-dialog"))

            app.screen.query_one("#confirm-live", Button).press()
            await pilot.pause()
            self.assertEqual(api.run["mode"], "live")

    async def test_detail_and_logs_navigation(self):
        api = FakeApi()
        api.start_strategy("paper_test_strategy", "paper", {})
        app = LumiqTui(api=api)

        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.pause(0.2)
            table = app.query_one("#strategies", DataTable)
            self.assertEqual(table.row_count, 1)
            table.focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsNotNone(app.screen.query_one("#runtime-detail"))
            app.screen.action_logs()
            await pilot.pause()
            self.assertIsNotNone(app.screen.query_one("#run-logs"))
            await pilot.press("escape")


if __name__ == "__main__":
    unittest.main()