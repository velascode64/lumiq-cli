from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..infrastructure.supervisor import Supervisor
from .responses import error, success


class RuntimeService:
    def __init__(self, project_root: Path, state_dir: Path):
        self.supervisor = Supervisor(project_root, state_dir)

    def start(self, strategy_id: str, mode: str, parameters: dict[str, Any], confirm_live: bool = False) -> dict:
        validation = self._validate_start(mode, confirm_live)
        if validation is not None:
            return validation
        try:
            return success(run=self.supervisor.start(strategy_id, mode, parameters, {}))
        except KeyError:
            return error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.")
        except RuntimeError as exc:
            return error("RUN_ALREADY_ACTIVE", str(exc))
        except Exception as exc:
            return error("START_FAILED", str(exc))

    def stop(self, run_id: str) -> dict:
        try:
            return success(run=self.supervisor.stop(run_id))
        except KeyError:
            return error("RUN_NOT_FOUND", f"Run {run_id!r} was not found.")

    def status(self, run_id: str | None = None) -> dict:
        return success(runs=self.supervisor.status(run_id))

    def logs(self, run_id: str, lines: int = 100) -> dict:
        try:
            return success(run_id=run_id, logs=self.supervisor.logs_for(run_id, lines))
        except KeyError:
            return error("RUN_NOT_FOUND", f"Run {run_id!r} was not found.")

    def resume(self, run_id: str, confirm_live: bool = False) -> dict:
        row = self.supervisor.store.get(run_id)
        if row is None:
            return error("RUN_NOT_FOUND", f"Run {run_id!r} was not found.")
        return self.start(
            row["strategy_id"],
            row["mode"],
            json.loads(row["parameters"]),
            confirm_live or row["mode"] == "paper",
        )

    def _validate_start(self, mode: str, confirm_live: bool) -> dict | None:
        if mode not in {"paper", "live"}:
            return error("INVALID_MODE", "Mode must be paper or live.")
        if mode == "live" and not confirm_live:
            return error("LIVE_CONFIRMATION_REQUIRED", "Live mode requires --confirm-live.")
        configured_paper = os.environ.get("ALPACA_IS_PAPER")
        if configured_paper is not None:
            is_paper = configured_paper.strip().lower() in {"1", "true", "yes", "on"}
            if mode == "live" and is_paper:
                return error("BROKER_MODE_MISMATCH", "ALPACA_IS_PAPER is enabled, so live mode is unavailable.")
            if mode == "paper" and not is_paper:
                return error("BROKER_MODE_MISMATCH", "ALPACA_IS_PAPER is disabled, so paper mode is unavailable.")
        if mode == "live" and "paper-api.alpaca.markets" in os.environ.get("ALPACA_BASE_URL", "").lower():
            return error("BROKER_MODE_MISMATCH", "ALPACA_BASE_URL points to the paper endpoint; live mode is unavailable.")
        if not os.environ.get("ALPACA_API_KEY") and not os.environ.get("ALPACA_OAUTH_TOKEN"):
            return error("MISSING_ALPACA_CREDENTIALS", "Set ALPACA_API_KEY and ALPACA_API_SECRET (or ALPACA_OAUTH_TOKEN).")
        if os.environ.get("ALPACA_API_KEY") and not os.environ.get("ALPACA_API_SECRET"):
            return error("MISSING_ALPACA_SECRET", "ALPACA_API_SECRET is required with ALPACA_API_KEY.")
        return None