from __future__ import annotations

import asyncio

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, RichLog, Select, Static

from ..api import LumiqApi


class LogsScreen(Screen):
    """Read-only log viewer backed by Lumiq's existing run logs."""

    CSS = """
    LogsScreen {
        background: #101417;
        color: #e7ecef;
    }

    #logs-workspace {
        padding: 1 2;
    }

    #logs-title {
        height: 2;
        color: #79d6c9;
        text-style: bold;
    }

    #run-logs {
        height: 1fr;
        border: solid #31434b;
        background: #0c1114;
    }

    #logs-actions {
        height: 3;
        margin-top: 1;
    }

    #logs-actions Button {
        margin-right: 1;
    }

    #logs-filters {
        height: 3;
    }

    #log-filter {
        width: 1fr;
        margin-right: 1;
    }

    #log-level, #log-lines {
        width: 14;
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("space", "toggle_follow", "Pause/resume"),
        ("c", "clear_view", "Clear view"),
    ]

    def __init__(self, api: LumiqApi, run_id: str):
        super().__init__()
        self.api = api
        self.run_id = run_id
        self.following = True
        self.line_count = 50

    def compose(self) -> ComposeResult:
        with Vertical(id="logs-workspace"):
            yield Static(f"LOGS · {self.run_id}", id="logs-title")
            with Horizontal(id="logs-filters"):
                yield Input(placeholder="Filter logs", id="log-filter")
                yield Select([("All levels", "all"), ("INFO", "info"), ("WARNING", "warning"), ("ERROR", "error")], value="all", id="log-level")
                yield Select([("Last 50", "50"), ("Last 100", "100"), ("Last 250", "250"), ("Last 500", "500")], value="50", id="log-lines")
            yield RichLog(id="run-logs", wrap=True, markup=False, highlight=True)
            with Horizontal(id="logs-actions"):
                yield Button("Pause", id="toggle-follow")
                yield Button("Clear view", id="clear-view")
                yield Button("Back", id="logs-back")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(2, self.refresh_logs)
        self.refresh_logs()

    @work(exclusive=True, group="logs")
    async def refresh_logs(self) -> None:
        if not self.following:
            return
        response = await asyncio.to_thread(self.api.logs, self.run_id, self.line_count)
        log = self.query_one("#run-logs", RichLog)
        log.clear()
        if response.get("status") == "error":
            log.clear()
            log.write(f"Error: {response['error']['message']}")
            return
        content = response.get("logs", "")
        if not content:
            log.write("No log output yet.")
            return
        filter_text = self.query_one("#log-filter", Input).value.lower()
        level = self.query_one("#log-level", Select).value
        lines = [line for line in content.splitlines() if (not filter_text or filter_text in line.lower())]
        if level != "all":
            lines = [line for line in lines if str(level).upper() in line.upper()]
        log.write("\n".join(lines) if lines else "No matching log lines.", scroll_end=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle-follow":
            self.action_toggle_follow()
        elif event.button.id == "clear-view":
            self.action_clear_view()
        elif event.button.id == "logs-back":
            self.action_back()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "log-filter":
            self.refresh_logs()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "log-lines":
            self.line_count = int(str(event.value))
        if event.select.id in {"log-level", "log-lines"}:
            self.refresh_logs()

    def action_toggle_follow(self) -> None:
        self.following = not self.following
        self.query_one("#toggle-follow", Button).label = "Pause" if self.following else "Resume"
        if self.following:
            self.refresh_logs()

    def action_clear_view(self) -> None:
        self.query_one("#run-logs", RichLog).clear()

    def action_back(self) -> None:
        self.app.pop_screen()