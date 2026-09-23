Sí. Este es el documento que le daría directamente al agente. Está escrito para evitar que implemente abstracciones que LumiBot ya tiene.

LumiLab — Agent-First CLI for LumiBot

1. Objective

Build a lightweight, agent-first CLI for managing an existing pool of trading strategies built with LumiBot.

The CLI is not a new trading framework.

LumiBot remains responsible for:

* Strategy execution
* Backtesting
* Paper/live trading
* Brokers
* Orders
* Positions
* Portfolio state
* Data sources
* Metrics
* Statistics
* Tearsheets
* Logs and artifacts
* Strategy lifecycle

The CLI is an adapter between:

Human / AI Agent / OpenClaw
             ↓
         LumiLab CLI
             ↓
    Existing Strategy Pool
             ↓
           LumiBot
             ↓
 Backtest / Paper / Live / Results

The primary consumer is an AI coding/trading agent, with human terminal usage as a secondary consumer.

⸻

2. Core Principle

Reuse LumiBot before building anything.

Before implementing any feature, inspect the current LumiBot repository:

⁠Lumiwealth/lumibot

Do not recreate functionality already provided by LumiBot.

In particular, investigate and reuse the existing implementations around:

Strategy
Strategy.run_backtest()
Strategy.backtest()
StrategyExecutor
Trader
Broker
BacktestingBroker
Order
Position
stats_summary
create_tearsheet
SafeJSONEncoder
to_dict()
to_minimal_dict()
strategy parameters
backtesting environment variables

The CLI should contain orchestration and adaptation logic, not trading logic.

⸻

3. Technology

Python

Use the same supported Python versions as the installed LumiBot version.

CLI Framework

Use:

Typer
Rich

Typer handles:

* Commands
* Subcommands
* Arguments
* Options
* Validation
* Help
* Shell completion

Rich handles human-readable terminal output.

Do not build a Textual/TUI application.

There are no screens.

⸻

4. Agent-First Design

Every useful command must support structured output.

Human:

lumiq strategies list

Agent:

lumiq strategies list --json

Human output can use Rich tables.

Agent output must be:

* Valid JSON
* Deterministic
* Minimal
* Machine-readable
* Free of ANSI formatting
* Free of explanatory prose
* Suitable for piping to another program

Example:

{
  "status": "success",
  "strategies": [
    {
      "id": "momentum",
      "class": "MomentumStrategy"
    },
    {
      "id": "mean_reversion",
      "class": "MeanReversionStrategy"
    }
  ]
}

Errors in JSON mode must also be structured:

{
  "status": "error",
  "error": {
    "code": "STRATEGY_NOT_FOUND",
    "message": "Strategy 'foo' was not found."
  }
}

Use meaningful process exit codes in addition to JSON errors.

⸻

5. Existing Strategy Pool

The user already has a pool of LumiBot strategies.

Do not redesign or rewrite these strategies.

The CLI needs a small Strategy Registry/Discovery layer that allows strategies to be referenced by stable IDs rather than Python filenames.

Conceptually:

strategies/
├── momentum/
│   └── strategy.py
├── mean_reversion/
│   └── strategy.py
└── volatility_breakout/
    └── strategy.py

The actual existing repository structure must be inspected before implementing discovery.

Do not force this directory structure if the repository already uses another convention.

⸻

6. Strategy Discovery

The CLI should be able to discover available LumiBot Strategy subclasses.

Minimum command:

lumiq strategies list

Agent:

lumiq strategies list --json

Strategy details:

lumiq strategy show momentum

Agent:

lumiq strategy show momentum --json

Where possible, expose information already available from the Strategy class:

id
class
module/path
parameters
strategy name
backtest capability

Do not instantiate a live broker merely to inspect strategy metadata.

⸻

7. Backtesting

LumiLab must use LumiBot’s existing backtesting API.

Prefer the public API:

Strategy.run_backtest(...)

or the currently recommended equivalent in the installed LumiBot version.

Do not implement a backtesting engine.

Example:

lumiq backtest momentum \
  --start 2025-01-01 \
  --end 2025-12-31

Support common LumiBot inputs where appropriate:

--start
--end
--budget
--benchmark
--data-source
--set KEY=VALUE

Example:

lumiq backtest momentum \
  --start 2025-01-01 \
  --end 2025-12-31 \
  --set lookback=20 \
  --set stop_loss=0.03

Translate --set values into LumiBot strategy parameters.

Do not modify the strategy source code to run parameter variations.

Respect existing LumiBot configuration/environment behavior, including relevant settings such as:

BACKTESTING_START
BACKTESTING_END
BACKTESTING_DATA_SOURCE
BACKTESTING_BUDGET
BACKTESTING_PARAMETERS
LUMIBOT_STRATEGY_PARAMETERS

Be careful that LumiBot environment configuration can override values provided in code. Document this behavior rather than hiding it.

⸻

8. Backtest Results

LumiBot already generates statistics and artifacts.

Do not independently reimplement financial calculations such as:

Sharpe ratio
CAGR
drawdown
returns
benchmark returns
trade statistics

Use LumiBot’s existing outputs.

Relevant existing functionality includes things such as:

stats_summary
create_tearsheet
stats
trade records
logs
CSV/parquet artifacts
tearsheets

Provide:

lumiq results <run-id>

and:

lumiq results <run-id> --json

The CLI should expose the most useful LumiBot results and paths to generated artifacts.

Example conceptual JSON:

{
  "status": "success",
  "run_id": "bt_20260921_001",
  "strategy": "momentum",
  "mode": "backtest",
  "metrics": {},
  "artifacts": {}
}

The exact metrics schema should be derived from LumiBot’s actual returned/generated data rather than invented independently.

⸻

9. Experiments

Experiments are repeated LumiBot backtests with different strategy parameters.

Example:

lumiq experiment run momentum \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --set stop_loss=0.03 \
  --set lookback=20

Another:

lumiq experiment run momentum \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --set stop_loss=0.04 \
  --set lookback=20

Each execution should receive a stable run/experiment ID.

Example:

exp_20260921_001

Store enough metadata to reproduce the experiment:

strategy
strategy parameters
start
end
budget
benchmark
data source
timestamp
LumiBot version
result/artifact locations

Do not build an experiment execution engine separate from LumiBot.

An experiment is fundamentally:

configuration
      +
Strategy.run_backtest(...)
      +
stored metadata/results

⸻

10. Comparing Experiments

Provide:

lumiq experiment compare <run-a> <run-b>

and:

lumiq experiment compare <run-a> <run-b> --json

Comparison should compare metrics already calculated by LumiBot.

For example:

{
  "status": "success",
  "baseline": "exp_001",
  "candidate": "exp_002",
  "metrics": {
    "total_return": {
      "baseline": 0.12,
      "candidate": 0.14,
      "delta": 0.02
    },
    "max_drawdown": {
      "baseline": -0.09,
      "candidate": -0.07,
      "delta": 0.02
    }
  }
}

LumiLab may calculate simple differences between LumiBot metrics.

It should not recalculate the underlying financial metrics.

⸻

11. Paper / Live Execution

LumiBot already provides:

broker = ...
strategy = Strategy(broker=broker)
trader = Trader()
trader.add_strategy(strategy)
trader.run_all()

Reuse this architecture.

Initial CLI:

lumiq run momentum --paper

Potential future live execution:

lumiq run momentum --live

Live execution must not be enabled accidentally.

If implemented, --live must require explicit confirmation or an explicit non-interactive acknowledgement flag for agent execution.

Example:

lumiq run momentum --live --confirm-live

Do not infer live trading from broker configuration alone.

⸻

12. Runtime Management

The CLI must make it possible to inspect managed strategy processes:

lumiq status

or:

lumiq status momentum

Possible information:

strategy
mode
process state
broker
started_at
last activity
portfolio value
positions
orders

Runtime process information comes from LumiQ's Supervisor. Broker account information comes from the configured LumiBot Alpaca broker through read-only calls. They are intentionally separate:

- `lumiq status --json` reports LumiQ-managed process state.
- `lumiq account --mode paper --json` reports the selected Alpaca account.
- `lumiq positions --mode paper --json` reports positions in that account.
- `lumiq orders --mode paper --json` reports orders in that account.

All broker-monitoring commands are read-only. They must not start a strategy, create an order, connect a streaming execution loop, or mutate broker state.

But only expose information that can reliably be obtained from LumiBot/broker/process state.

Do not invent an independent trading state machine.

If persistent process supervision is necessary, use a thin process-management mechanism around LumiBot rather than modifying StrategyExecutor.

⸻

13. Orders and Positions

LumiBot already has Order and Position entities and broker/strategy APIs.

Expose them rather than creating competing domain models.

Broker monitoring is account-scoped, not strategy-scoped:

```bash
lumiq account --mode paper --json
lumiq positions --mode paper --json
lumiq orders --mode paper --limit 100 --json
```

`--mode` must be explicit and accept only `paper` or `live`. It defaults to `paper` for safe inspection. The selected mode configures the LumiBot Alpaca adapter with the same `PAPER` / `IS_PAPER` behavior used by the execution worker.

### Account

`lumiq account --mode <paper|live> --json` returns the broker account summary. When Alpaca supplies the values, this includes:

- `cash`
- `equity` or `portfolio_value`
- `buying_power`
- `last_equity`
- account `status`
- `pnl_today` and `pnl_today_pct`, derived only as $equity - last_equity$

Conceptual response:

```json
{
  "status": "success",
  "mode": "paper",
  "broker": "alpaca",
  "account": {
    "cash": "100000.00",
    "equity": "100142.30",
    "buying_power": "200284.60",
    "last_equity": "100000.00",
    "status": "ACTIVE"
  },
  "pnl_today": 142.3,
  "pnl_today_pct": 0.1423
}
```

This P&L is the P&L of the selected broker account. It must not be labelled as P&L for a specific strategy when multiple strategies share that account.

### Positions

`lumiq positions --mode <paper|live> --json` returns open broker positions. Each item may include the broker-provided fields:

- `symbol`, `qty`, `side`
- `market_value`, `cost_basis`
- `avg_entry_price`, `current_price`
- `unrealized_pl`, `unrealized_plpc`
- intraday unrealized P&L fields when the broker provides them

### Orders

`lumiq orders --mode <paper|live> --limit <1..500> --json` returns broker orders. Each item may include:

- `id`, `symbol`, `side`, `qty`, `filled_qty`
- `status`, order type, limit/stop price
- `filled_avg_price`, `submitted_at`, `filled_at`

`--limit` defaults to `100` and must be between `1` and `500`.

All three commands must preserve the agent JSON contract:

- stdout contains one valid JSON document and no ANSI or startup logging.
- any library startup output is redirected to stderr.
- failures are structured `{"status":"error", "error":{"code":"...", "message":"..."}}` responses with a non-zero exit code.
- missing credentials, incompatible Paper/Live configuration, invalid mode, invalid order limit, and broker query failures must be distinguishable error codes.

Reuse LumiBot serialization such as:

to_dict()
to_minimal_dict()
SafeJSONEncoder

where appropriate.

⸻

14. Run Registry

LumiLab does need one small piece of persistence that LumiBot does not provide as the product-level abstraction we need:

Run Registry

It connects CLI invocations to LumiBot artifacts.

Minimum conceptual record:

{
  "id": "exp_20260921_001",
  "strategy": "momentum",
  "mode": "backtest",
  "created_at": "...",
  "parameters": {},
  "configuration": {},
  "artifacts": {}
}

Keep this extremely simple for the MVP.

Prefer a local filesystem representation or SQLite only if there is a concrete need for querying.

Do not introduce PostgreSQL, Redis or another service.

⸻

15. Suggested Project Structure

Keep the wrapper small.

lumiq/
├── cli/
│   ├── app.py
│   ├── strategies.py
│   ├── backtest.py
│   ├── experiments.py
│   ├── results.py
│   └── runtime.py
│
├── registry/
│   ├── strategies.py
│   └── runs.py
│
├── adapters/
│   └── lumibot.py
│
└── output/
    ├── console.py
    └── json.py

This is a suggestion, not a mandatory architecture.

Prefer fewer files if the implementation remains clear.

⸻

16. Commands — MVP

The first usable version should focus on:

lumiq strategies list
lumiq strategy show <strategy>
lumiq backtest <strategy>
lumiq experiment run <strategy>
lumiq experiment compare <run-a> <run-b>
lumiq results <run-id>
lumiq run <strategy> --paper
lumiq status [strategy]
lumiq account --mode paper
lumiq positions --mode paper
lumiq orders --mode paper

All relevant commands should support:

--json

Do not expand the CLI until these flows work end-to-end.

⸻

17. Primary Agent Workflow

The CLI should make this workflow easy:

1. Agent discovers strategies
          ↓
2. Agent inspects strategy parameters
          ↓
3. Agent establishes baseline backtest
          ↓
4. Agent proposes parameter variation
          ↓
5. Agent runs experiment
          ↓
6. Agent compares results
          ↓
7. Agent reasons about results
          ↓
8. Agent runs another experiment
          ↓
9. Promising candidate goes to paper trading
          ↓
10. Agent monitors results

For example, an agent should be capable of autonomously executing:

lumiq strategies list --json

then:

lumiq strategy show momentum --json

then:

lumiq experiment run momentum \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --set stop_loss=0.03 \
  --json

then:

lumiq experiment compare baseline candidate --json

without needing to understand LumiBot’s internal implementation.

⸻

18. Safety Boundary

Agents may autonomously:

inspect strategies
inspect parameters
run backtests
run experiments
compare experiments
read results
read artifacts
generate analysis
start explicitly configured paper trading

Agents must not autonomously promote a strategy to live trading.

The intended progression is:

hypothesis
    ↓
backtest
    ↓
experiment
    ↓
comparison
    ↓
paper
    ↓
observation
    ↓
human-approved live promotion

⸻

19. Non-Goals

Do not build:

A new trading engine
A new backtesting engine
A new broker abstraction
A new Order model
A new Position model
A new Strategy lifecycle
A replacement for StrategyExecutor
A new metrics engine
A new tearsheet engine
A web UI
A terminal UI
An AI agent framework
An LLM orchestration framework

LumiBot already owns most of these responsibilities.

⸻

20. Testing

Unit-test LumiLab-specific behavior:

strategy discovery
CLI argument parsing
parameter parsing
JSON serialization
run registry
experiment metadata
error handling

Add integration tests against LumiBot for:

discover strategy
run minimal backtest
receive LumiBot results
persist run
read results
compare two runs

Do not mock LumiBot everywhere.

At least one end-to-end test should execute a small real LumiBot backtest using a data source suitable for automated testing.

⸻

21. Implementation Rule

Before writing code for each CLI capability:

1. Search the current LumiBot source.
2. Identify the public API that already provides the capability.
3. Use that API whenever practical.
4. Only implement missing adapter/orchestration behavior in LumiLab.
5. Document any place where LumiLab must depend on a LumiBot internal/private API.
6. Avoid modifying LumiBot itself unless there is a demonstrated framework limitation.

If functionality appears to be missing, do not immediately implement it. Search LumiBot’s:

lumibot/
docs/
docsrc/
examples/
tests/

first.

⸻

22. Definition of Done — MVP

The MVP is complete when an AI agent can execute this sequence without editing Python strategy files:

lumiq strategies list --json
lumiq strategy show momentum --json
lumiq backtest momentum \
  --start 2025-01-01 \
  --end 2025-12-31 \
  --json
lumiq experiment run momentum \
  --start 2025-01-01 \
  --end 2025-12-31 \
  --set lookback=30 \
  --json
lumiq experiment compare <baseline-id> <candidate-id> --json
lumiq results <candidate-id> --json

The agent must receive enough structured information from those commands to decide what experiment to run next.

That loop — discover → backtest → modify parameters → experiment → compare → reason → repeat — is the core product.


Yo agregaría esta sección al Product Definition. Ya la dejo escrita como instrucción para que el agente pueda reorganizar el proyecto existente sin rehacer lo que funciona.

Human TUI & Project Structure

23. Dual Interface: Human TUI + Agent CLI

LumiQ must expose two interfaces over the same application core:

                    LumiQ Core
                        │
             ┌──────────┴──────────┐
             │                     │
          Human                  Agent
             │                     │
        Textual TUI           Typer CLI
             │                  --json
             │                     │
             └──────────┬──────────┘
                        │
                        ▼
                  LumiQ Services
                        │
             Registry / Supervisor
                        │
                        ▼
                     LumiBot

The interfaces have different purposes:

Human interface

Running:

lumiq

must open an interactive terminal UI designed for:

* Operating the trading laboratory.
* Debugging strategies.
* Seeing which strategies are running.
* Starting/stopping strategies.
* Running backtests.
* Editing strategy parameters.
* Inspecting experiments.
* Inspecting results.
* Following logs.

Use:

Textual
Rich

Agent interface

AI agents such as OpenClaw must not interact with the TUI.

Agents use deterministic CLI commands:

lumiq strategies list --json
lumiq strategy show momentum --json
lumiq status momentum --json
lumiq account --mode paper --json
lumiq positions --mode paper --json
lumiq orders --mode paper --limit 100 --json
lumiq backtest momentum --json
lumiq experiment run momentum --json
lumiq experiment compare <run-a> <run-b> --json
lumiq start momentum --paper --json
lumiq stop momentum --json
lumiq results <run-id> --json

--json is the canonical machine interface.

The JSON interface must remain stable even if the TUI changes.

⸻

24. Shared Application Logic

The TUI and CLI must never implement separate trading/application logic.

Both must call the same Python services.

Do NOT implement:

TUI → shell → CLI → LumiQ

Instead:

                  ┌── CLI
                  │
LumiQ services ←──┤
                  │
                  └── TUI

For example, starting a strategy should conceptually work like:

supervisor.start_strategy(...)

Both:

lumiq start momentum --paper --json

and the TUI Start action call that same underlying service.

The same rule applies to:

* Strategy discovery
* Backtests
* Start
* Stop
* Status
* Experiments
* Results
* Logs

⸻

25. TUI — Main Screen

The initial TUI should remain intentionally small.

The main screen displays the strategy pool and current runtime state.

┌─ LumiQ ───────────────────────────────────────────────────────────┐
│ Trading Laboratory                              System ● Running │
│                                                                  │
│ Strategies                                                       │
│                                                                  │
│ NAME                 MODE       STATUS                           │
│ › Momentum V3        Paper      ● Running                        │
│   Mean Reversion     —          ○ Stopped                        │
│   SPY Breakout       Paper      ● Running                        │
│   Crypto Momentum    —          ○ Stopped                        │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ ↑↓ Select   Enter Details   R Run   S Stop   B    Q Quit │
└──────────────────────────────────────────────────────────────────┘

The main screen must prioritize operational information rather than analytics.

The user should immediately understand:

What strategies exist?
What is running?
What mode is each strategy using?
Is something failing?
What can I start or stop?

⸻

# 26. Strategy Detail

Selecting a strategy opens its operational detail view.

The purpose of this screen is to understand the current state of an existing strategy and operate it in Paper or Live mode.

Example:

┌─ Momentum V3 ────────────────────────────────────────────────────┐
│                                                                  │
│ Status       ● Running          Mode          Paper              │
│ Broker       Alpaca             Started       09:31              │
│                                                                  │
│ Parameters                                                       │
│ lookback                         30                               │
│ stop_loss                        0.03                             │
│ risk                             0.02                             │
│                                                                  │
│ [Run Paper] [Run Live] [Stop] [Edit Params] [Param History]      │
│                                                                  │
│ Recent Logs                                      Last 50 lines   │
│ ──────────────────────────────────────────────────────────────── │
│ 14:31:02  INFO   Trading iteration started                       │
│ 14:31:03  INFO   SPY price 674.21                                │
│ 14:31:03  INFO   Signal HOLD                                     │
│ 14:31:04  INFO   Portfolio value $102,431                        │
│                                                                  │
│ Filter: [________________________]   Level: [ALL ▼]               │
│                                                                  │
│ [Logs]                                           [Open Source]   │
└──────────────────────────────────────────────────────────────────┘

The Strategy Detail screen must expose:

- Current status
- Current execution mode
- Broker
- Start time
- Current parameters
- Parameter history
- Recent logs
- Source location

Available operational actions:

- Run Paper
- Run Live
- Stop
- Edit Parameters
- View Parameter History
- View Logs
- Open Source

There must be no Backtest, Experiment, or Compare action in this screen.

Backtesting and strategy research belong to the agent/code iteration workflow and are not TUI operations.

The Recent Logs section displays at most the latest 50 lines by default.


# 27. Editing Strategies

There are two different kinds of editing.

## Parameter Editing

Runtime/configurable strategy parameters may be edited directly from the TUI.

Example:

lookback       [30    ]
stop_loss      [0.03  ]
risk           [0.02  ]

Editing a parameter modifies the configuration of the same registered strategy.

It does NOT:

- Create another strategy
- Create an experiment
- Duplicate the strategy
- Automatically start another process

Every parameter modification must be persisted in parameter history.

At minimum record:

- strategy_id
- timestamp
- parameter
- previous_value
- new_value
- source

`source` should identify who performed the change when known:

- human
- agent

Example:

{
  "strategy_id": "momentum-v3",
  "timestamp": "2026-09-22T21:35:00",
  "parameter": "stop_loss",
  "previous_value": 0.03,
  "new_value": 0.025,
  "source": "human"
}

This history is important because the agent must be able to understand how the strategy configuration has evolved.

## Source Code

Do not build a code editor inside LumiQ.

The TUI provides:

Open Source

This opens the existing strategy source using `$EDITOR`.

Conceptually:

$EDITOR strategies/momentum/strategy.py

The TUI should display the source location before opening it.

Code iteration, strategy development and backtesting remain primarily agent/developer workflows.


# 28. Run Strategy

The TUI only launches existing registered strategies.

Selecting Run opens a small operational dialog.

Example:

┌─ Run Strategy ────────────────────────────┐
│                                          │
│ Strategy        momentum-v3              │
│                                          │
│ Mode                                     │
│   ● Paper                                │
│   ○ Live                                 │
│                                          │
│ Broker          Alpaca                   │
│                                          │
│ Parameters                               │
│ lookback        30                       │
│ stop_loss       0.03                     │
│ risk            0.02                     │
│                                          │
│           [Cancel]   [Start]              │
└──────────────────────────────────────────┘

Paper is the normal operational launch mode.

Live must require explicit human confirmation.

Live must never be inferred or automatically selected because of broker configuration.

Before starting Live execution, show a confirmation such as:

┌─ Confirm Live Trading ────────────────────┐
│                                          │
│ Start momentum-v3 with REAL capital?     │
│                                          │
│ Broker: Alpaca                           │
│ Mode:   LIVE                             │
│                                          │
│       [Cancel]   [Confirm Live]           │
└──────────────────────────────────────────┘

There is no backtest action in the TUI.


# 29. Parameter History

Each registered strategy has a parameter-change history.

This is not an experiment system.

The strategy remains the same strategy while its configuration evolves.

Example:

┌─ Parameter History / Momentum V3 ────────────────────────────────┐
│                                                                  │
│ TIME        PARAMETER      PREVIOUS      NEW          SOURCE     │
│ 09/22 18:20 stop_loss      0.03          0.025        agent      │
│ 09/22 15:42 lookback       20            30           agent      │
│ 09/21 12:11 risk           0.01          0.02         human      │
│                                                                  │
│                                              [Back]              │
└──────────────────────────────────────────────────────────────────┘

The history must allow both the human and agent to answer:

- What changed?
- When did it change?
- What was the previous value?
- What is the new value?
- Was the change made by the human or agent?

Parameter modifications do not create separate experiments or strategy instances.

The agent may modify strategy code and parameters over time to pursue the strategy's goal.

LumiQ records the operational history of those parameter changes.


# 30. Logs

Logs are part of the Strategy Detail screen.

The default embedded view displays only the latest 50 lines.

Example:

┌─ Recent Logs ────────────────────────────────────────────────────┐
│ Filter: [order____________]   Level: [ALL ▼]    Last 50 lines    │
│                                                                  │
│ 14:31:02 INFO   Trading iteration started                        │
│ 14:31:03 INFO   SPY price 674.21                                 │
│ 14:31:04 INFO   Order submitted                                  │
│ 14:31:04 INFO   BUY 10 SPY @ MARKET                              │
│                                                                  │
│                                               ● FOLLOWING        │
└──────────────────────────────────────────────────────────────────┘

The user can open a dedicated Logs view for more space.

The dedicated view must also default to the latest 50 lines.

Logs should support:

- Text filtering
- Log-level filtering when level information exists
- Follow
- Scroll
- Pause
- Resume
- Changing the number of displayed lines

For example:

50
100
250
500

Filtering must happen without modifying the underlying log.

"Clear View" may clear the currently rendered output but must never delete the underlying logs.

Do not create a separate logging system for the TUI.

Reuse the logs produced by LumiQ/LumiBot and the running strategy.


# 31. Keyboard Navigation

The TUI should be optimized for keyboard operation.

Recommended shortcuts:

↑ / ↓       Navigate
Enter       Open strategy
Esc         Back
R           Run Paper
V           Run Live
S           Stop
E           Edit Parameters
H           Parameter History
L           Logs
Q           Quit

Keep shortcuts consistent across screens.

Actions that do not make sense for the current strategy state should be disabled.

For example:

Running Paper:

Run Paper     disabled
Run Live      disabled
Stop          enabled

Stopped:

Run Paper     enabled
Run Live      enabled
Stop          disabled


# 32. Runtime State

The TUI and CLI must observe exactly the same runtime state.

There is no separate state for humans and agents.

For example, if OpenClaw executes:

lumiq start momentum --paper --json

the TUI should display:

Momentum V3       Paper       ● Running

If the human stops it from the TUI:

[Stop]

then:

lumiq status momentum --json

must report the strategy as stopped.

Likewise, if the human changes:

stop_loss: 0.03 → 0.025

the agent must be able to retrieve the updated value and its parameter history.

A registered strategy should have only one active operational instance managed by LumiQ at a time unless the existing runtime explicitly supports otherwise.

Changing parameters does not create another strategy entry.

The operational states should remain simple:

Stopped
Starting
Running Paper
Running Live
Stopping
Error


# 33. Project Structure

The existing project already contains working LumiQ functionality.

Current structure:

luminbot-cli/
├── docs/
├── lumibot-old-orchestrator/
├── lumiq/
│   ├── __init__.py
│   ├── __main__.py
│   ├── .env
│   ├── cli.py
│   ├── database.py
│   ├── registry.py
│   ├── supervisor.py
│   └── worker.py
├── scripts/
├── strategies/
├── .gitignore
└── requirements.txt

Do not perform a broad architectural refactor.

The existing CLI, registry, database, supervisor and worker are already part of the working system.

The immediate architectural change is to add the TUI alongside them.

Target:

luminbot-cli/
│
├── docs/
│   └── product-definition.md
│
├── lumiq/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── database.py
│   ├── registry.py
│   ├── supervisor.py
│   ├── worker.py
│   │
│   └── tui/
│       ├── __init__.py
│       ├── app.py
│       ├── strategies.py
│       ├── detail.py
│       ├── run.py
│       ├── parameter_history.py
│       └── logs.py
│
├── strategies/
├── scripts/
├── tests/
├── .env
├── .gitignore
└── requirements.txt

Responsibilities:

cli.py
    Existing Typer CLI.
    Primary machine/agent interface through --json.

registry.py
    Existing strategy discovery/registry.

supervisor.py
    Existing strategy process/runtime management.

worker.py
    Existing execution worker.

database.py
    Existing persistence layer.

tui/
    Human operational interface built with Textual.

strategies/
    Existing LumiBot strategies.

Do not move working modules merely for architectural cleanliness.


# 34. Integration With Existing Code

Before implementing the TUI, inspect:

lumiq/cli.py
lumiq/database.py
lumiq/registry.py
lumiq/supervisor.py
lumiq/worker.py

Reuse their existing public behavior wherever practical.

The TUI should call the same underlying Python functionality already used by the CLI.

Do not implement:

TUI
 ↓
execute shell command
 ↓
CLI
 ↓
LumiQ

Prefer:

             CLI
              │
              ↓
       Existing LumiQ logic
              ↑
              │
             TUI

Only extract a shared function when the alternative would require duplicating existing logic.

Do not reorganize working files simply to create a theoretically cleaner architecture.

Preserve existing CLI behavior.


# 35. Entry Point Behavior

Running:

lumiq

with no subcommand opens the Textual TUI.

The TUI is the human operational interface.

Existing CLI commands remain available for automation and agent workflows.

For example:

lumiq strategies list
lumiq strategy show momentum
lumiq status momentum
lumiq start momentum --paper
lumiq stop momentum
lumiq account --mode paper
lumiq positions --mode paper
lumiq orders --mode paper

Agent usage:

lumiq strategies list --json
lumiq strategy show momentum --json
lumiq status momentum --json
lumiq start momentum --paper --json
lumiq stop momentum --json
lumiq account --mode paper --json
lumiq positions --mode paper --json
lumiq orders --mode paper --json

Backtesting and code-iteration commands may continue to exist in the CLI:

lumiq backtest momentum --json

Those commands are intended for the agent/developer workflow.

The existence of a CLI command does NOT imply that an equivalent TUI screen or action should exist.

In particular:

Backtesting → CLI/Agent only
Code iteration → Agent/Developer
Strategy operation → CLI + TUI
Paper/Live monitoring → CLI + TUI
Parameter management → CLI + TUI
Logs → CLI + TUI


# 36. TUI Implementation Constraint

The current CLI is working.

Do not rewrite it as part of building the TUI.

Implementation order:

1. Inspect the existing LumiQ modules.

2. Verify and preserve existing CLI behavior.

3. Add Textual as the interactive TUI framework.

4. Create:

   lumiq/tui/

5. Implement the Strategy List screen.

6. Implement Strategy Detail with:
   - runtime state
   - mode
   - broker
   - parameters
   - latest 50 log lines

7. Implement:
   - Run Paper
   - Run Live with explicit confirmation
   - Stop

8. Implement parameter editing.

9. Persist parameter-change history.

10. Implement Parameter History view.

11. Implement log filtering and the dedicated Logs view.

12. Configure:

   lumiq

   with no subcommand to open the TUI.

13. Verify all existing CLI --json behavior remains unchanged.

Do NOT build TUI functionality for:

- Backtesting
- Creating experiments
- Comparing experiments
- Strategy generation
- Code generation

Those remain part of the agent/developer workflow.

The TUI has one responsibility:

**Operate, inspect and debug the existing strategy pool in Paper or Live execution.**