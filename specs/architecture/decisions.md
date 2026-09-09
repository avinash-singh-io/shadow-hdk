---
type: Architecture
---

# Decisions taken at founding

> `09-the-agentic-system.md` decides the design. These are the thirteen things it leaves open that
> had to be settled before code. Each is recorded on Epic 0001 and each is falsifiable — the column
> that matters is *what would overturn it*.

## D1 — The agent loop is a component, not a second entry point

`run(composition, ports)` is the only way in. The model-driven loop lives in
`shadow_hdk.adapters.agent` as a `ComponentPort`, so "run one agent" is a composition of one
step, and "an orchestrator with workers" is an agent component whose composition invokes other agent
components. There is no `run_agent()` beside `run()`.

*Why:* one mechanism. It is also what makes patterns data — `single` is a composition plus a role
file, not a code path. *Overturned by:* a pattern that cannot be expressed as a composition over
agent components.

## D2 — Spawning is ambient

A `run()` started while a step is executing discovers its parent through a contextvar — the way
LangGraph's own `get_stream_writer()` finds its writer. The child carves its lease from the parent's
meter, emits `Spawned` on the parent, and forwards its events into the parent's stream.

*Why:* no label branch in the runtime (a sub-agent is a component like any other), no kernel change,
and it works identically in-process and behind the wire. *Overturned by:* a host that needs two
unrelated runs in one task without one becoming the other's child — then `run(..., parent=None)`
becomes explicit.

## D3 — The model's meta-tools belong to the pattern, not the runtime

`compose`, `propose`, `done` — and later `spawn`, `send`, `release`, `describe` — are offered by the
agent adapter, and **which of them the model sees is the pattern's choice**. The runtime knows none of
their names.

*Why:* it is the mechanism by which one product gets a deterministic ReAct agent and another gets a
dynamic orchestrator from the same code. *Overturned by:* nothing foreseeable; a new meta-tool is a
new entry in a pattern file.

## D4 — `Ports` and `RunOptions` are runtime types, not kernel types

The kernel defines the port protocols. How a runtime is *configured* — the bundle of six, plus the
lease, context, principal, checkpointer and run id — is the runtime's own dataclass.

*Why:* the kernel stays a vocabulary, not a wiring convention. *Overturned by:* the wire needing to
serialise a bundle, which it does not — it serialises the calls.

## D5 — Ask and Await are `interrupt()`

Both compile to LangGraph's `interrupt()`; a run is addressed by `thread_id = run_id`; a host resumes
with `Command(resume=…)`. Phase 0 ships `InMemorySaver`; a host passes its own checkpointer.

*Why:* §10's rule — nothing LangGraph already does is rebuilt. *Overturned by:* a host that must
survive a process restart without a checkpointer, which is a contradiction.

## D6 — Events go two ways at once

`run()` yields events **and** calls the observer port if one is bound. The observer is fed from a
queue on its own task; a raising observer is swallowed and counted, never failing a step.

*Why:* embeddable (iterate it) and hostable (bind an observer) without two APIs, and the observer is
off the critical path — part of the latency budget. *Overturned by:* an observer that must be able to
abort a run, which is governance's job, not an observer's.

## D7 — A component raising is data; a port raising is a failure

A component's exception becomes a `Failed` observation and the run continues — the agent sees it and
may retry, ask, or route around. A port's exception ends the run `failed`. No exception escapes
`run()`.

*Why:* a component is untrusted and arrives from anywhere; a port is the host, and a broken host is
not something the runtime can reason past. *Overturned by:* a host wanting a component's crash to end
the run, which is a governance policy it can already express.

## D8 — Test doubles ship in the package

`shadow_hdk.runtime.testing` carries an in-memory component port, a scripted model, list sink and
observer, and a fixed clock. The tiny real adapters — allow-all governance, stdout sink, system clock
— ship as `adapters/basic`, alongside the `callable` adapter that turns a Python function into a
component.

*Why:* a host's suite must be able to run the harness for $0, and `08` already wanted
`testing.assert_account_is_derived`; this is its general form. *Overturned by:* nothing — this is the
cheapest thing in the design.

## D9 — Versioning and the pin

SemVer. Every package reaches 0.1.0 at Phase 0's end; `v0.1.0` is tagged at Phase 9 (join J2).
Pre-1.0, a contract change is a **minor** bump plus a row on `intent-ecosystem/lanes/board.md` under
*Pins*. The product pins an exact version and adopts deliberately.

*Why:* the join is the only place two lanes can break each other. *Overturned by:* 1.0, when a
contract change becomes a major bump.

## D10 — LangGraph `>=1.2,<2`; Python `>=3.12`

The same major line the product runs (1.2.11), so the R3 join has one framework version.

*Why:* two LangGraph majors in one process is not a thing. *Overturned by:* LangGraph 2, which is an
ADR and a coordinated bump on both lanes.

## D11 — Latency is a budget with a benchmark, not an aspiration

**≤ 1 ms p50 of runtime overhead per step**, measured on a no-op component under allow-all. The
mechanisms that make it true, each a design rule rather than an optimisation pass:

- governance is an in-process async call; the effect-rules adapter is a table lookup over six fields, never a model call
- **no serialisation per step in-process** — the JSON round-trip is a CI proof about the *shape* of the contracts, not a runtime cost
- compiled graphs are cached by the composition's structural hash, so a repeated shape compiles once
- the observer is fed from a queue on its own task and never awaited on the critical path
- checkpointing is opt-in; the default in-process run persists nothing
- `FanOut` is real concurrency (`Send` + `asyncio`), not a loop
- the registry is refreshed per step but *filtered* lazily; visibility is computed only when the model is about to be shown the catalogue

`tests/runtime/test_benchmark.py` runs in CI: 100 sequential no-op steps < 100 ms, 50-way fan-out
< 50 ms. A regression past the budget fails the build.

## D12 — Build versus buy: LangGraph executes; we compile and govern

We do not write a Python interpreter for compositions. We write a **compiler**
(`Composition → StateGraph`) and a **governed step** every node calls. Execution, concurrency,
checkpointing, interrupts, streaming, retries and timeouts are LangGraph's.

| candidate | licence | verdict |
|---|---|---|
| **LangGraph** | MIT | the executor — fixed by `09` §10 |
| Temporal · DBOS Transact | MIT | durable workflows — a different layer; DBOS stays product-side for jobs |
| CrewAI · AutoGen · OpenAI Agents SDK | MIT | each imposes an agent shape, which is what this design refuses; their shapes are portable as *pattern files* |
| smolagents (HF) | Apache-2.0 | a code-agent loop worth porting as a pattern later, not a runtime |
| LlamaIndex Workflows | MIT | event-driven executor; no advantage over LangGraph here |

*Why:* "declarative plan → graph engine" is the standard shape (Temporal, Argo, Airflow, LangGraph's
own spec). What is unusual about Codex, Claude Code and opencode is the opposite — they hardcode the
loop, because they are products rather than runtimes. *Overturned by:* the compiler growing past a
few hundred lines to fight the engine, which would mean the grammar and the engine disagree.

## D13 — Tools scale by scoping, not by a bigger list

There is one flat registry. Four mechanisms keep a large one from becoming the model's problem:

| mechanism | what it does | phase |
|---|---|---|
| visibility is computed | the registry is filtered by governance every step; under a read mode no write tool is ever shown | 0 |
| patterns scope tools | a pattern names which tools each role gets, and which meta-tools exist | 0 (`single`), 8 |
| sub-agents partition tools | the orchestrator holds five and delegates; each worker holds its own ten | 7 |
| catalogue compaction | above a threshold (a setting, default ~30) the model sees names and one-line descriptions and pulls a schema on demand with `describe` | 8 |

*Why:* the harness's job is to make scoping free; whether a given catalogue degrades a given model is
the product's eval, not the harness's. *Overturned by:* a measurement showing a scoped catalogue still
degrades quality, which would move compaction earlier.
