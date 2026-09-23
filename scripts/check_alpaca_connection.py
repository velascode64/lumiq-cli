from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "lumiq" / ".env", override=False)


def result(status: str, **values: Any) -> dict[str, Any]:
    return {"status": status, **values}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Alpaca/LumiBot connectivity check")
    parser.add_argument("--mode", choices=("paper", "live"), default="paper")
    parser.add_argument("--symbol", default="BTC/USD")
    args = parser.parse_args()

    api_key = os.environ.get("ALPACA_API_KEY") or os.environ.get("ALPACA_OAUTH_TOKEN")
    api_secret = os.environ.get("ALPACA_API_SECRET")
    base_url = os.environ.get("ALPACA_BASE_URL", "")
    if not api_key or (not os.environ.get("ALPACA_OAUTH_TOKEN") and not api_secret):
        print(json.dumps(result("error", code="MISSING_CREDENTIALS", message="Alpaca credentials are incomplete."), sort_keys=True))
        return 2

    url_is_paper = "paper-api.alpaca.markets" in base_url.lower()
    if args.mode == "live" and url_is_paper:
        print(json.dumps(result("error", code="ENDPOINT_MODE_MISMATCH", message="Live mode requested with a paper Alpaca endpoint.", base_url_kind="paper"), sort_keys=True))
        return 2

    from lumibot.brokers import Alpaca
    from lumibot.entities import Asset

    config = {
        "API_KEY": os.environ.get("ALPACA_API_KEY"),
        "API_SECRET": api_secret,
        "OAUTH_TOKEN": os.environ.get("ALPACA_OAUTH_TOKEN"),
        "PAPER": args.mode == "paper",
        "IS_PAPER": args.mode == "paper",
    }
    if base_url:
        config["BASE_URL"] = base_url

    try:
        broker = Alpaca(config, connect_stream=False, start_orders_thread=False)
        account = broker.api.get_account()
        clock = broker.api.get_clock()
        base, quote = args.symbol.upper().split("/", 1)
        price = broker.get_last_price(
            Asset(symbol=base, asset_type="crypto"),
            quote=Asset(symbol=quote, asset_type="forex"),
        )
        market = "24/7" if args.symbol.upper().endswith(("/USD", "/USDC", "/USDT")) else "exchange-hours"
        print(json.dumps(result(
            "success",
            mode=args.mode,
            endpoint="paper" if config["PAPER"] else "live",
            account_status=getattr(account, "status", None),
            buying_power_present=bool(getattr(account, "buying_power", None)),
            clock_is_open=getattr(clock, "is_open", None),
            symbol=args.symbol.upper(),
            last_price=str(price) if price is not None else None,
            expected_market=market,
            orders_placed=0,
        ), sort_keys=True, default=str))
        return 0
    except Exception as exc:
        print(json.dumps(result("error", code="ALPACA_CONNECTION_FAILED", message=str(exc), symbol=args.symbol.upper(), orders_placed=0), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
