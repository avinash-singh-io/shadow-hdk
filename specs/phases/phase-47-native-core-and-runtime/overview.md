---
type: Phase
status: planned
epic: cross-platform
deps: [phase-46-architecture-proof]
---

# Phase 47 — native core and durable execution

## Goal

Implement pure Rust contracts and the shared executor: composition, leases, waiting/resume, child supervision, cancellation, current authority and versioned execution records.

## Boundary and acceptance

Use atomic append/concurrency ownership and crash-injection tests on SQLite and Postgres; preserve controlled/observed distinctions and receipts. The existing Python runtime remains usable.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0010-cross-platform.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
