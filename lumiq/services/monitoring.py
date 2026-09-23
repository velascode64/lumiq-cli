from __future__ import annotations

import contextlib
import os
import sys
from typing import Any, Callable

from .responses import error, success


def _value(record: Any, name: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _public(record: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for field in fields:
        value = _value(record, field)
        if value is not None:
            result[field] = str(value) if field.endswith(("_at", "_time")) else value
    return result


class MonitoringService:
    """Read-only Alpaca account information through LumiBot's broker adapter."""

    def __init__(self, broker_factory: Callable[[dict[str, Any]], Any] | None = None):
        self.broker_factory = broker_factory or self._create_broker

    @staticmethod
    def _create_broker(config: dict[str, Any]) -> Any:
        with contextlib.redirect_stdout(sys.stderr):
            from lumibot.brokers import Alpaca

            return Alpaca(config, connect_stream=False)

    def _broker(self, mode: str) -> Any | dict:
        if mode not in {"paper", "live"}:
            return error("INVALID_MODE", "Mode must be paper or live.")
        configured_paper = os.environ.get("ALPACA_IS_PAPER")
        if configured_paper is not None:
            is_paper = configured_paper.strip().lower() in {"1", "true", "yes", "on"}
            if (mode == "paper") != is_paper:
                return error("BROKER_MODE_MISMATCH", f"Configured Alpaca mode does not allow {mode} monitoring.")
        if mode == "live" and "paper-api.alpaca.markets" in os.environ.get("ALPACA_BASE_URL", "").lower():
            return error("BROKER_MODE_MISMATCH", "ALPACA_BASE_URL points to the paper endpoint; live monitoring is unavailable.")
        api_key = os.environ.get("ALPACA_API_KEY")
        api_secret = os.environ.get("ALPACA_API_SECRET")
        oauth_token = os.environ.get("ALPACA_OAUTH_TOKEN")
        if not api_key and not oauth_token:
            return error("MISSING_ALPACA_CREDENTIALS", "Set ALPACA_API_KEY and ALPACA_API_SECRET (or ALPACA_OAUTH_TOKEN).")
        if api_key and not api_secret:
            return error("MISSING_ALPACA_SECRET", "ALPACA_API_SECRET is required with ALPACA_API_KEY.")
        try:
            return self.broker_factory(
                {
                    "API_KEY": api_key,
                    "API_SECRET": api_secret,
                    "OAUTH_TOKEN": oauth_token,
                    "PAPER": mode == "paper",
                    "IS_PAPER": mode == "paper",
                }
            )
        except Exception as exc:
            return error("BROKER_CONNECTION_FAILED", str(exc))

    def account(self, mode: str) -> dict:
        broker = self._broker(mode)
        if isinstance(broker, dict):
            return broker
        try:
            with contextlib.redirect_stdout(sys.stderr):
                account = broker.api.get_account()
            equity = _float(_value(account, "equity", _value(account, "portfolio_value")))
            last_equity = _float(_value(account, "last_equity"))
            pnl_today = equity - last_equity if equity is not None and last_equity is not None else None
            return success(
                mode=mode,
                broker="alpaca",
                account=_public(account, ("cash", "equity", "portfolio_value", "buying_power", "last_equity", "status", "account_number")),
                pnl_today=pnl_today,
                pnl_today_pct=(pnl_today / last_equity * 100) if pnl_today is not None and last_equity else None,
            )
        except Exception as exc:
            return error("ACCOUNT_QUERY_FAILED", str(exc))

    def positions(self, mode: str) -> dict:
        broker = self._broker(mode)
        if isinstance(broker, dict):
            return broker
        try:
            with contextlib.redirect_stdout(sys.stderr):
                positions = [
                    _public(position, ("symbol", "qty", "side", "market_value", "cost_basis", "avg_entry_price", "current_price", "unrealized_pl", "unrealized_plpc", "unrealized_intraday_pl", "unrealized_intraday_plpc"))
                    for position in broker.api.get_all_positions()
                ]
            return success(mode=mode, broker="alpaca", positions=positions)
        except Exception as exc:
            return error("POSITIONS_QUERY_FAILED", str(exc))

    def orders(self, mode: str, limit: int = 100) -> dict:
        broker = self._broker(mode)
        if isinstance(broker, dict):
            return broker
        if limit < 1 or limit > 500:
            return error("INVALID_LIMIT", "Limit must be between 1 and 500.")
        try:
            from alpaca.trading.enums import QueryOrderStatus
            from alpaca.trading.requests import GetOrdersRequest

            request = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
            with contextlib.redirect_stdout(sys.stderr):
                orders = [
                    _public(order, ("id", "symbol", "side", "qty", "filled_qty", "status", "type", "order_type", "limit_price", "stop_price", "filled_avg_price", "submitted_at", "filled_at"))
                    for order in broker.api.get_orders(filter=request)
                ]
            return success(mode=mode, broker="alpaca", orders=orders)
        except Exception as exc:
            return error("ORDERS_QUERY_FAILED", str(exc))