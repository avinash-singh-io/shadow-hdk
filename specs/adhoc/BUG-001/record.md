---
type: Ad-hoc Record
---

# Ad-hoc Work Record: BUG-001

> **Type**: quick-task
> **Created**: 2026-09-10
> **Branch**: fix/BUG-001-meta-tool-shadowing
> **Backlog**: BUG-001
> **Status**: shipped

## Current Behavior

A registered component whose interface name matches one of the agent's meta-tools — `compose`,
`propose`, `done`, `describe`, `compact`, `spawn`, `send`, `release` (`BY_NAME` in
`adapters/agent/meta.py`) — never runs, and nobody is told. `AgentComponent` routes by name:
`compose()` drops every call whose name is in `BY_NAME` from the work it plans (`work = [c for c
in calls if c.name not in BY_NAME]`) and `carry_out()` skips answering them, so the meta handler
replies instead. Found while writing Phase 13's agent test: a tool `send(to)` was answered by the
helper-mailbox verb with *there is no helper ''; spawn one first*. The routing does not consult
`Pattern.meta_tools`, so a verb the pattern never enabled shadows a tool just as thoroughly.

## Expected Behavior

The collision is a configuration error and is refused where the agent builds its tool list, before
the model is asked to start a turn it could not route correctly. `catalogue()` raises a
`ValueError` naming the registration id and the meta-tool it collides with; the agent is a
component, so by D7 the step becomes `Failed` carrying that reason, on the record, with the run
intact. A deployment's naming is not the model's to work around.

**Rejected.** *Rename on the fly* — it lies about the registration's id, and the receipt, the
proposal and the audit trail all carry that id. *Hide the colliding tool* — silently absent is the
same bug in a new coat. *Prefer the registration over the meta-tool* — the model has been told
about the verb in its system prompt; taking it away mid-run makes the pattern a lie.

## Unchanged Behavior

Every non-colliding tool still runs; the meta-tools still answer for themselves; `Pattern.shows`
and D13's thinning are untouched; no contract, no kernel change, no other adapter.

## Verification Evidence

```
$ uv run pytest tests/adapters/agent/test_a_tool_named_like_a_meta_tool.py -q
4 passed

$ uv run ruff check -q; echo $?          → 0
$ uv run ruff format --check -q; echo $? → 0
$ uv run mypy; echo $?                   → 0   (Success: no issues found in 115 source files)
$ uv run pytest -q; echo $?              → 0   (695 passed, 9 deselected)
```

Four RED-first tests, each through a real run: a colliding tool the pattern does **not** enable
(`send`), one it does (`propose`), a registration whose id differs from its interface name so both
halves of the reason are checkable (`ops-mailer` named `send`), and a tool that does not collide
still running. Five mutations, all bite: the collision not detected; only pattern-enabled verbs
counted; the reason missing the registration id; the reason missing the meta-tool; everything
treated as colliding.
