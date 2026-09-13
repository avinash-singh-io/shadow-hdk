---
type: Tasks
phase: 29
---

# Tasks — Phase 29

## Group 1 — the record chooses its store; a parked run survives
- [ ] `[store] url` (`path` as sugar); `stores_for(url)`; `langgraph-checkpoint-sqlite` a base dependency
- [ ] `adapters.postgres`: `PostgresStore`, `PostgresThreads`, the Postgres checkpointer; the `[postgres]` extra; the lazy import with the install hint
- [ ] the contract suites against Postgres under `SHADOW_HDK_TEST_POSTGRES_URL`; CI's Postgres service
- [ ] `ServeHost(store=, threads=, checkpointer=)`; the served threads on the host's checkpointer
- [ ] a parked run survives a host: pending rebuilt from the checkpoint on resume; measured across two hosts
- [ ] records: D79 (the store is a choice), D80 (a parked run is on the record's store); backlog; changelog; adapters.md; the file structure

## Group 2 — one thread, one holder
- [ ] `ThreadStore.acquire/renew/release`; the three implementations; the contract suite
- [ ] `Thread.open/resume` acquire and renew; `ThreadHeld` refused with the holder; `thread/list` `held_by`
- [ ] `turn/start {when}`: enqueue · reject · interrupt; `TurnRecord.started_as`
- [ ] records: D81; wire.md

## Group 3 — identity on the thread, scope on the rows
- [ ] `thread/start {principal, attributes}` → the record and every judgement's context
- [ ] `ModeSpec.scope`, `ActRule.scope`; registries read in scope; a card's rule scoped to who answered
- [ ] records: D82; adapters.md (multi-tenancy: by scope, or by process — both named)

## Group 4 — batteries live
- [ ] wanted batteries as rows seeded from `[tools]`; opened at the next thread; `batteries/list` says on/off by row
- [ ] records: D83

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
