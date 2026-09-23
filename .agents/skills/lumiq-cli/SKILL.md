---
name: lumiq-cli
description: "Operate and inspect the LumiQ CLI in this repository: discover strategies, configure parameters, manage paper runs, inspect logs, and query Alpaca account data. Use for `python -m lumiq` tasks; do not use for implementing LumiBot trading logic."
metadata:
  author: LumiQ
  version: "1.0"
---

# LumiQ CLI

Use this skill only to operate the CLI in this repository. LumiQ is a thin adapter over LumiBot; it must not become a replacement trading framework or a source of independently calculated trading metrics.

It requires the project Python environment and LumiBot dependency; broker-monitoring and execution commands also require configured Alpaca credentials.

Run commands from the repository root:

```bash
cd luminbot-ai/luminbot-cli
python -m lumiq <command> --json
```

Do not invoke `python -m lumiq` with no command: it starts the Textual UI. For agent work, use a named command and `--json`. Treat stdout as one JSON document; diagnostics belong on stderr. Check the process exit status as well as the JSON `status`.

## Operating rules

- Inspect before acting: start with `strategies list --json`, then `strategy show <id> --json` before changing parameters or starting a run.
- Use stable strategy IDs returned by discovery. Current discovery scans `strategies/`, excluding `old/` and `backtesting/`; do not assume filenames or paths outside that result are runnable.
- Pass each parameter as `--set KEY=VALUE`. Values that are valid JSON are typed (`20`, `true`, `0.03`, `"text"`, arrays, objects); other values are strings. Repeat `--set` for multiple parameters.
- Prefer read-only commands. `account`, `positions`, and `orders` default to `--mode paper`; explicitly state `--mode live` when live account data is requested.
- Starting, stopping, resuming, and configuring change local runtime or configuration state. Only perform them when the user asks.
- Never start or resume live trading without explicit user authorization in the current request. Live execution additionally requires `--confirm-live`; that flag is a guard, not authorization.
- Do not expose credentials or copy `.env` contents into output. Broker errors can be reported by their error code and message.

## Supported command flow

```bash
# Discover and inspect
python -m lumiq strategies list --json
python -m lumiq strategy show <strategy-id> --json
python -m lumiq strategy history <strategy-id> --json

# Save parameters, then start a paper run
python -m lumiq strategy configure <strategy-id> --set lookback=20 --set stop_loss=0.03 --json
python -m lumiq run <strategy-id> --paper --set lookback=20 --json

# Inspect or manage a run
python -m lumiq status --json
python -m lumiq status <run-id> --json
python -m lumiq logs <run-id> --lines 100 --json
python -m lumiq stop <run-id> --json
python -m lumiq resume <run-id> --json

# Read-only broker monitoring
python -m lumiq account --mode paper --json
python -m lumiq positions --mode paper --json
python -m lumiq orders --mode paper --limit 100 --json
```

`run` requires exactly one of `--paper` or `--live`. `start <strategy-id> --mode paper` is equivalent for paper execution. `orders --limit` accepts 1 through 500.

## Known implementation caveat

Strategy discovery imports strategy modules. Some current modules can initialize Alpaca streaming clients while being inspected, so `strategies list` is not guaranteed to be offline or side-effect-free despite its read-only intent. It can also emit connection failures to stderr while still returning a successful JSON result. Do not retry or start a run merely because discovery logs a broker connection failure; report that caveat and let the user decide whether broker connectivity should be investigated.

## Current boundaries

`backtest <strategy-id> --json` currently returns `NOT_IMPLEMENTED`; do not present it as a completed backtest or substitute a custom engine. `results`, `experiment run`, and `experiment compare` are product goals, not current CLI commands. Use LumiBot directly only when the user explicitly asks for work outside the CLI.

The current command surface is authoritative: inspect `python -m lumiq --help` and the relevant subcommand help if it conflicts with [the product definition](../../../docs/product-definition.md), which describes intended as well as implemented functionality.

## Response handling

Successful responses have `"status": "success"`; failures have `"status": "error"` with `error.code` and `error.message`, and a non-zero exit status. Report the command outcome, returned IDs, and material error codes concisely. Do not invent fields or financial metrics absent from the CLI response.
