---
type: History
phase: 30
---

# History — Phase 30

Append-only. Decisions as `### [DECISION] date — D<n>: title`; the index in
`specs/decisions/index.md` is regenerated from them.

### [NOTE] 2026-09-14 — Opened, from the research note and the owner's go

`specs/research/2026-09-14-what-a-harness-development-kit-owes-its-products.md` read sixteen
things a kit owes against the field and against Intent Studio's fifteen harness modules; the
owner: *"go ahead, write the phase and run it in autonomous mode"*, after confirming the
architecture must stay generic — the note's admission rule is this phase's rule. Context
engineering and collaboration move to 31 and 32. A CI flake seen on the docs branch's run
(`tests/adapters/mqtt/test_review_findings.py::test_a_fault_in_routing_does_not_kill_the_network_thread`
— the subscription acknowledgement timed out on a loaded runner; green on the next run) is
filed as BUG-043 and not chased here.

### [DECISION] 2026-09-14 — D87: the governed turn as a primitive — `Conversation`

**Decision.** `runtime/conversation.py`: `Conversation.open(agent=, ports=, root= | workspace=,
lease=, registry=, approvals=, checkpointer=, modes=, rules=, mode=, principal=, attributes=)` —
one provider session opened on the served registry; `turn(text, when=, on_question=, began=)`
runs one turn as a run of one step and yields every event; `last: Turned` is what it came to
(the turn as a record would remember it, what it spent, the questions it left open);
`tools()`, `set_mode` (answering `Changed` or `None`), `add_root`, `set_option`, `steer`,
`interrupt`, `close`; `resume_parked` wakes a child from the checkpointer; `tell` folds a line
ahead of the next prompt. Nothing of a record: no store, no `ThreadRecord`, no hold. `Thread`
is a `Conversation` plus a record, a store and a hold — every method it had, over the
conversation, the record kept in step (`began` writes the turn down before it runs, the open
questions as they open, the outcome and the spend when it ends); every test of `Thread` passed
unchanged.

**Why.** The Agents SDK's `Runner.run` runs a turn over the product's own session; the Agent
SDK's `query()` and ADK's `Runner` likewise: a product that owns its conversation gets the turn
without the container. Ours could not: to run one governed CLI turn a product opened a `Thread`
per turn over an in-memory store with a one-entry fake mode registry.

### [DECISION] 2026-09-14 — D88: a park on purpose

**Decision.** `Parked` is an answer on the host's handle (`approvals/answer {kind: "park"}`):
the offer returns the provider a refusal that says the call is kept and will run once approved
— and asks it to stop — and does **not** wake the child, which stays asleep in the checkpointer
with the question on it; `Approvals.parked` remembers the handle. A turn whose questions were
answered so ends `parked` (`Turned.pending` carries them); `Thread` keeps them on the record, and
`settle` runs the act from its checkpoint on any later request and tells the agent at its next
turn — D80's machinery, for a host that chose to. `turn(on_question="park")` answers every
question of the turn so, without a host in the loop; `turn/start {on_question}` crosses. A
question neither answered nor parked when the turn ends is withdrawn, as D59 says.

**Why.** A request/response product cannot hold a turn open while a person thinks; LangGraph's
`interrupt` ends the request and a later one resumes. D80 covered the host that died — the
research note's second read found that a turn ended on purpose withdrew its questions, and the
product had built the on-purpose case itself (`_CardAsks`, `parked.py`, in memory, lost on
restart).

### [DECISION] 2026-09-14 — D89: the agent streams

**Decision.** `AgentComponent` reads the model through `ModelPort.stream`: every delta of
thinking and of text is activity beside the record the moment it arrives (D63), the response is
assembled from the chunks — text and reasoning concatenated, the tool calls and the usage off
the chunks that carry them — and the record is what a completed turn's was: the reasoning once,
the answer once. A port without a stream of its own (implemented structurally, or one whose
`stream` is not a stream) answers in one piece through `complete`, and that piece is activity.
`ModelChunk` from the port's default `stream`, the scripted double and the wire's `RemoteModel`
carries `reasoning`. `LangChainModel.stream` merges chunks the way LangChain merges them, yields
every thinking delta as its own chunk, and reads the tool calls and the usage off the merged
message on the last chunk — a call whose arguments arrive in fragments is one call, whole.

**Why.** Every runtime in the field streams; a product streamed *underneath* `complete` with a
model wrapper that folded chunks back (ENH-065, join J5). Closed here.
