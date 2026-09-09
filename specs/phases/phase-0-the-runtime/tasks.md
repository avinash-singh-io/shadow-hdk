---
type: Tasks
phase: 0-the-runtime
---

# Phase 0 — tasks

The reasoning lives in `overview.md` and `plan.md`; this is the checklist. Every `RED:` line is
written first and must fail for its stated reason; every assertion is mutation-checked before the
group is claimed done.

## Group 0 — the spine

- [x] `packages/runtime/pyproject.toml` — distribution `shadow-hdk`, `shadow_hdk.runtime`, depends on `shadow-hdk-kernel` + `langgraph>=1.2,<2`; workspace member + source registered in the root
- [x] `bindings.py` — `Ports` (model · components · governance · sink · observer? · clock), `RunOptions` (lease · context · principal · checkpointer? · run_id? · parent), `RunContext`, `_CURRENT` contextvar
- [x] `session.py` — `Session.open`, `Handles` (put · get · as_json), `LeaseMeter`: `charge` · `check` · `floor_met` · `carve` · `remaining`
- [x] `emit.py` — `Emitter`: `seq` from 0 and monotone, `at` from the clock port, an `asyncio.Queue`, the observer on its own task, failures counted not raised
- [x] `state.py` — `RunState` TypedDict; `merge_dicts` and `merge_counts`, both commutative
- [x] `errors.py` — `LeaseExhausted(reason)`, `Cancelled`, `PortFailure`, `DanglingRef`
- [x] `testing/` — `InMemoryComponents`, `ScriptedModel`, `ListSink`, `ListObserver`, `FixedClock`
- [x] RED: `tests/runtime/test_leases.py` — step ceiling · wall ceiling · cost ceiling · carve debits the parent · child over-ask → `Failed` · unknown usage is not zero · floor visible
- [x] RED: `tests/runtime/test_events.py` — seq from 0, strictly increasing · every stamp from the clock port · `Started` first and `Ended` last, once each · a raising observer does not fail a step · iterator and observer agree
- [x] `tests/invariants/test_stands_alone.py` — add: the runtime imports no adapter; no adapter imports another
- [x] Gate: ruff · ruff format · mypy · pytest

## Group 1 — one governed step

- [ ] `registry.py` — union of component ports, `refresh`, `resolve` (unknown → `KeyError`), `visible(governance, ctx)` filtering by `judge`
- [ ] `inputs.py` — `resolve_inputs(bindings, handles)`; literal values pass through; `ref` reads an earlier observation's output; unknown ref → `DanglingRef`
- [ ] `step.py` — the seven moves in order: lease check → resolve → inputs → judge → invoke → charge → observe
- [ ] `Refuse` emits `Refused` **and** returns `Refused`; the component is never called
- [ ] `Ask` emits `Asked` then `interrupt({run_id, step, question})`; a non-`Allow` resume → `Refused`
- [ ] D7: a component's exception → `Failed`; a port's exception → `PortFailure`
- [ ] RED: `tests/runtime/test_governance.py` — refuse · ask → resume(Allow) · resume(Refuse) · `Context` carries run/step/principal/attributes verbatim · judged inside a `FanOut` child too
- [ ] RED: `tests/runtime/test_errors.py` — component raises → run continues · model/sink/governance raises → `Ended(failed)` · nothing escapes `run()`
- [ ] Gate

## Group 2 — compositions become graphs

- [ ] `compile.py` — `compile_composition(c, executor, checkpointer) -> CompiledStateGraph`
- [ ] `Invoke` and `Await` → nodes calling `executor.invoke`
- [ ] `Sequence` → its children wired in order
- [ ] `FanOut` → a dispatcher returning `[Send(...)]` + a join node; real concurrency
- [ ] `Until` → body node + conditional edge on `condition satisfied or iterations >= max`
- [ ] a nested composite → a subgraph node with its own checkpoint namespace
- [ ] the structural-hash cache — the same shape compiles once per process (D11)
- [ ] RED: `tests/runtime/test_compile.py` — the ten cases in `architecture/testing.md`
- [ ] Gate

## Group 3 — the drive

- [ ] `loop.py::run` — `Started` (with lease and parent) · `Composed` · steps · `Ended`, the five end reasons
- [ ] `_resolve_parent` — ambient by default, `parent=None` forces a root (D2)
- [ ] `Spawned` on the parent; the child's events forwarded into the parent's stream in order
- [ ] `RunContext.propose` → `Proposed` event **and** `sink.propose`, carrying the child's provenance
- [ ] `RunContext.remaining` and `spawn_options(ceiling)` — carve from the parent's meter
- [ ] `loop.py::resume(run_id, answer, ...)` — `Command(resume=…)` against `thread_id = run_id`
- [ ] `current_run()` returns `None` outside a step, the context inside one
- [ ] RED: `tests/runtime/test_spawn.py` — child spawn · forwarding order · child proposals carry child provenance · `parent=None` is a root
- [ ] RED: `tests/runtime/test_replay.py` — two runs JSON-identical, with and without a `FanOut`
- [ ] Gate

## Group 4 — the agent, and the small real adapters

- [ ] `packages/adapters/basic` — `AllowAll`, `StdoutSink` (one JSON line per proposal), `CallbackObserver`, `SystemClock`
- [ ] `callable_component(fn, *, effects, name?, description?)` and `CallableComponents` — schema from the signature, exception → `Failed`
- [ ] `packages/adapters/agent` — `Pattern(name, system, meta_tools, tool_filter, ceiling?, max_turns)`
- [ ] the `single` pattern + `patterns/single.md`; meta-tools `propose` and `done` only (D3)
- [ ] `AgentComponent.invoke` — the turn loop; catalogue = visible tools + the pattern's meta-tools
- [ ] one tool call → an `Invoke`; several → a `FanOut`; `compose` → the model's composition verbatim
- [ ] `propose` → `ctx.propose`; `done` → `Completed`; no tool calls → `Completed`
- [ ] the floor: done before `min_steps` → exactly one nudge, then accepted → `gave_up`
- [ ] `tests/adapters/contract/` — `ComponentPortContract`, `ModelPortContract`, `GovernancePortContract`, `SinkPortContract`, `ObserverPortContract`, `ClockPortContract`
- [ ] RED: `tests/adapters/agent/` and `tests/adapters/basic/` — the cases in `architecture/testing.md`
- [ ] the doubles, `basic` and `agent` each subclass their contract suite
- [ ] Gate

## Group 5 — verification

- [ ] `tests/runtime/test_benchmark.py` — 100 sequential no-op steps < 100 ms · 50-way fan-out < 50 ms · p50 per-step overhead reported
- [ ] `examples/bare.py` — a composition over a stub MCP-shaped component, the agent, and a sub-agent, allow-all, stdout; output committed as evidence
- [ ] `tests/test_bare_harness.py` — **the `xfail` marker removed**, the real assertion written
- [ ] `tests/test_versions.py` — every package at `0.1.0`
- [ ] coverage ≥ 90 % on `packages/runtime`
- [ ] `.github/workflows/ci.yml` — run the benchmark and print its numbers
- [ ] README — the four public names, a two-line quickstart, the status line updated
- [ ] Board: lane H row → H0 done, with the commit; the log line
- [ ] Gate, then `/complete-phase`
