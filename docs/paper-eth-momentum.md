# Paper ETH Momentum

`paper_test_eth_momentum` reuses the ETH aggressive momentum backtest signals.
The original `paper_test_strategy` remains unchanged.

This runner accepts only a Paper broker, uses ETH/USD and trades continuously
with an hourly signal interval. Default allocation is 95% of account equity,
limited to 99% of available cash. Unlike the backtest's 130% allocation, this
does not assume crypto margin. Use a dedicated Paper account without another
ETH strategy: account positions are shared, and this runner refuses to add
exposure when it encounters an ETH position without its own entry state.

## Start

Configure `ALPACA_API_KEY` and `ALPACA_API_SECRET` with Paper credentials and
`ALPACA_IS_PAPER=true`. The runtime uses the normal variables, not
`ALPACA_TEST_API_KEY` or `ALPACA_TEST_API_SECRET`.

From the project root:

```bash
.venv/bin/python -m lumiq start paper_test_eth_momentum --mode paper --json
```

Keep the returned run ID. The supervisor starts a separate process. It does
not guarantee restart after machine shutdown or prevent macOS sleep.

## Agent Checks

An external agent or scheduler can run these checks every 15 minutes:

```bash
.venv/bin/python -m lumiq status <run-id> --json
.venv/bin/python -m lumiq logs <run-id> --lines 100 --json
.venv/bin/python -m lumiq account --mode paper --json
.venv/bin/python -m lumiq positions --mode paper --json
.venv/bin/python -m lumiq orders --mode paper --limit 100 --json
```

Persist timestamped snapshots outside the strategy. Report failed processes,
authentication errors, rejected orders, insufficient data, and missing hourly
heartbeats. Repeated checks within an hour need not contain a new signal.
Logs contain account equity/cash, indicators, entry/exit decisions and reasons.

Account equity, daily P&L and positions are account-scoped, not strategy-scoped.
Measure experiment return against an initial equity snapshot, accounting for
deposits and withdrawals. Use broker fills for executed prices and quantities:
the inherited signal logs use observed prices, not necessarily fill prices.
Entry/trailing state is in memory and is not restored on process restart.
Do not automatically resume, alter parameters or submit orders during checks.

```bash
.venv/bin/python -m lumiq stop <run-id> --json
```

No periodic agent is installed or scheduled by this strategy file. Scheduling
and historical performance storage remain the responsibility of the external
agent.