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

The CLI should eventually make it possible to inspect running strategies:

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

But only expose information that can reliably be obtained from LumiBot/broker/process state.

Do not invent an independent trading state machine.

If persistent process supervision is necessary, use a thin process-management mechanism around LumiBot rather than modifying StrategyExecutor.

⸻

13. Orders and Positions

LumiBot already has Order and Position entities and broker/strategy APIs.

Expose them rather than creating competing domain models.

Potential commands:

lumiq positions momentum
lumiq orders momentum

Agent:

lumiq positions momentum --json
lumiq orders momentum --json

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
│ NAME                 MODE       STATUS       PNL       ACTION     │
│ › Momentum V3        Paper      ● Running    +1.4%     [Stop]     │
│   Mean Reversion     —          ○ Stopped     —        [Start]    │
│   SPY Breakout       Paper      ● Running    +0.3%     [Stop]     │
│   Crypto Momentum    —          ○ Stopped     —        [Start]    │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ ↑↓ Select   Enter Details   R Run   S Stop   B Backtest   Q Quit │
└──────────────────────────────────────────────────────────────────┘

The main screen must prioritize operational information rather than analytics.

The user should immediately understand:

What strategies exist?
What is running?
What mode is each strategy using?
Is something failing?
What can I start or stop?

⸻

26. Strategy Detail

Selecting a strategy opens its detail view.

┌─ Momentum V3 ────────────────────────────────────────────────────┐
│                                                                  │
│ Status       ● Running          Mode          Paper              │
│ Broker       Alpaca             Started       09:31              │
│                                                                  │
│ Parameters                                                       │
│ lookback                         30                              │
│ stop_loss                        0.03                            │
│ risk                             0.02                            │
│                                                                  │
│ [Backtest] [Edit Params] [Experiments] [Logs] [Stop]             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

The initial actions are:

Start
Stop
Backtest
Edit Parameters
Experiments
Results
Logs
Open Source

Do not turn this into a full IDE.

⸻

27. Editing

There are two different kinds of editing.

Parameters

Strategy parameters should be editable directly from the TUI.

For example:

lookback       [30    ]
stop_loss      [0.03  ]
risk           [0.02  ]

These values must map to LumiBot strategy parameters and the existing LumiQ experiment/backtest system.

Source Code

Do not build a source-code editor inside LumiQ.

Provide:

Open Source

which opens the strategy using $EDITOR.

Conceptually:

$EDITOR strategies/momentum/strategy.py

The TUI should display the strategy’s source location before opening it.

⸻

28. Backtest Dialog

Backtest opens a small configuration dialog:

┌─ Run Backtest ────────────────────────────┐
│                                          │
│ Strategy        momentum-v3              │
│                                          │
│ Start           2025-01-01               │
│ End             2025-12-31               │
│ Budget          $100,000                  │
│ Data Source     Yahoo                     │
│                                          │
│ Parameters                               │
│ lookback        [ 30    ]                 │
│ stop_loss       [ 0.03  ]                 │
│ risk            [ 0.02  ]                 │
│                                          │
│          [ Cancel ]  [ Run Backtest ]     │
└───────────────────────────────────────────┘

This must call the same backtest service used by:

lumiq backtest momentum-v3 ...

Do not implement TUI-specific backtesting behavior.

⸻

29. Experiments View

The TUI should make experiments observable to the human operator.

Example:

┌─ Experiments / Momentum V3 ──────────────────────────────────────┐
│                                                                  │
│ RUN             RETURN       SHARPE       DRAWDOWN     STATUS    │
│ baseline         12.1%        1.31         -9.4%       Complete  │
│ exp_021          13.8%        1.52         -7.1%       Complete  │
│ exp_022          11.9%        1.28         -6.8%       Complete  │
│ exp_023            —            —            —         Running   │
│                                                                  │
│ [Compare]        [New Experiment]        [View Results]           │
└──────────────────────────────────────────────────────────────────┘

The TUI must read from the same Run Registry used by the agent CLI.

This allows a human to observe experiments launched by OpenClaw and vice versa.

⸻

30. Logs View

Provide a simple live log viewer:

┌─ Momentum V3 / Logs ─────────────────────────────────────────────┐
│                                                                  │
│ 14:31:02  Iteration started                                      │
│ 14:31:03  SPY price 674.21                                       │
│ 14:31:03  Signal HOLD                                            │
│ 14:31:04  Portfolio value $102,431                               │
│ 14:32:02  Iteration started                                      │
│                                                                  │
│                                                    ● FOLLOWING   │
└──────────────────────────────────────────────────────────────────┘

Reuse LumiBot/LumiQ logs.

Do not create another logging system exclusively for the TUI.

The viewer only needs basic functionality initially:

follow
scroll
pause
resume
clear view

“Clear view” must not delete the underlying log.

⸻

31. Keyboard Navigation

The initial TUI should be optimized for keyboard operation.

Recommended shortcuts:

↑ / ↓       Navigate
Enter       Open strategy
Esc         Back
R           Run
S           Stop
B           Backtest
E           Edit parameters
X           Experiments
L           Logs
Q           Quit

Keep shortcuts consistent across screens.

⸻

32. Runtime State

The TUI and agent must observe the same runtime state.

For example, if OpenClaw executes:

lumiq start momentum --paper --json

the TUI should subsequently display:

Momentum       Paper       ● Running

Likewise, if the human stops it from the TUI:

[Stop]

then:

lumiq status momentum --json

must report it as stopped.

There must not be separate human and agent state.

⸻

33. Project Reorganization

The existing project already contains:

luminbot-cli/
├── .venv/
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

Do not discard or rewrite working implementations simply to achieve a new folder structure.

First inspect the responsibility of every existing module.

Then refactor incrementally toward:

luminbot-cli/
│
├── docs/
│   └── product-definition.md
│
├── lumiq/
│   ├── __init__.py
│   ├── __main__.py
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── strategies.py
│   │   ├── backtest.py
│   │   ├── experiments.py
│   │   ├── runtime.py
│   │   └── results.py
│   │
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── strategies.py
│   │   ├── detail.py
│   │   ├── backtest.py
│   │   ├── experiments.py
│   │   └── logs.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── strategies.py
│   │   ├── backtests.py
│   │   ├── experiments.py
│   │   ├── runtime.py
│   │   └── results.py
│   │
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── strategies.py
│   │   └── runs.py
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── supervisor.py
│   │   └── worker.py
│   │
│   └── output/
│       ├── __init__.py
│       ├── console.py
│       └── json.py
│
├── strategies/
│
├── scripts/
├── tests/
│   ├── cli/
│   ├── tui/
│   ├── services/
│   └── integration/
│
├── .env
├── .gitignore
└── requirements.txt

Responsibility of each layer

cli/

Typer commands only. Parse input, call services, render output.

tui/

Textual interface only. Display state and call services.

services/

Shared application operations used by both CLI and TUI.

registry/

Strategy discovery and LumiQ run/experiment registry.

infrastructure/

Process supervision, persistence and worker implementation.

output/

Human console rendering and deterministic JSON serialization.

strategies/

Existing LumiBot strategies. Do not couple them to the TUI or CLI.

⸻

34. Refactoring Existing Files

Before moving anything, inspect the current implementations of:

lumiq/cli.py
lumiq/database.py
lumiq/registry.py
lumiq/supervisor.py
lumiq/worker.py

Then separate responsibilities.

Expected direction:

Current                         Target
cli.py                    →     cli/*
database.py               →     infrastructure/database.py
registry.py               →     registry/*
supervisor.py             →     infrastructure/supervisor.py
worker.py                 →     infrastructure/worker.py

Business/application logic currently embedded in those files should move into:

services/*

Do not mechanically move whole files if they contain mixed responsibilities.

Extract by responsibility.

⸻

35. Entry Point Behavior

The default command:

lumiq

opens the TUI.

Agent/human automation commands remain available:

lumiq strategies list
lumiq strategy show momentum
lumiq backtest momentum
lumiq experiment run momentum
lumiq results <run-id>
lumiq start momentum --paper
lumiq stop momentum
lumiq status momentum

Agent usage adds:

--json

Example:

lumiq status momentum --json

The presence of a subcommand means do not launch the TUI.

⸻

36. Refactoring Constraint

The agent must not perform a big-bang rewrite.

Required order:

1. Inspect existing implementation
2. Add tests around currently working behavior
3. Identify mixed responsibilities
4. Create shared services
5. Move CLI to use services
6. Verify existing CLI still works
7. Add deterministic --json output
8. Add TUI on top of the same services
9. Verify CLI and TUI observe identical state
10. Remove obsolete code only after replacement is verified

lumibot-old-orchestrator/ must not be deleted automatically. Inspect whether it contains functionality still referenced by LumiQ. If it is truly obsolete, document that finding before removing it.

The refactor is successful when the architecture becomes cleaner without breaking the currently executing strategy workflow.