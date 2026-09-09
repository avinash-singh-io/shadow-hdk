---
type: Plan
phase: 0-the-runtime
---

# Phase 0 — plan

```
# Mixed:  Group 0 → (Groups 1 + 2 in parallel) → Group 3 → Group 4 → Group 5
```

Every group is red first (Rule 13): the tests are written, they fail for the stated reason, then the
code exists. Every assertion is mutation-checked before the group is claimed done.

---

## Group 0 — the spine

**Sequential. Blocks everything.** External: LangGraph `>=1.2,<2`.

- `packages/runtime` scaffolding: `pyproject.toml` (distribution `shadow-hdk`), the namespace layout, the workspace member entry
- `bindings.py` — `Ports`, `RunOptions`, `RunContext`, the `_CURRENT` contextvar
- `session.py` — `Session`, `LeaseMeter` (charge · check · floor_met · carve · remaining), `Handles`
- `emit.py` — `Emitter`: monotone `seq`, the clock port's stamp, the queue and the observer task
- `state.py` — `RunState` and the commutative reducers
- `errors.py`
- `testing/` — `InMemoryComponents`, `ScriptedModel`, `ListSink`, `ListObserver`, `FixedClock`
- `tests/invariants` extended: the runtime imports no adapter; no adapter imports another

**Red first:** `tests/runtime/test_leases.py`, `test_events.py`.
**Commit:** `feat(runtime): package, ports bundle, session, meter, emitter, doubles`

---

## Group 1 — one governed step

**Parallel with Group 2.** Depends on Group 0.

- `registry.py` — the union of component ports; `resolve`; `visible(governance, ctx)`
- `inputs.py` — bindings → JSON from handles; `DanglingRef`
- `step.py` — `StepExecutor.invoke`: the seven moves exactly as `architecture/runtime.md` states them, including `Ask` → `interrupt()` and D7's two error classes

**Red first:** `tests/runtime/test_governance.py`, `test_errors.py`.
**Commit:** `feat(runtime): one governed step — judge, invoke, observe`

---

## Group 2 — compositions become graphs

**Parallel with Group 1.** Depends on Group 0.

- `compile.py` — `Invoke`/`Await` → nodes; `Sequence` → edges; `FanOut` → dispatcher returning `Send`s + join; `Until` → body + conditional edge on condition-or-count; a nested composite → subgraph
- the structural-hash cache (D11)

**Red first:** `tests/runtime/test_compile.py`.
**Commit:** `feat(runtime): compositions compile to graphs`

---

## Group 3 — the drive

**Sequential.** Depends on Groups 1 and 2.

- `loop.py` — `run`: Started · Composed · … · Ended, the five end reasons, the contextvar, `Spawned` on the parent, child event forwarding; `resume`
- `current_run()` and `RunContext.propose` / `remaining` / `spawn_options`

**Red first:** `tests/runtime/test_spawn.py`, `test_replay.py`.
**Commit:** `feat(runtime): run — events out, proposals to the sink, children carved`

---

## Group 4 — the agent, and the small real adapters

**Sequential.** Depends on Group 3.

- `packages/adapters/basic` — `AllowAll`, `StdoutSink`, `CallbackObserver`, `SystemClock`, `callable_component` + `CallableComponents`
- `packages/adapters/agent` — `Pattern`, the `single` pattern and its role file under `patterns/`, `AgentComponent`: the turn loop, the meta-tools the pattern offers, tool calls → composition, the floor nudge
- `tests/adapters/contract/` — the six abstract suites; `basic`, `agent` and the doubles subclass them

**Red first:** `tests/adapters/agent/`, `tests/adapters/basic/`, the contract suites.
**Commit:** `feat(adapters): the agent as a component; allow-all, stdout, callable`

---

## Group 5 — verification

**Sequential. Last.**

- `tests/runtime/test_benchmark.py` — the three budgets, reported in CI
- `examples/bare.py` — the demo; its output committed as evidence
- `tests/test_bare_harness.py` — **the `xfail` marker removed**
- every package to `0.1.0`; `tests/test_versions.py`
- coverage gate ≥ 90 % on the runtime; CI job updated to run the benchmark and print its numbers
- README updated: the four public names and the two-line quickstart

**Commit:** `feat: the bare harness runs with zero product code`
