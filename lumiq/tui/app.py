from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from ..api import LumiqApi
from .detail import StrategyDetailScreen
from .dialogs import ConfirmLiveDialog, ParametersDialog, StartDialog
from .logs import LogsScreen
from .parameter_history import ParameterHistoryScreen


ACTIVE_STATUSES = {"starting", "running"}


class StrategyTable(DataTable):
    def action_select_cursor(self) -> None:
        self.app.action_details()


class LumiqTui(App[None]):
    """Operational interface for strategies managed by Lumiq."""

    TITLE = "LumiQ"
    SUB_TITLE = "Trading Laboratory"
    CSS = """
    Screen {
        background: #101417;
        color: #e7ecef;
    }

    Header {
        background: #162127;
        color: #ffffff;
    }

    #workspace {
        height: 1fr;
        padding: 1 2;
    }

    #system-status {
        height: 2;
        padding: 0 1;
        color: #b9c6cc;
        background: #162127;
    }

    #section-title {
        height: 2;
        color: #79d6c9;
        text-style: bold;
    }

    #strategies {
        height: 1fr;
        border: solid #31434b;
        background: #131b1f;
    }

    #strategies:focus {
        border: solid #79d6c9;
    }

    #detail {
        height: 4;
        margin-top: 1;
        padding: 1;
        border-left: thick #79d6c9;
        background: #162127;
    }

    #actions {
        height: 3;
        margin-top: 1;
    }

    #actions Button {
        margin-right: 1;
        min-width: 14;
    }

    #message {
        height: 2;
        color: #b9c6cc;
        padding-left: 1;
    }

    .error {
        color: #ff8a80;
    }

    .healthy {
        color: #79d6c9;
    }
    """

    BINDINGS = [
        ("enter", "details", "Details"),
        ("r", "start_paper", "Run"),
        ("s", "stop_run", "Stop"),
        ("x", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, api: LumiqApi | None = None):
        super().__init__()
        self.api = api or LumiqApi()
        self.strategies: list[dict[str, Any]] = []
        self.runs_by_strategy: dict[str, dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="workspace"):
            yield Static("System: loading runtime state...", id="system-status")
            yield Static("STRATEGIES", id="section-title")
            yield StrategyTable(id="strategies", cursor_type="row", zebra_stripes=True)
            yield Static("Selecciona una estrategia.", id="detail")
            with Horizontal(id="actions"):
                yield Button("Run", id="start", variant="success")
                yield Button("Stop", id="stop", variant="error", disabled=True)
                yield Button("Refresh", id="refresh")
            yield Static("Cargando estado...", id="message")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#strategies", DataTable)
        table.add_column("Strategy", key="strategy")
        table.add_column("Mode", width=10, key="mode")
        table.add_column("Status", width=14, key="status")
        table.focus()
        self.set_interval(3, self.refresh_data)
        self.refresh_data()

    def selected_strategy_id(self) -> str | None:
        table = self.query_one("#strategies", DataTable)
        if not self.strategies or table.row_count == 0:
            return None
        return str(table.get_row_at(table.cursor_row)[0])

    def show_message(self, message: str, is_error: bool = False) -> None:
        widget = self.query_one("#message", Static)
        widget.set_class(is_error, "error")
        widget.update(message)

    @staticmethod
    def display_status(run: dict[str, Any] | None) -> str:
        if run is None or run.get("status") == "stopped":
            return "Stopped"
        status = str(run.get("status", "unknown")).lower()
        return {
            "starting": "Starting",
            "running": "Running",
            "failed": "Error",
            "error": "Error",
        }.get(status, status.title())

    @staticmethod
    def display_mode(run: dict[str, Any] | None) -> str:
        if run is None or run.get("status") == "stopped":
            return "-"
        return str(run.get("mode", "-")).title()

    def update_system_status(self) -> None:
        active_runs = [run for run in self.runs_by_strategy.values() if run.get("status") in ACTIVE_STATUSES]
        widget = self.query_one("#system-status", Static)
        widget.set_class(bool(active_runs), "healthy")
        if active_runs:
            modes = ", ".join(sorted({str(run["mode"]).title() for run in active_runs}))
            label = "strategy" if len(active_runs) == 1 else "strategies"
            widget.update(f"System: operational | {len(active_runs)} active {label} | {modes}")
        else:
            widget.update("System: idle | no active strategies")

    def apply_snapshot(self, strategies_response: dict, status_response: dict) -> None:
        if strategies_response.get("status") == "error":
            self.show_message(strategies_response["error"]["message"], True)
            return
        if status_response.get("status") == "error":
            self.show_message(status_response["error"]["message"], True)
            return

        self.strategies = strategies_response.get("strategies", [])
        self.runs_by_strategy = {}
        for run in reversed(status_response.get("runs", [])):
            self.runs_by_strategy[run["strategy_id"]] = run

        table = self.query_one("#strategies", DataTable)
        selected_id = self.selected_strategy_id()
        table.clear(columns=False)
        selected_row = 0
        for index, strategy in enumerate(self.strategies):
            strategy_id = strategy["id"]
            run = self.runs_by_strategy.get(strategy_id)
            table.add_row(
                strategy_id,
                self.display_mode(run),
                self.display_status(run),
                key=strategy_id,
            )
            if strategy_id == selected_id:
                selected_row = index
        if table.row_count:
            table.move_cursor(row=selected_row)
        self.update_detail()
        self.update_system_status()
        self.show_message(f"{len(self.strategies)} estrategias · {len(status_response.get('runs', []))} ejecuciones registradas")

    def update_detail(self) -> None:
        strategy_id = self.selected_strategy_id()
        detail = self.query_one("#detail", Static)
        stop_button = self.query_one("#stop", Button)
        start_button = self.query_one("#start", Button)
        if strategy_id is None:
            detail.update("No hay estrategias disponibles.")
            stop_button.disabled = True
            start_button.disabled = True
            return
        run = self.runs_by_strategy.get(strategy_id)
        is_active = bool(run and run.get("status") in ACTIVE_STATUSES)
        start_button.disabled = is_active
        stop_button.disabled = not is_active
        if run:
            detail.update(
                f"[b]{strategy_id}[/b]\n"
                f"Mode: {self.display_mode(run)}   Status: {self.display_status(run)}   Broker: {run['broker']}\n"
                f"Run: {run['run_id']}   Started: {run.get('started_at') or '-'}"
            )
        else:
            detail.update(f"[b]{strategy_id}[/b]\nStatus: Stopped\nReady to run in paper mode.")

    @work(exclusive=True, group="refresh")
    async def refresh_data(self) -> None:
        strategies_response, status_response = await asyncio.gather(
            asyncio.to_thread(self.api.list_strategies),
            asyncio.to_thread(self.api.status),
        )
        self.apply_snapshot(strategies_response, status_response)

    @work(exclusive=True, group="operation")
    async def start_with_parameters(
        self, strategy_id: str, mode: str, parameters: dict[str, Any], confirm_live: bool = False
    ) -> None:
        if strategy_id not in {strategy["id"] for strategy in self.strategies}:
            return
        self.show_message(f"Iniciando {strategy_id} en {mode}...")
        response = await asyncio.to_thread(self.api.start_strategy, strategy_id, mode, parameters, confirm_live)
        if response.get("status") == "error":
            self.show_message(response["error"]["message"], True)
            return
        self.show_message(f"{strategy_id} iniciado.")
        self.refresh_data()

    @work(exclusive=True, group="operation")
    async def stop_strategy(self, strategy_id: str) -> None:
        run = self.runs_by_strategy.get(strategy_id or "")
        if not run or run.get("status") not in ACTIVE_STATUSES:
            self.show_message("La estrategia seleccionada no está activa.", True)
            return
        self.show_message(f"Deteniendo {strategy_id}...")
        response = await asyncio.to_thread(self.api.stop_run, run["run_id"])
        if response.get("status") == "error":
            self.show_message(response["error"]["message"], True)
            return
        self.show_message(f"{strategy_id} detenida.")
        self.refresh_data()

    def on_data_table_row_highlighted(self, _event: DataTable.RowHighlighted) -> None:
        self.update_detail()

    def on_data_table_row_selected(self, _event: DataTable.RowSelected) -> None:
        self.action_details()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.action_start_paper()
        elif event.button.id == "stop":
            self.action_stop_run()
        elif event.button.id == "refresh":
            self.refresh_data()

    def strategy_for(self, strategy_id: str) -> dict[str, Any] | None:
        return next((strategy for strategy in self.strategies if strategy["id"] == strategy_id), None)

    def open_start_dialog(self, strategy_id: str, default_mode: str = "paper") -> None:
        strategy = self.strategy_for(strategy_id)
        if strategy:
            self.push_screen(StartDialog(strategy, default_mode), self.on_start_dialog_closed)

    def open_parameter_dialog(self, strategy_id: str) -> None:
        strategy = self.strategy_for(strategy_id)
        if strategy:
            self.push_screen(ParametersDialog(strategy), self.on_parameters_dialog_closed)

    def on_parameters_dialog_closed(self, result: dict[str, Any] | None) -> None:
        if result:
            self.save_parameters(result["strategy_id"], result["parameters"])

    @work(exclusive=True, group="operation")
    async def save_parameters(self, strategy_id: str, parameters: dict[str, Any]) -> None:
        response = await asyncio.to_thread(self.api.update_parameters, strategy_id, parameters, "human")
        if response.get("status") == "error":
            self.show_message(response["error"]["message"], True)
            return
        self.show_message(f"Parameters saved for {strategy_id}.")
        self.refresh_data()

    def open_parameter_history(self, strategy_id: str) -> None:
        self.push_screen(ParameterHistoryScreen(self.api, strategy_id))

    def on_start_dialog_closed(self, result: dict[str, Any] | None) -> None:
        if not result:
            return
        if result["mode"] == "live":
            self.push_screen(
                ConfirmLiveDialog(result["strategy_id"]),
                lambda confirmed: self.on_live_confirmation_closed(result, confirmed),
            )
            return
        self.start_with_parameters(result["strategy_id"], result["mode"], result["parameters"])

    def on_live_confirmation_closed(self, result: dict[str, Any], confirmed: bool) -> None:
        if confirmed:
            self.start_with_parameters(result["strategy_id"], "live", result["parameters"], True)
        else:
            self.show_message("Live launch cancelled.")

    def open_logs(self, run_id: str) -> None:
        self.push_screen(LogsScreen(self.api, run_id))

    def open_source(self, module: str) -> None:
        editor = os.environ.get("EDITOR")
        if not editor:
            self.show_message("Define $EDITOR para abrir el archivo fuente.", True)
            return
        with self.suspend():
            subprocess.run([*shlex.split(editor), module], check=False)
        self.show_message(f"Editor cerrado: {module}")

    def action_details(self) -> None:
        strategy_id = self.selected_strategy_id()
        strategy = self.strategy_for(strategy_id or "")
        if strategy:
            self.push_screen(StrategyDetailScreen(strategy, self.runs_by_strategy.get(strategy_id or "")))

    def action_start_paper(self) -> None:
        strategy_id = self.selected_strategy_id()
        if strategy_id:
            self.open_start_dialog(strategy_id)

    def action_start_live(self) -> None:
        strategy_id = self.selected_strategy_id()
        if strategy_id:
            self.open_start_dialog(strategy_id, "live")

    def action_edit_parameters(self) -> None:
        strategy_id = self.selected_strategy_id()
        if strategy_id:
            self.open_parameter_dialog(strategy_id)

    def action_parameter_history(self) -> None:
        strategy_id = self.selected_strategy_id()
        if strategy_id:
            self.open_parameter_history(strategy_id)

    def action_stop_run(self) -> None:
        strategy_id = self.selected_strategy_id()
        if strategy_id:
            self.stop_strategy(strategy_id)

    def action_logs(self) -> None:
        run = self.runs_by_strategy.get(self.selected_strategy_id() or "")
        if run:
            self.open_logs(run["run_id"])

    def action_source(self) -> None:
        strategy = self.strategy_for(self.selected_strategy_id() or "")
        if strategy:
            self.open_source(strategy["module"])

    def action_refresh(self) -> None:
        self.refresh_data()


def run() -> None:
    LumiqTui().run()