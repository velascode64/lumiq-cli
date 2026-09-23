from __future__ import annotations

import asyncio
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, RichLog, Select, Static


ACTIVE_STATUSES = {"starting", "running"}


class StrategyDetailScreen(Screen):
    """Operational detail for one strategy."""

    CSS = """
    StrategyDetailScreen {
        background: #101417;
        color: #e7ecef;
    }

    #detail-workspace {
        padding: 2 4;
    }

    #detail-name {
        height: 3;
        text-style: bold;
        color: #79d6c9;
    }

    #runtime-detail, #parameter-detail, #source-detail {
        margin-bottom: 1;
        padding: 1 2;
        border-left: thick #31434b;
        background: #162127;
    }

    #detail-actions {
        height: 3;
    }

    #detail-actions Button {
        margin-right: 1;
    }

    #recent-logs {
        height: 8;
        margin-bottom: 1;
        border: solid #31434b;
        background: #0c1114;
    }

    #detail-log-filter {
        width: 1fr;
        margin-right: 1;
    }

    #detail-log-level {
        width: 14;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("r", "run", "Run"),
        ("s", "stop_run", "Stop"),
        ("e", "edit_parameters", "Edit params"),
        ("h", "parameter_history", "Param history"),
        ("l", "logs", "Logs"),
        ("o", "source", "Open source"),
    ]

    def __init__(self, strategy: dict[str, Any], run: dict[str, Any] | None):
        super().__init__()
        self.strategy = strategy
        self.run = run

    def compose(self) -> ComposeResult:
        run = self.run
        is_active = bool(run and run.get("status") in ACTIVE_STATUSES)
        runtime = (
            f"Status: {run['status']}\nMode: {run['mode']}   Broker: {run['broker']}\n"
            f"Run: {run['run_id']}\nStarted: {run.get('started_at') or '-'}"
            if run
            else "Status: stopped\nMode: -\nRun: -"
        )
        with Vertical(id="detail-workspace"):
            yield Static(self.strategy["id"], id="detail-name")
            yield Static(runtime, id="runtime-detail")
            yield Static(f"Parameters\n{self.strategy.get('parameters') or '{}'}", id="parameter-detail")
            yield Static(f"Source\n{self.strategy['module']}", id="source-detail")
            yield Static("RECENT LOGS · Last 50 lines")
            with Horizontal():
                yield Input(placeholder="Filter logs", id="detail-log-filter")
                yield Select([("All levels", "all"), ("INFO", "info"), ("WARNING", "warning"), ("ERROR", "error")], value="all", id="detail-log-level")
            yield RichLog(id="recent-logs", wrap=True, markup=False, highlight=True)
            with Horizontal(id="detail-actions"):
                yield Button("Run", id="detail-start", variant="success", disabled=is_active)
                yield Button("Stop", id="detail-stop", variant="error", disabled=not is_active)
                yield Button("Edit params", id="detail-edit")
                yield Button("Param history", id="detail-history")
                yield Button("Logs", id="detail-logs", disabled=run is None)
                yield Button("Open source", id="detail-source")
                yield Button("Back", id="detail-back")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_recent_logs()

    @work(exclusive=True, group="detail-logs")
    async def refresh_recent_logs(self) -> None:
        log = self.query_one("#recent-logs", RichLog)
        log.clear()
        if not self.run:
            log.write("No run logs yet.")
            return
        response = await asyncio.to_thread(self.app.api.logs, self.run["run_id"], 50)
        if response.get("status") == "error":
            log.write(f"Error: {response['error']['message']}")
            return
        filter_text = self.query_one("#detail-log-filter", Input).value.lower()
        level = self.query_one("#detail-log-level", Select).value
        lines = [line for line in response.get("logs", "").splitlines() if not filter_text or filter_text in line.lower()]
        if level != "all":
            lines = [line for line in lines if str(level).upper() in line.upper()]
        log.write("\n".join(lines) if lines else "No matching log lines.")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "detail-log-filter":
            self.refresh_recent_logs()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "detail-log-level":
            self.refresh_recent_logs()

    def return_to_main(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "detail-start": self.action_run,
            "detail-stop": self.action_stop_run,
            "detail-edit": self.action_edit_parameters,
            "detail-history": self.action_parameter_history,
            "detail-logs": self.action_logs,
            "detail-source": self.action_source,
            "detail-back": self.action_back,
        }
        action = actions.get(event.button.id)
        if action:
            action()

    def action_back(self) -> None:
        self.return_to_main()

    def action_run(self) -> None:
        self.return_to_main()
        self.app.open_start_dialog(self.strategy["id"])

    def action_stop_run(self) -> None:
        self.return_to_main()
        self.app.stop_strategy(self.strategy["id"])

    def action_edit_parameters(self) -> None:
        self.return_to_main()
        self.app.open_parameter_dialog(self.strategy["id"])

    def action_parameter_history(self) -> None:
        self.return_to_main()
        self.app.open_parameter_history(self.strategy["id"])

    def action_logs(self) -> None:
        if self.run:
            self.return_to_main()
            self.app.open_logs(self.run["run_id"])

    def action_source(self) -> None:
        self.return_to_main()
        self.app.open_source(self.strategy["module"])