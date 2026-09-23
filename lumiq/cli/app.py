from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv

from ..api import LumiqApi
from ..output.console import lines
from ..output.json import dumps

app = typer.Typer(no_args_is_help=True, add_completion=False)
strategies_app = typer.Typer(no_args_is_help=True)
strategy_app = typer.Typer(no_args_is_help=True)
app.add_typer(strategies_app, name="strategies")
app.add_typer(strategy_app, name="strategy")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "lumiq"
load_dotenv(PACKAGE_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _api() -> LumiqApi:
    return LumiqApi(PROJECT_ROOT)


def _render(response: dict[str, Any], as_json: bool) -> None:
    if as_json:
        typer.echo(dumps(response))
    else:
        for line in lines(response):
            typer.echo(line, err=response.get("status") == "error")
    if response.get("status") == "error":
        raise typer.Exit(code=2)


def _parse_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _parse_sets(values: list[str]) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError("Parameter key cannot be empty")
        parameters[key] = _parse_value(value)
    return parameters


def _parameters(values: list[str], as_json: bool) -> dict[str, Any]:
    try:
        return _parse_sets(values)
    except ValueError as exc:
        _render({"status": "error", "error": {"code": "INVALID_PARAMETER", "message": str(exc)}}, as_json)
        return {}


@strategies_app.command("list")
def strategies_list(json_output: bool = typer.Option(False, "--json")):
    _render(_api().list_strategies(), json_output)


@strategy_app.command("show")
def strategy_show(strategy_id: str, json_output: bool = typer.Option(False, "--json")):
    _render(_api().show_strategy(strategy_id), json_output)


@strategy_app.command("history")
def strategy_history(strategy_id: str, json_output: bool = typer.Option(False, "--json")):
    _render(_api().parameter_history(strategy_id), json_output)


@strategy_app.command("configure")
def strategy_configure(
    strategy_id: str,
    sets: list[str] = typer.Option([], "--set"),
    source: str = typer.Option("agent", "--source"),
    json_output: bool = typer.Option(False, "--json"),
):
    _render(_api().update_parameters(strategy_id, _parameters(sets, json_output), source), json_output)


@app.command("discover")
def discover_command(json_output: bool = typer.Option(False, "--json")):
    _render(_api().list_strategies(), json_output)


@app.command("show")
def show_command(strategy_id: str, json_output: bool = typer.Option(False, "--json")):
    _render(_api().show_strategy(strategy_id), json_output)


@app.command("start")
def start_command(
    strategy_id: str,
    mode: str = typer.Option("paper", "--mode"),
    sets: list[str] = typer.Option([], "--set"),
    json_output: bool = typer.Option(False, "--json"),
    confirm_live: bool = typer.Option(False, "--confirm-live"),
):
    _render(_api().start_strategy(strategy_id, mode, _parameters(sets, json_output), confirm_live), json_output)


@app.command("run")
def run_command(
    strategy_id: str,
    paper: bool = typer.Option(False, "--paper"),
    live: bool = typer.Option(False, "--live"),
    sets: list[str] = typer.Option([], "--set"),
    json_output: bool = typer.Option(False, "--json"),
    confirm_live: bool = typer.Option(False, "--confirm-live"),
):
    if paper == live:
        _render({"status": "error", "error": {"code": "INVALID_MODE", "message": "Choose exactly one of --paper or --live."}}, json_output)
        return
    _render(_api().start_strategy(strategy_id, "live" if live else "paper", _parameters(sets, json_output), confirm_live), json_output)


@app.command("stop")
def stop_command(run_id: str, json_output: bool = typer.Option(False, "--json")):
    _render(_api().stop_run(run_id), json_output)


@app.command("status")
def status_command(run_id: str | None = typer.Argument(None), json_output: bool = typer.Option(False, "--json")):
    _render(_api().status(run_id), json_output)


@app.command("logs")
def logs_command(run_id: str, lines_count: int = typer.Option(100, "--lines"), json_output: bool = typer.Option(False, "--json")):
    _render(_api().logs(run_id, lines_count), json_output)


@app.command("resume")
def resume_command(
    run_id: str,
    json_output: bool = typer.Option(False, "--json"),
    confirm_live: bool = typer.Option(False, "--confirm-live"),
):
    _render(_api().resume_run(run_id, confirm_live), json_output)


@app.command("backtest")
def backtest_command(strategy_id: str, sets: list[str] = typer.Option([], "--set"), json_output: bool = typer.Option(False, "--json")):
    _render(_api().backtest(strategy_id, _parameters(sets, json_output)), json_output)


def main() -> None:
    app()