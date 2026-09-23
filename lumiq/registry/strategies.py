from __future__ import annotations

import contextlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any


def _ensure_lumibot_importable(path: Path) -> None:
    for parent in path.resolve().parents:
        checkout = parent / "lumibot"
        if (checkout / "lumibot").is_dir() and str(checkout) not in sys.path:
            sys.path.insert(0, str(checkout))
            return


def strategy_files(root: Path):
    return sorted(
        path for path in root.rglob("*.py")
        if path.name != "__init__.py" and "old" not in path.parts and "backtesting" not in path.parts
    )


def inspect_strategy(path: Path) -> dict[str, Any]:
    _ensure_lumibot_importable(path)
    module_name = f"lumiq_discovery_{path.stem}_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
        from lumibot.strategies import Strategy
        classes = [
            obj for _, obj in inspect.getmembers(module, inspect.isclass)
            if issubclass(obj, Strategy) and obj is not Strategy and obj.__module__ == module.__name__
        ]
    if not classes:
        raise ValueError(f"No LumiBot Strategy subclass found in {path}")
    strategy_class = classes[0]
    return {
        "id": path.stem,
        "class": strategy_class.__name__,
        "module": str(path),
        "parameters": getattr(strategy_class, "parameters", {}) or {},
    }


def discover(root: Path, strict: bool = False):
    result = []
    for path in strategy_files(root):
        try:
            result.append(inspect_strategy(path))
        except Exception:
            if strict:
                raise
    return result


def resolve(root: Path, strategy_id: str) -> dict[str, Any]:
    direct_matches = [path for path in strategy_files(root) if path.stem == strategy_id]
    if direct_matches:
        return inspect_strategy(direct_matches[0])
    raise KeyError(strategy_id)