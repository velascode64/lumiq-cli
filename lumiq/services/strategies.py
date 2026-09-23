from __future__ import annotations

from pathlib import Path

from ..registry.strategies import discover, resolve
from .responses import error, success


class StrategyService:
    def __init__(self, strategies_root: Path):
        self.strategies_root = strategies_root

    def list(self) -> dict:
        try:
            strategies = [
                {
                    "id": item["id"],
                    "class": item["class"],
                    "module": item["module"],
                    "parameters": item["parameters"],
                }
                for item in discover(self.strategies_root)
            ]
            return success(strategies=strategies)
        except Exception as exc:
            return error("DISCOVERY_FAILED", str(exc))

    def show(self, strategy_id: str) -> dict:
        try:
            return success(strategy=resolve(self.strategies_root, strategy_id))
        except KeyError:
            return error("STRATEGY_NOT_FOUND", f"Strategy {strategy_id!r} was not found.")
        except Exception as exc:
            return error("DISCOVERY_FAILED", str(exc))