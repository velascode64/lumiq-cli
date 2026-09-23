from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .services.responses import error
from .services.runtime import RuntimeService
from .services.strategies import StrategyService


class LumiqApi:
    """Stable application API shared by CLI, TUI, and future web adapters."""

    def __init__(self, project_root: Path | str | None = None, state_dir: Path | str | None = None):
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
        resolved_state = Path(state_dir or os.environ.get("LUMIQ_STATE_DIR", "~/.lumiq"))
        self.strategies = StrategyService(self.project_root / "strategies")
        self.runtime = RuntimeService(self.project_root, resolved_state)

    def list_strategies(self) -> dict:
        return self.strategies.list()

    def show_strategy(self, strategy_id: str) -> dict:
        return self.strategies.show(strategy_id)

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