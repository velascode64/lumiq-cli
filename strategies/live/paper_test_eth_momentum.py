"""ETH momentum signals from the backtest, restricted to Alpaca Paper."""

import importlib.util
from pathlib import Path

from lumibot.entities import Order


_source = Path(__file__).resolve().parents[1] / "backtesting" / "eth_aggressive_momentum_ytd_backtest.py"
_spec = importlib.util.spec_from_file_location("eth_momentum_signals", _source)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load momentum strategy: {_source}")
_signals = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_signals)


class PaperTestETHMomentumStrategy(_signals.ETHAggressiveMomentumYTDStrategy):
    parameters = {
        **_signals.ETHAggressiveMomentumYTDStrategy.parameters,
        "symbol": "ETH/USD",
        "quote_symbol": "USD",
        "position_size": 0.95,
    }

    def initialize(self):
        if getattr(self.broker, "is_paper", False) is not True:
            raise ValueError("PaperTestETHMomentumStrategy requires a Paper broker")
        allocation = float(self.parameters["position_size"])
        if not 0 < allocation <= 1:
            raise ValueError("Paper crypto position_size must be greater than 0 and at most 1")
        super().initialize()
        self.set_market("24/7")
        self.log_message("PAPER ETH MOMENTUM | Continuous operation | ETH/USD")

    def on_trading_iteration(self):
        self.log_message(
            f"[PAPER-ACCOUNT] equity={float(self.portfolio_value or 0):.2f} "
            f"cash={float(self.cash or 0):.2f} entries={self.total_entries}"
        )
        if self.get_orders(statuses=Order.ACTIVE_STATUSES):
            self.log_message("Pending orders: waiting before evaluating another signal")
            return
        position = self.get_position(self.base_asset)
        if position and getattr(position, "quantity", 0) and self.entry_price is None:
            self.log_message("Existing ETH position without entry state: refusing to add exposure")
            return
        original_allocation = self.parameters["position_size"]
        equity = float(self.portfolio_value or 0)
        if equity > 0:
            self.parameters["position_size"] = min(
                float(original_allocation), max(0, float(self.cash or 0)) * 0.99 / equity
            )
        try:
            super().on_trading_iteration()
        finally:
            self.parameters["position_size"] = original_allocation