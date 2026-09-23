# LumiQ CLI

LumiQ is a lightweight operational layer for an existing LumiBot strategy pool. LumiBot continues to own execution, brokers, orders, positions, portfolio state, and strategy lifecycle.

LumiQ provides two interfaces over the same services:

- **Textual TUI** for a human operator.
- **Typer CLI** with stable `--json` output for agents and automation.

## Setup

This checkout expects the sibling LumiBot checkout at `../lumibot`, as declared in `requirements.txt`.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local `.env` file with Alpaca credentials when using broker-backed commands:

```dotenv
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
ALPACA_IS_PAPER=true
```

`ALPACA_OAUTH_TOKEN` may be used instead of an API key/secret pair when supported by the configured Alpaca account.

LumiQ stores its run registry and logs under `~/.lumiq` by default. Set `LUMIQ_STATE_DIR` to use another state directory, for example in tests or isolated environments.

```bash
export LUMIQ_STATE_DIR=/tmp/lumiq-state
```

## Run The TUI

With no subcommand, LumiQ opens the human TUI:

```bash
python -m lumiq
```

The main screen lists strategies and their managed runtime state. It exposes only:

- `Run`
- `Stop`
- `Refresh`

Open a strategy with `Enter` to access its operational detail. The detail screen provides a mode selector for Paper or Live, parameter editing and history, recent logs, the dedicated log view, source location, and stop control.

Live execution requires a second explicit confirmation in the TUI.

### TUI Shortcuts

| Key | Main screen | Strategy detail |
| --- | --- | --- |
| `Enter` | Open selected strategy | - |
| `R` | Run selected strategy | Run selected strategy |
| `S` | Stop selected strategy | Stop selected strategy |
| `X` | Refresh | - |
| `E` | - | Edit parameters |
| `H` | - | Parameter history |
| `L` | - | Dedicated logs |
| `O` | - | Open source with `$EDITOR` |
| `Esc` | - | Back |
| `Q` | Quit | - |

## Agent CLI

Use `--json` for agent and automation calls. JSON is written exclusively to stdout; LumiBot startup messages and diagnostics go to stderr.

### Discover Strategies

```bash
python -m lumiq strategies list --json
python -m lumiq strategy show <strategy-id> --json
```

Strategy parameters can be persisted without changing the strategy source:

```bash
python -m lumiq strategy configure <strategy-id> \
  --set lookback=30 \
  --set stop_loss=0.025 \
  --source agent \
  --json

python -m lumiq strategy history <strategy-id> --json
```

Parameter history records the strategy, timestamp, parameter, previous value, new value, and source.

### Start, Inspect, And Stop Runs

Start Paper trading:

```bash
python -m lumiq start <strategy-id> --mode paper --json
# Equivalent explicit form:
python -m lumiq run <strategy-id> --paper --json
```

Pass runtime parameters with repeated `--set KEY=VALUE` options. Values are parsed as JSON when possible:

```bash
python -m lumiq start <strategy-id> --mode paper \
  --set lookback=30 \
  --set risk=0.02 \
  --json
```

Live trading is never inferred from configuration. It requires explicit mode and acknowledgement:

```bash
python -m lumiq start <strategy-id> --mode live --confirm-live --json
# Or:
python -m lumiq run <strategy-id> --live --confirm-live --json
```

Inspect and control the LumiQ-managed process:

```bash
python -m lumiq status --json
python -m lumiq status <run-id> --json
python -m lumiq logs <run-id> --lines 100 --json
python -m lumiq stop <run-id> --json
python -m lumiq resume <run-id> --json
```

A run is monitored by its supervisor process and log output. `status` reports LumiQ process state; it does not invent a separate trading state machine.

### Account Monitoring

LumiQ exposes read-only Alpaca account data through the LumiBot broker adapter. These commands do not start a strategy, submit orders, or change broker state.

```bash
python -m lumiq account --mode paper --json
python -m lumiq positions --mode paper --json
python -m lumiq orders --mode paper --limit 100 --json
```

`--mode` accepts `paper` or `live` and defaults to `paper`. The selected mode must match the configured Alpaca credentials and endpoint.

- `account` returns available broker fields such as cash, equity or portfolio value, buying power, status, and daily account P&L when Alpaca provides equity and last equity.
- `positions` returns open account positions with broker-provided valuation and unrealized P&L fields.
- `orders` returns account orders; `--limit` must be from `1` to `500` and defaults to `100`.

Account P&L, positions, and orders are **account-scoped**. LumiQ does not label them as per-strategy values when strategies share an account.

## Error Contract

Commands in JSON mode return either:

```json
{"status":"success"}
```

or:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable explanation"
  }
}
```

Errors use a non-zero process exit code. Common causes include missing Alpaca credentials, Paper/Live configuration mismatch, missing run IDs, and an unavailable broker.

## Development Checks

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q lumiq
```

## Current Scope

Implemented operational capabilities:

- Strategy discovery and metadata.
- Paper and explicitly confirmed Live launches.
- Process supervision, status, stop, resume, and logs.
- Persistent strategy parameters and parameter history.
- Read-only Alpaca account, positions, and orders monitoring.
- Human TUI for operating and debugging registered strategies.

Backtest delegation, experiments, comparisons, and results aggregation are not implemented in LumiQ yet. Use LumiBot directly for those workflows.
