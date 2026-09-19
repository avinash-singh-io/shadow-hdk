---
type: Ad-hoc Record
---

# Ad-hoc Work Record: BUG-056

> **Type**: quick-task
> **Created**: 2026-09-19
> **Branch**: fix/BUG-056-set-mode-mid-turn
> **Backlog**: BUG-056
> **Status**: in-progress

## Current Behavior

`Conversation.set_mode` reopens the provider on a behaviour or environment change and nothing on
the path — `Conversation`, `Thread`, `thread/set_mode` — checks whether a turn is running. On a
resident CLI the reopen closes stdin and ends the process group while the turn is mid-stream: the
turn ends early as a failed or truncated `Turn`, with no event saying a mode change did it.
`add_root` does check, but refuses with a bare `RuntimeError` no page can switch on.

## Expected Behavior

Both operations happen **between turns, or not at all**. During a running turn they refuse with
the typed `TurnRunning` — the refusal `turn(when="reject")` already gives (D81), which the wire
already names `turn_running` with `thread_id` and `turn_id`. The change holds the turn lock while
it runs, so a turn asked for meanwhile waits and runs on the reopened session rather than racing
the reopen. The rule is said once (`Conversation._between_turns`).

## Unchanged Behavior

`turn(when=…)` semantics; `TurnRunning`'s shape and the wire's `turn_running` kind; what
`set_mode` and `add_root` do between turns (the environment re-proven, the provider reopened on
its session id, `ModeChanged` / `WorkspaceChanged` on the record); no new error kind, no schema
change, protocol 3. Rule 14: one production file, no contract change — a quick-task.

## Verification Evidence

Captured 2026-09-19 on `fix/BUG-056-set-mode-mid-turn`. Mutations: the refusal dropped → 3 of 4
fail within their bound; the lock not held across the change → 1 fails; restored → 4 pass.

```
$ uv run pytest -q tests/runtime/test_a_change_between_turns_is_refused_during_one.py
....                                                                     [100%]
4 passed in 0.40s
exit=0
```

```
$ uv run ruff check .
All checks passed!
exit=0
```

```
$ uv run mypy .
Success: no issues found in 458 source files
exit=0
```

The wider suites: `tests/runtime tests/wire tests/serve tests/invariants` — 789 passed, 2 skipped.
The whole non-live suite is run at the gate below.
