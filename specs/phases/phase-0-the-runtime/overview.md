---
type: Phase
phase: 0
name: the-runtime
epic: 0001-the-bare-harness
status: complete
topics: [runtime, langgraph, composition, governance, leases, events, agent, patterns]
---

# Phase 0 — The runtime, and the bare test goes green

## Goal

`run(composition, ports)` exists: it compiles a composition to a LangGraph graph, judges every step
through the governance port, emits the nine events, hands proposals to the sink, and carves children
from the parent's lease — and `tests/test_bare_harness.py` passes **with its `xfail` marker removed**,
using stub adapters and zero product code.

## Why now

The kernel is types; nothing runs. Every later phase — real adapters, ACP, sub-agents, the wire —
plugs into an entry point that does not exist yet. This phase is also where the shape gets argued on
a $0 replay rather than inside a product.

## Key decisions

Inherited from Epic 0001 (D1–D13). The four that shape this phase's code most:

| # | in this phase |
|---|---|
| D1 | the agent loop is a component; `run()` is the only entry point |
| D2 | `current_run()` and the contextvar; children carve and forward |
| D6 | `run()` yields events **and** feeds an optional observer from a queue |
| D11 | the benchmark is written in this phase, not retrofitted |

## Scope

### In
- `packages/runtime` — every module in [`architecture/runtime.md`](../../architecture/runtime.md)
- `packages/adapters/basic` — allow-all governance, stdout sink, callback observer, system clock, **callable**
- `packages/adapters/agent` — the model loop as a component, `Pattern`, and the `single` pattern
- `shadow_hdk.runtime.testing` — the five doubles
- `examples/bare.py`, the bare-harness test green, the benchmark, coverage gate
- Every package to **0.1.0**

### Out
- Real providers and real MCP (Phase 1) · modes (Phase 1) · files and code (Phase 3) · ACP (4) ·
  the recording server (5) · nested-composite polish, cancellation and host checkpointers (6) ·
  spawn/send/release as *meta-tools* (7) · the other four patterns (8) · the wire (9)

## Deliverables

| # | Deliverable | Verification |
|---|---|---|
| 1 | The runtime package: session, meter, emitter, registry, inputs, step, compile, state, loop, errors | `uv run pytest tests/runtime` |
| 2 | The five test doubles | `uv run pytest tests/adapters/contract` |
| 3 | `adapters/basic` incl. `callable` | `uv run pytest tests/adapters/basic` |
| 4 | `adapters/agent` with `Pattern` and `single` | `uv run pytest tests/adapters/agent` |
| 5 | Replay determinism | `uv run pytest tests/runtime/test_replay.py` |
| 6 | The latency budget | `uv run pytest tests/runtime/test_benchmark.py` |
| 7 | The bare-harness test, marker removed | `uv run pytest tests/test_bare_harness.py` |
| 8 | Layering invariants extended | `uv run pytest tests/invariants` |
| 9 | 0.1.0 across every package | `uv run pytest tests/test_versions.py` |

## Acceptance criteria

Every row of `specs/vision/success-criteria.md` § Phase 0 Targets, checked by the command in its
last column. In particular: the marker is off the bare-harness test, mypy strict is clean, coverage
on the runtime is ≥ 90 %, and the benchmark reports inside its budget.

## Non-goals worth stating

- **No optimisation pass.** D11's mechanisms are design rules applied as the code is written; if the
  benchmark misses, the design is wrong, not the code slow.
- **No second entry point.** If something seems to need `run_agent()`, it is a pattern.
