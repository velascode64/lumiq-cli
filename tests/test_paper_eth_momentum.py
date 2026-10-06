import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lumiq.infrastructure.worker import load_class
from lumiq.registry.strategies import inspect_strategy


PATH = Path(__file__).resolve().parents[1] / "strategies/live/paper_test_eth_momentum.py"
StrategyClass = load_class(PATH)


class ProbeStrategy(StrategyClass):
    portfolio_value = 1000
    cash = 100

    def __init__(self, paper=True):
        self.broker = SimpleNamespace(is_paper=paper)
        self.parameters = dict(StrategyClass.parameters)
        self.total_entries = 0
        self.entry_price = None
        self.base_asset = "ETH"
        self.active_orders = []
        self.position = None

    def log_message(self, *args):
        pass

    def get_orders(self, **kwargs):
        return self.active_orders

    def get_position(self, asset):
        return self.position


class PaperETHMomentumTests(unittest.TestCase):
    def test_discovery_and_worker_agree(self):
        self.assertEqual(inspect_strategy(PATH)["class"], StrategyClass.__name__)
        self.assertEqual(StrategyClass.parameters["symbol"], "ETH/USD")

    def test_live_and_excess_allocation_rejected(self):
        with self.assertRaises(ValueError):
            ProbeStrategy(paper=False).initialize()
        probe = ProbeStrategy()
        probe.parameters["position_size"] = 1.3
        with self.assertRaises(ValueError):
            probe.initialize()

    def test_cash_cap_and_parameter_restoration(self):
        probe = ProbeStrategy()
        allocations = []
        with patch.object(StrategyClass.__bases__[0], "on_trading_iteration",
                          lambda strategy: allocations.append(strategy.parameters["position_size"])):
            probe.on_trading_iteration()
        self.assertAlmostEqual(allocations[0], 0.099)
        self.assertEqual(probe.parameters["position_size"], 0.95)

    def test_pending_orders_and_unknown_position_block_signals(self):
        probe = ProbeStrategy()
        with patch.object(StrategyClass.__bases__[0], "on_trading_iteration") as iteration:
            probe.active_orders = [object()]
            probe.on_trading_iteration()
            probe.active_orders = []
            probe.position = SimpleNamespace(quantity=1)
            probe.on_trading_iteration()
            iteration.assert_not_called()