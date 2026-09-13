---
type: Tasks
phase: 29
---

# Tasks — Phase 29

## Group 1 — the record chooses its store; a parked run survives
- [x] `[store] url` (`path` as sugar); `stores_for(url)`; `langgraph-checkpoint-sqlite` a base dependency
- [x] `adapters.postgres`: `PostgresStore`, `PostgresThreads`, the Postgres checkpointer; the `[postgres]` extra; the lazy import with the install hint
- [x] the contract suites against Postgres under `SHADOW_HDK_TEST_POSTGRES_URL`; CI's Postgres service
- [x] `ServeHost(store=, threads=, checkpointer=)`; the served threads on the host's checkpointer
- [x] a parked run survives a host: the question on the record, the child resumed from the checkpoint by `settle`; measured across two hosts (a crash image of the store) and over the wire
- [x] BUG-041 — a cancelled reader of `run()` hung on a drive waiting for nobody — found and closed
- [x] records: D79, D80; backlog; changelog; adapters.md; wire.md; the file structure

## Group 2 — one thread, one holder
- [x] `ThreadStore.hold/renew/release/held_by`; the three implementations; the contract suite
- [x] `Thread.open/resume` hold and renew; `ThreadHeld` refused with the holder; `thread/list` `held_by`
- [x] `turn/start {when}`: enqueue · reject · interrupt (`TurnRecord.started_as` not added — the record already says)
- [x] BUG-042 — a second turn refused *no steps left* — found and closed
- [x] records: D81; wire.md; adapters.md

## Group 3 — identity on the thread, scope on the rows
- [x] `thread/start {principal, attributes}` → the record and every judgement's context
- [x] `ModeSpec.scope`, `ActRule.scope`; registries read in scope; a card's rule scoped to who answered
- [x] records: D82; adapters.md (multi-tenancy: by scope, or by process — both named); wire.md

## Group 4 — batteries live
- [x] wanted batteries as rows seeded from `[tools]`; opened at the next thread; `batteries/list` says on/off by row
- [x] records: D83; adapters.md; wire.md; serve.md

## Group 5 — the budget on the record
- [ ] `thread/start {budget}`; `ThreadRecord.budget`, `.spent`; `thread/remaining` = budget − spent; resume from spent; ENH-013 closed

## Group 6 — the rules the field has
- [ ] `ActRule.decision = "ask"`; deny holds in `full`; glob inputs anchored to roots; the invariant and its mutation
- [ ] records: D84

## Group 7 — operations
- [ ] `GET /healthz`; `admin/sessions`, `admin/threads`; the version in `initialize`
- [ ] the per-run token closed as a decision (D85); wire.md

## The release
- [ ] schemas regenerated; the TypeScript client grown and its smoke green; the demo's tour updated and run once against the wheel
- [ ] the architecture documents; Verification Evidence fresh in this history; 0.28.0 tagged, released, on PyPI; the demo pinned; the board's Pins row
