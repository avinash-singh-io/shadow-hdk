---
type: Research
status: open
date: 2026-09-19
epic: cross-platform
---

# The LangGraph ledger

> D129: the decision to build a native engine (B) is made on evidence, and this file is the first
> of its three inputs. It records **what the kit takes from LangGraph**, **every place the kit's
> code exists to live with LangGraph's semantics**, and **every defect those semantics caused**.
> Append-only; a row is never softened after the fact. Reviewed at the release that closes
> Epic 0009, no later than 2026-12-31.

## What the kit takes — eight imports, seven files

| import | what it does for the kit |
|---|---|
| `StateGraph`, `START`, `END` | run nodes in order |
| `Send` | fan-out |
| `interrupt`, `Command(resume=…)` | park a step; resume it later |
| `BaseCheckpointSaver`, `InMemorySaver`, `AsyncPostgresSaver`, `JsonPlusSerializer` | persist the parked state |

LangGraph is the kit's **scheduler and checkpointer**. The kit's grammar is five shapes — `Invoke`,
`Sequence`, `FanOut`, `Until`, `Await` (`kernel/composition.py`) — and the runtime it drives is
~2,700 lines (`runtime/loop.py`, `compile.py`, `step.py`, `state.py`, `children.py`,
`checkpoints.py`, `session.py`, `emit.py`). Everything above that — effects, governance, admission,
leases, the record, children's semantics, providers, environments, the wire, threads — is the
kit's own and would be unchanged by any engine.

## The accommodations — code that exists because of LangGraph's semantics

| # | where | what the kit had to do | why |
|---|---|---|---|
| L1 | `runtime/step.py` — D38, `_resume_where_it_parked`, the raise-to-park contract of `_ask` and `_wait` | pick a step up **at the `interrupt()` it raised and nowhere earlier**; emit `ApprovalRequested` only on the raising path | LangGraph re-runs a node from the top on resume, so everything above the interrupt happened twice: two asks in the record for one question, a judgement repeated after a human had answered |
| L2 | `runtime/step.py` — `_wait` | a component put on an `Await` "has to tolerate being called twice" | the same re-run: the component is asked again and says `Pending` again before `interrupt()` returns the answer |
| L3 | `runtime/children.py::release` | resume a released child with a placeholder *word* rather than `None` | `Command(resume=None)` raises inside LangGraph 1.2 (`cannot access local variable 'resume_is_map'`), so a released run would have ended `failed` about a variable instead of `cancelled` |
| L4 | `runtime/loop.py` — `RECURSION_HEADROOM` | size the graph's recursion limit from the lease's step ceiling | LangGraph counts its own super-steps against a recursion limit unrelated to the kit's lease |
| L5 | `runtime/state.py` — D19, state as JSON; `JsonPlusSerializer` | every channel of `RunState` is JSON, the composition is written into the state as JSON (`plan`) | the checkpointer serialises channels; live objects would not survive a park |
| L6 | `runtime/compile.py` — D11, the structural-hash cache | memoise `compile_composition` on the composition's structural hash | compiling a graph per run was measurable overhead; the cache exists to hide LangGraph's compile cost |
| L7 | `runtime/step.py`, `loop.py` — `replays` on the park payload, drained on the resume path | count how many answers a task already holds and drain the replays before handing the component the newest | **BUG-055**: LangGraph replays a task's earlier resume values by index on every re-run, so a step that parked twice in one leg got its first answer again and the second park's `interrupt()` returned instead of raising |

Nineteen mentions of "LangGraph" in the runtime's source exist to explain one of these seven.

## The defects those semantics caused

| id | severity | what | age in the tree |
|---|---|---|---|
| BUG-055 | P1 | a step that parked a second time in one leg was handed its first answer again; the turn `failed` on *"interrupt() returned on the parking path"* | since D57 (Phase 19) until Phase 36 G7 — four phases behind tests that each parked once |
| (L3) | — | a released child ended `failed` naming a LangGraph local variable | found and worked around in Phase 7; never a backlog row |
| (L1) | — | two `ApprovalRequested` events for one question; a judgement repeated after the answer | found and worked around when D38 was written |

## What a scheduler of our own would change

The record is already an event log. A checkpoint could be *derived* — replay the record to the
parked step and continue — which makes the record the single source of truth (D130) and removes
L1, L2, L5 and L7 rather than reimplementing them. The building blocks for a five-shape scheduler
exist in Rust (`tokio`, `serde`, `sqlx`, `axum`); there is no "LangGraph for Rust", and the kit
would not want one — a general graph runtime is what produced this ledger.

## Review criteria (D129)

At the review, record here: the ledger's length and severity at that date; the artifact's size and
time-to-first-turn per OS (Phase 42); Windows proof status (Phase 43); and the decision — B started,
deferred with a new date, or declined — as a numbered decision on the epic.

_(review not yet held)_
