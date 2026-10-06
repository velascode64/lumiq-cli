---
name: lumiq-platform-review
description: "Review the LumiQ platform and monitor Paper strategies with read-only checks. Use for periodic monitoring, platform health reviews, run status, logs, Alpaca account, positions, orders, heartbeats, errors, and observed performance. Never change parameters, start, stop, resume, or submit orders unless the user explicitly requests that action."
metadata:
  author: LumiQ
  version: "1.0"
---

# LumiQ Platform Review

Use this skill to inspect the running LumiQ platform and Paper strategies. The
primary monitored strategy is `paper_test_eth_momentum`, but accept a different
strategy or run ID when the user provides one.

## Safety Boundary

This is a read-only review workflow by default:

- Never print, read aloud, or copy `.env` values, API keys, secrets, or tokens.
- Never call `start`, `run`, `stop`, `resume`, or `strategy configure` during a
  review unless the user explicitly asks for that exact action.
- Never use `--mode live` for monitoring unless the user explicitly requests a
  live account review.
- Never infer strategy-level P&L from shared Alpaca account P&L.
- Never treat an observed market price as an executed fill price.
- Do not automatically restart a failed process or change its parameters.

## Strategy Change Protocol

If the user explicitly asks to modify a strategy, do not edit the current
branch directly:

1. Inspect the current Git status and preserve unrelated working-tree changes.
2. Create and switch to a new descriptive branch before editing, for example
   `strategy/paper-eth-momentum-risk-limit`.
3. Make only the requested strategy changes on that branch.
4. Run focused validation and report its result.
5. Notify the user of the branch name, files changed, behavior changed, and
   validation performed. Mention any remaining risk or required approval.

Do not commit, push, merge, or delete branches unless the user explicitly asks.
If a branch cannot be created because the working tree or repository state
would make it unsafe, stop before editing and report the blocker.

## Review Workflow

Run commands from the LumiQ project root. Prefer the installed `lumiq`
executable. If it is unavailable, use the project's Python environment:

```bash
lumiq strategies list --json
lumiq status --json
lumiq account --mode paper --json
lumiq positions --mode paper --json
lumiq orders --mode paper --limit 100 --json
```

If the strategy is present, inspect it:

```bash
lumiq strategy show paper_test_eth_momentum --json
lumiq strategy history paper_test_eth_momentum --json
```

For each active run, collect its run ID and inspect the recent log tail:

```bash
lumiq status <run-id> --json
lumiq logs <run-id> --lines 200 --json
```

Use the project's configured state directory when needed:

```bash
export LUMIQ_PROJECT_ROOT=/path/to/lumiq-cli
```

## Findings

Report findings in this order:

1. **Platform status**: run status, PID, heartbeat age, mode, and process
   errors or exit code.
2. **Strategy health**: initialization, latest `[CHECK]`, `[PAPER-ACCOUNT]`,
   entries, exits, active-order messages, and exceptions from logs.
3. **Broker account**: account status, cash, equity, buying power, and
   account-scoped daily P&L when returned.
4. **Exposure and orders**: open positions and order statuses, explicitly
   noting that they are account-scoped.
5. **Observed performance**: only calculate changes from timestamped account
   snapshots or broker fills supplied by the CLI. State the measurement window
   and limitations. Do not claim strategy attribution without isolated account
   or fill data.
6. **Action needed**: classify as `healthy`, `attention`, or `blocked`, with a
   concrete next diagnostic step. Do not execute that step automatically if it
   mutates state.

A missing new signal for less than the strategy interval is not automatically a
failure. For `paper_test_eth_momentum`, the expected signal cadence is hourly.
Treat repeated missing heartbeats, a dead PID, authentication errors, order
rejections, stale data, uncaught exceptions, or unexpected account exposure as
attention or blocked conditions.

## Performance Limitations

The current strategy keeps entry and trailing state in process memory. A process
restart can therefore make strategy attribution incomplete. Account equity,
daily
P&L, positions, and orders are shared Alpaca account data. Broker fills are the
source of truth for execution; log prices are decision observations.

Persist review snapshots outside the strategy if historical comparison is
needed. A periodic reviewer may run this workflow every 15 minutes, but it must
not alter the running process or submit orders.

## Response Format

Return a concise report with:

- `status`: `healthy`, `attention`, or `blocked`.
- `run_id` and last heartbeat when available.
- Most recent relevant log event and its timestamp.
- Account/exposure facts with `account-scoped` labels.
- Errors with their CLI error code and message.
- A next step, clearly marked as read-only or requiring user approval.

Treat the CLI JSON response and process exit code as authoritative. Diagnostics
on stderr are context only and must not be mixed into the JSON response.
