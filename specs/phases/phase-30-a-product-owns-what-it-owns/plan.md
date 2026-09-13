---
type: Plan
phase: 30
---

# Plan — Phase 30

Six groups in the order a product meets them; each on the phase branch with CI green before
the next; RED first for every rule, a mutation for every load-bearing assertion, the records in
the same commit; the release is one, **0.29.0**, a contract change (additions only).

## Group 1 — the governed turn; a park on purpose; the agent streams (Q1, Q17, Q2)

`runtime/conversation.py`: `Conversation.open(agent=, ports=, lease=, registry=, approvals=,
rules=, checkpointer=, modes=, mode=, principal=, attributes=)` — the provider session opened on
the served registry, `turn(text, when=, on_question=) -> AsyncIterator[Event]`, `last: Turned`
(the turn's id, run id, outcome, text, what it spent, the questions it parked), `tools()`,
`set_mode`, `add_root`, `steer`, `interrupt`, `close`. `Thread` = a `Conversation` + a
`ThreadRecord` + a `ThreadStore` + the hold + `pending`/`settle` — every existing test of
`Thread` passes unchanged. `Parked` as an answer (`runtime/approvals.py`): the offer returns the
provider a refusal that says the call is kept and will run once approved, and does **not** send
the child anything — it stays in the checkpointer; `on_question="park"` answers every question
of the turn so; the turn ends `parked` and its questions stay on the record; `settle` is
unchanged. `AgentComponent` streams when the model can: `ModelPort.stream` chunks become
`activity` (text and reasoning deltas), the response assembled from them; `LangChainModel.stream`
merges chunks the way LangChain merges them, reasoning kept. Wire: `turn/start {on_question}`,
`approvals/answer {kind: "park"}`.

## Group 2 — tokens and running time (Q5, Q10)

`Spent.input_tokens`, `.output_tokens` (unknown never zero: `unpriced` already says so for
money; `unmetered` for tokens); the thread's meter runs only during a turn (`LeaseMeter.pause`
/`resume`), so a thread open overnight with one turn has spent that turn's seconds.

## Group 3 — the contracts shipped; a `Questions` port (Q4)

`shadow_hdk.testing.contracts` — the suites, importable; `shadow_hdk.testing.providers` — a
scripted `AgentPort` that calls the tools it is told to and says its line; the tests import from
there. `Questions` (`kernel/ports.py`): `ask(request) -> answer`; `Approvals` implements it;
`RunOptions.approvals: Questions | None`.

## Group 4 — routed governance; typed refusals (Q6, Q11)

`adapters/modes/routed.py`: `Routed(by_component={...}, otherwise=...)`, a `GovernancePort`
that hands each judgement to the port named for the component in the context, the rest to
`otherwise`; total, never raises. `wire/protocol.py`: `ERROR_KINDS`; `peer.py` writes
`error.data = {"kind", ...detail}`; `ThreadHeld` → `thread_held {holder, thread_id}`,
`TurnRunning` → `turn_running {turn_id}`, `KeyError` → `not_found`, `ValueError` →
`invalid`, else `refused`; the TypeScript client's `RemoteError` carries `kind` and `detail`.

## Group 5 — a parked run behind our port; the record versioned (Q7, Q12)

`kernel/ports.py::RunStore` — `put(run_id, key, blob)`, `get`, `list(run_id)`, `delete(run_id)`
over bytes; `runtime/checkpoints.py`: a `BaseCheckpointSaver` over a `RunStore` (the checkpoint
tuples and writes as rows, the runtime's serde); `stores_for` unchanged for sqlite and Postgres
(LangGraph's own savers stay the fast path); `InMemoryRunStore`; the contract suite and the
durability test over it. `ThreadRecord.version` (2; a record without one reads as 1); the
changelog's migration note for pre-D82 rules.

## Group 6 — sessions that idle out; a stream that survives a drop (Q9, Q8)

`Thread(idle_seconds=)` / `[provider] idle_seconds`: a task closes the provider session after
that long without a turn (the thread stays open and held); the next turn reopens it on its
session id. The wire: every frame carries an `id:`; a session outlives its stream for
`grace_seconds` (60) keeping the frames it could not deliver; `GET /rpc` with the session header
and `Last-Event-ID` reattaches and replays; the TypeScript client reconnects so.

## The release

0.29.0: schemas regenerated where a published contract moved; the TypeScript client grown; the
demo re-pinned and its tour run once; the architecture documents; the Pins row; the guide for a
product (a `consuming` page under `docs/`, written at the release) — the note's §7 in the kit's own words.
