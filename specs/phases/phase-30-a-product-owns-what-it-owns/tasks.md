---
type: Tasks
phase: 30
---

# Tasks — Phase 30

## Group 1 — the governed turn; a park on purpose; the agent streams
- [x] `Conversation` in the runtime; `Thread` over it; every `Thread` test unchanged
- [x] `Parked` answer; `turn(on_question="park")`; the turn ends `parked`, `settle` later; over the wire
- [x] `AgentComponent` streams through `ModelPort.stream` as activity; `LangChainModel.stream` keeps reasoning and merges tool calls
- [x] records: D87 (a conversation without a record), D88 (a park on purpose), D89 (the agent streams)

## Group 2 — tokens and running time
- [x] `Spent` tokens; the thread's clock runs only in a turn; records: D90

## Group 3 — the contracts shipped; a `Questions` port
- [x] `shadow_hdk.testing.contracts`, `shadow_hdk.testing.providers`; the tests import from there
- [x] `Questions` port; `Approvals` implements it; records: D91

## Group 4 — routed governance; typed refusals
- [x] `Routed`; `ERROR_KINDS` and `error.data`; the TypeScript client's `RemoteError.kind`; records: D92

## Group 5 — a parked run behind our port; the record versioned
- [x] `RunStore`, the saver over it, `InMemoryRunStore`, the contract and durability tests
- [x] `ThreadRecord.version`; the migration note; records: D93

## Group 6 — sessions that idle out; a stream that survives a drop
- [x] `idle_seconds`; the wire's frame ids, grace period, reattach and replay; the TypeScript client reconnects; records: D94

## The release
- [x] `docs/consuming.md`; the architecture documents; Verification Evidence; 0.29.0 tagged and released; the demo pinned; the board's Pins row
