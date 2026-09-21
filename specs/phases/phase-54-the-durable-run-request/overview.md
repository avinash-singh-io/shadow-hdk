---
type: Phase
status: planned
epic: the-harness-as-data
deps: [phase-53-the-harness-as-data]
---

# Phase 54 — the durable run request

## Goal

Deliver idempotent durable run requests with retry/cancel/catch-up policy and cron, queue and webhook reference adapters.

## Boundary and acceptance

Carries former Phase 37. Timing adapters submit requests, never confer authority. Reuse native execution durability rather than adding a competing scheduler or journal.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0009-the-harness-as-data.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
