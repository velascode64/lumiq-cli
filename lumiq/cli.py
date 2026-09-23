from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv

from .registry import discover, resolve
from .supervisor import Supervisor

app = typer.Typer(no_args_is_help=True, add_completion=False)
strategies_app = typer.Typer(no_args_is_help=True)
strategy_app = typer.Typer(no_args_is_help=True)
app.add_typer(strategies_app, name="strategies")
app.add_typer(strategy_app, name="strategy")

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(Path(__file__).with_name(".env"), override=False)
load_dotenv(ROOT / ".env", override=False)


def _supervisor() -> Supervisor:
    return Supervisor(ROOT, Path(os.environ.get("LUMIQ_STATE_DIR", "~/.lumiq")))


def _emit(value: Any, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(value, default=str, sort_keys=True))
    elif isinstance(value, list):
        for item in value:
            typer.echo("  ".join(f"{key}={val}" for key, val in item.items()))
    elif isinstance(value, dict):
        for key, item in value.items():
            typer.echo(f"{key}: {item}")
    else:
        typer.echo(value)


def _error(code: str, message: str, as_json: bool) -> None:
    payload = {"status": "error", "error": {"code": code, "message": message}}
    if as_json:
        typer.echo(json.dumps(payload, sort_keys=True))
    else:
        typer.echo(f"Error: {message}", err=True)
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


def _strategy_payload(root: Path) -> list[dict[str, Any]]:
    return [{"id": item["id"], "class": item["class"], "module": item["module"],
             "parameters": item["parameters"]} for item in discover(root)]


@strategies_app.command("list")
def strategies_list(json_output: bool = typer.Option(False, "--json")):
    try:
        _emit({"status": "success", "strategies": _strategy_payload(ROOT)} if json_output else _strategy_payload(ROOT), json_output)
    except typer.Exit:
        raise
    except Exception as exc:
        _error("DISCOVERY_FAILED", str(exc), json_output)


@strategy_app.command("show")
def strategy_show(strategy_id: str, json_output: bool = typer.Option(False, "--json")):
    try:
        item = resolve(ROOT / "strategies", strategy_id)
        _emit({"status": "success", "strategy": item} if json_output else item, json_output)
    except typer.Exit:
        raise
    except KeyError:
        _error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.", json_output)
    except Exception as exc:
        _error("DISCOVERY_FAILED", str(exc), json_output)


@app.command("discover")
def discover_command(json_output: bool = typer.Option(False, "--json")):
    strategies_list(json_output)


@app.command("show")
def show_command(strategy_id: str, json_output: bool = typer.Option(False, "--json")):
    strategy_show(strategy_id, json_output)


def _start(strategy_id: str, mode: str, sets: list[str], json_output: bool, confirm_live: bool):
    if mode == "live" and not confirm_live:
        _error("LIVE_CONFIRMATION_REQUIRED", "Live mode requires --confirm-live.", json_output)
    configured_paper = os.environ.get("ALPACA_IS_PAPER")
    if configured_paper is not None:
        configured_paper = configured_paper.strip().lower() in {"1", "true", "yes", "on"}
        if mode == "live" and configured_paper:
            _error("BROKER_MODE_MISMATCH", "ALPACA_IS_PAPER is enabled, so live mode is unavailable.", json_output)
        if mode == "paper" and not configured_paper:
            _error("BROKER_MODE_MISMATCH", "ALPACA_IS_PAPER is disabled, so paper mode is unavailable.", json_output)
    if mode == "live" and "paper-api.alpaca.markets" in os.environ.get("ALPACA_BASE_URL", "").lower():
        _error("BROKER_MODE_MISMATCH", "ALPACA_BASE_URL points to the paper endpoint; live mode is unavailable.", json_output)
    try:
        parameters = _parse_sets(sets)
        if not os.environ.get("ALPACA_API_KEY") and not os.environ.get("ALPACA_OAUTH_TOKEN"):
            _error("MISSING_ALPACA_CREDENTIALS", "Set ALPACA_API_KEY and ALPACA_API_SECRET (or ALPACA_OAUTH_TOKEN).", json_output)
        if os.environ.get("ALPACA_API_KEY") and not os.environ.get("ALPACA_API_SECRET"):
            _error("MISSING_ALPACA_SECRET", "ALPACA_API_SECRET is required with ALPACA_API_KEY.", json_output)
        result = _supervisor().start(strategy_id, mode, parameters, {})
        _emit({"status": "success", "run": result} if json_output else result, json_output)
    except typer.Exit:
        raise
    except KeyError:
        _error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.", json_output)
    except ValueError as exc:
        _error("INVALID_PARAMETER", str(exc), json_output)
    except RuntimeError as exc:
        _error("RUN_ALREADY_ACTIVE", str(exc), json_output)
    except Exception as exc:
        _error("START_FAILED", str(exc), json_output)


@app.command("start")
def start_command(strategy_id: str, mode: str = typer.Option("paper", "--mode"), sets: list[str] = typer.Option([], "--set"),
                   json_output: bool = typer.Option(False, "--json"), confirm_live: bool = typer.Option(False, "--confirm-live")):
    if mode not in {"paper", "live"}:
        _error("INVALID_MODE", "Mode must be paper or live.", json_output)
    _start(strategy_id, mode, sets, json_output, confirm_live)


@app.command("run")
def run_command(strategy_id: str, paper: bool = typer.Option(False, "--paper"), live: bool = typer.Option(False, "--live"),
                sets: list[str] = typer.Option([], "--set"), json_output: bool = typer.Option(False, "--json"),
                confirm_live: bool = typer.Option(False, "--confirm-live")):
    if paper == live:
        _error("INVALID_MODE", "Choose exactly one of --paper or --live.", json_output)
    _start(strategy_id, "live" if live else "paper", sets, json_output, confirm_live)


@app.command("stop")
def stop_command(run_id: str, json_output: bool = typer.Option(False, "--json")):
    try:
        result = _supervisor().stop(run_id)
        _emit({"status": "success", "run": result} if json_output else result, json_output)
    except KeyError:
        _error("RUN_NOT_FOUND", f"Run {run_id!r} was not found.", json_output)


@app.command("status")
def status_command(run_id: str | None = typer.Argument(None), json_output: bool = typer.Option(False, "--json")):
    result = _supervisor().status(run_id)
    if not json_output and not result:
        typer.echo("No hay ejecuciones registradas.")
        return
    _emit({"status": "success", "runs": result} if json_output else result, json_output)


@app.command("logs")
def logs_command(run_id: str, lines: int = typer.Option(100, "--lines"), json_output: bool = typer.Option(False, "--json")):
    try:
        result = _supervisor().logs_for(run_id, lines)
        _emit({"status": "success", "run_id": run_id, "logs": result} if json_output else result, json_output)
    except KeyError:
        _error("RUN_NOT_FOUND", f"Run {run_id!r} was not found.", json_output)


@app.command("resume")
def resume_command(run_id: str, json_output: bool = typer.Option(False, "--json"), confirm_live: bool = typer.Option(False, "--confirm-live")):
    try:
        row = _supervisor().store.get(run_id)
        if row is None:
            raise KeyError(run_id)
        _start(row["strategy_id"], row["mode"], [f"{key}={json.dumps(value)}" for key, value in json.loads(row["parameters"]).items()], json_output, confirm_live or row["mode"] == "paper")
    except KeyError:
        _error("RUN_NOT_FOUND", f"Run {run_id!r} was not found.", json_output)


@app.command("backtest")
def backtest_command(strategy_id: str, sets: list[str] = typer.Option([], "--set"), json_output: bool = typer.Option(False, "--json")):
    _error("NOT_IMPLEMENTED", "Backtest delegation is not implemented yet; use LumiBot directly for now.", json_output)


def main() -> None:
    app()
