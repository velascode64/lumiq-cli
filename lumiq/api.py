from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .services.responses import error
from .services.monitoring import MonitoringService
from .services.runtime import RuntimeService
from .services.strategies import StrategyService


class LumiqApi:
    """Stable application API shared by CLI, TUI, and future web adapters."""

    def __init__(self, project_root: Path | str | None = None, state_dir: Path | str | None = None):
        default_root = Path(os.environ.get("LUMIQ_PROJECT_ROOT", Path(__file__).resolve().parents[1]))
        self.project_root = Path(project_root or default_root).expanduser().resolve()
        resolved_state = Path(state_dir or os.environ.get("LUMIQ_STATE_DIR", "~/.lumiq"))
        self.strategies = StrategyService(self.project_root / "strategies", resolved_state)
        self.runtime = RuntimeService(self.project_root, resolved_state)
        self.monitoring = MonitoringService()

    def list_strategies(self) -> dict:
        return self.strategies.list()

    def show_strategy(self, strategy_id: str) -> dict:
        return self.strategies.show(strategy_id)

    def update_parameters(self, strategy_id: str, parameters: dict[str, Any], source: str = "human") -> dict:
        return self.strategies.update_parameters(strategy_id, parameters, source)

    def parameter_history(self, strategy_id: str) -> dict:
        return self.strategies.parameter_history(strategy_id)

    def start_strategy(self, strategy_id: str, mode: str, parameters: dict[str, Any], confirm_live: bool = False) -> dict:
        return self.runtime.start(strategy_id, mode, parameters, confirm_live)

    def stop_run(self, run_id: str) -> dict:
        return self.runtime.stop(run_id)

    def status(self, run_id: str | None = None) -> dict:
        return self.runtime.status(run_id)

    def logs(self, run_id: str, lines: int = 100) -> dict:
        return self.runtime.logs(run_id, lines)

    def resume_run(self, run_id: str, confirm_live: bool = False) -> dict:
        return self.runtime.resume(run_id, confirm_live)

    def backtest(self, strategy_id: str, parameters: dict[str, Any]) -> dict:
        return error("NOT_IMPLEMENTED", "Backtest delegation is not implemented yet; use LumiBot directly for now.")

    def account(self, mode: str = "paper") -> dict:
        return self.monitoring.account(mode)

    def positions(self, mode: str = "paper") -> dict:
        return self.monitoring.positions(mode)

    def orders(self, mode: str = "paper", limit: int = 100) -> dict:
        return self.monitoring.orders(mode, limit)