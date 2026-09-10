---
type: Backlog
---

# Backlog

> **Last Updated**: YYYY-MM-DD

---

## Priority Levels

| Level | Meaning |
|-------|---------|
| **P0** | Critical — blocks current phase |
| **P1** | High — address in current/next phase |
| **P2** | Medium — within 2 phases |
| **P3** | Low — nice to have |

**Status**: `open` | `in-progress` | `resolved` | `deferred` | `deprecated`

---

## Bugs

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| BUG-001 | A component named like an agent meta-tool is shadowed silently | P2 | open (found 2026-09-10) | 13 | A registration whose id matches a name in `Pattern.meta_tools` (`send`, `spawn`, `release`, `done`, …) never runs: the agent adapter builds the model-facing tools from the meta-tools by name (`adapters/agent/component.py:184`) and the meta-tool answers the call. Observed: a tool `send(to)` got *there is no helper ''; spawn one first*. Fix: refuse at the point the agent builds its tool list, naming both the registration and the meta-tool. |
| _(none)_ | | | | | |

## Features

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none)_ | | | | | |

## Tech Debt

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| TD-001 | Observations ride in graph state as our own classes | P2 | **closed 2026-09-10 (D19)** | 7 → 9 | LangGraph 1.2 warns on deserializing `shadow_hdk.kernel.observations.*` from a checkpoint and says a future version will block it. **Measured 2026-09-10:** `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q` is green over 353 tests, so nothing breaks today. Two remedies: a host builds its checkpointer's serializer with `allowed_msgpack_modules` naming our module — which pushes our internals into every host's setup — or `RunState.observations` holds plain JSON and the runtime loads it back, which keeps the state boundary honest. The second is the design answer; done in Phase 9 Group 0 as **D19** — a checkpoint *is* a wire, so the state holds JSON and the runtime loads at its edge. **Verified:** `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q -W default` now reports zero such lines across 406 tests. |

## Enhancements

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none)_ | | | | | |
