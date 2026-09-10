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
| _(none)_ | | | | | |

## Features

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none)_ | | | | | |

## Tech Debt

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| TD-001 | Observations ride in graph state as our own classes | P2 | open | 7 | LangGraph 1.2 warns on deserializing `shadow_hdk.kernel.observations.*` from a checkpoint and says a future version will block it. **Measured 2026-09-10:** `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q` is green over 353 tests, so nothing breaks today. Two remedies: a host builds its checkpointer's serializer with `allowed_msgpack_modules` naming our module — which pushes our internals into every host's setup — or `RunState.observations` holds plain JSON and the runtime loads it back, which keeps the state boundary honest. The second is the design answer; do it when Phase 9 defines what crosses the wire. |

## Enhancements

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none)_ | | | | | |
