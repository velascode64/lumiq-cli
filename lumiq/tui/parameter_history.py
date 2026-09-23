from __future__ import annotations

import asyncio
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from ..api import LumiqApi


class ParameterHistoryScreen(Screen):
    """Read-only operational history for one strategy's configuration."""

    CSS = """
    ParameterHistoryScreen {
        background: #101417;
        color: #e7ecef;
    }

    #history-workspace {
        height: 1fr;
        padding: 1 2;
    }

    #history-title {
        height: 2;
        color: #79d6c9;
        text-style: bold;
    }

    #parameter-history {
        height: 1fr;
        border: solid #31434b;
        background: #131b1f;
    }
    """

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, api: LumiqApi, strategy_id: str):
        super().__init__()
        self.api = api
        self.strategy_id = strategy_id

    def compose(self) -> ComposeResult:
        with Vertical(id="history-workspace"):
            yield Static(f"PARAMETER HISTORY · {self.strategy_id}", id="history-title")
            yield DataTable(id="parameter-history", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#parameter-history", DataTable)
        table.add_columns("Time", "Parameter", "Previous", "New", "Source")
        self.load_history()

    @work(exclusive=True)
    async def load_history(self) -> None:
        response = await asyncio.to_thread(self.api.parameter_history, self.strategy_id)
        table = self.query_one("#parameter-history", DataTable)
        table.clear(columns=False)
        if response.get("status") == "error":
            table.add_row("-", "Error", response["error"]["message"], "-", "-")
            return
        for item in response.get("history", []):
            table.add_row(
                item["timestamp"],
                item["parameter"],
                repr(item["previous_value"]),
                repr(item["new_value"]),
                item["source"],
            )
        if not table.row_count:
            table.add_row("-", "No parameter changes", "-", "-", "-")

    def action_back(self) -> None:
        self.app.pop_screen()
