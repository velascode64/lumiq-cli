from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..infrastructure.database import RunStore
from ..registry.strategies import discover, resolve
from .responses import error, success


class StrategyService:
    def __init__(self, strategies_root: Path, state_dir: Path):
        self.strategies_root = strategies_root
        self.store = RunStore(state_dir.expanduser() / "lumiq.sqlite3")

    def _public(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "class": item["class"],
            "module": item["module"],
            "parameters": self.store.parameters_for(item["id"], item["parameters"]),
        }

    def list(self) -> dict:
        try:
            strategies = [self._public(item) for item in discover(self.strategies_root)]
            return success(strategies=strategies)
        except Exception as exc:
            return error("DISCOVERY_FAILED", str(exc))

    def show(self, strategy_id: str) -> dict:
        try:
            return success(strategy=self._public(resolve(self.strategies_root, strategy_id)))
        except KeyError:
            return error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.")
        except Exception as exc:
            return error("DISCOVERY_FAILED", str(exc))

    def update_parameters(self, strategy_id: str, parameters: dict[str, Any], source: str) -> dict:
        try:
            strategy = resolve(self.strategies_root, strategy_id)
            defaults = strategy["parameters"]
            unknown = set(parameters) - set(defaults)
            if unknown:
                return error("UNKNOWN_PARAMETER", f"Unknown parameter: {sorted(unknown)[0]}")
            updated = {**self.store.parameters_for(strategy_id, defaults), **parameters}
            self.store.save_parameters(strategy_id, updated, source)
            return success(strategy=self._public(strategy))
        except KeyError:
            return error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.")
        except Exception as exc:
            return error("PARAMETER_UPDATE_FAILED", str(exc))

    def parameter_history(self, strategy_id: str) -> dict:
        try:
            resolve(self.strategies_root, strategy_id)
            history = []
            for row in self.store.parameter_history(strategy_id):
                item = dict(row)
                item["previous_value"] = json.loads(item["previous_value"])
                item["new_value"] = json.loads(item["new_value"])
                history.append(item)
            return success(strategy_id=strategy_id, history=history)
        except KeyError:
            return error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.")
        except Exception as exc:
            return error("PARAMETER_HISTORY_FAILED", str(exc))