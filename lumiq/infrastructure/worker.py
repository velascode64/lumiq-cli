from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import signal
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
load_dotenv(PACKAGE_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)
os.environ.setdefault("TRADING_BROKER", "alpaca")


def load_class(path: Path):
    spec = importlib.util.spec_from_file_location(f"lumiq_strategy_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load strategy: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from lumibot.strategies import Strategy
    for value in vars(module).values():
        if isinstance(value, type) and issubclass(value, Strategy) and value is not Strategy:
            return value
    raise ValueError(f"No Strategy subclass found in {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one LumiBot strategy")
    parser.add_argument("--strategy-path", required=True, type=Path)
    parser.add_argument("--mode", choices=("paper", "live"), required=True)
    parser.add_argument("--parameters", default="{}")
    parser.add_argument("--logfile", required=True, type=Path)
    args = parser.parse_args()
    args.logfile.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(args.logfile)],
    )
    from lumibot.brokers import Alpaca
    from lumibot.traders import Trader

    is_paper = args.mode == "paper"
    config = {
        "API_KEY": os.environ.get("ALPACA_API_KEY"),
        "API_SECRET": os.environ.get("ALPACA_API_SECRET"),
        "OAUTH_TOKEN": os.environ.get("ALPACA_OAUTH_TOKEN"),
        "PAPER": is_paper,
        "IS_PAPER": is_paper,
    }
    if not config["API_KEY"] and not config["OAUTH_TOKEN"]:
        raise RuntimeError("Missing ALPACA_API_KEY/ALPACA_OAUTH_TOKEN")
    strategy_class = load_class(args.strategy_path)
    trader = Trader()
    trader.add_strategy(strategy_class(broker=Alpaca(config), parameters=json.loads(args.parameters)))
    signal.signal(signal.SIGTERM, lambda *_: trader.stop_all())
    trader.run_all(show_plot=False, show_tearsheet=False, save_tearsheet=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())