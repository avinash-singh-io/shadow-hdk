---
type: Phase
status: planned
epic: cross-platform
deps: [phase-51-native-distribution]
---

# Phase 52 — migration and native release acceptance

> **Transferred:** the canonical delivery spec is
> [Shadow Phase 52 — migration and native release acceptance](../../../../shadow/specs/phases/phase-52-native-migration/overview.md).
> This copy remains only for provenance and old-link continuity; do not plan or execute the phase here.

## Goal

Prove supported behavior parity, persistence transition and rollback before making native execution the default.

## Boundary and acceptance

Keep old data intact; identify engine/store formats and define drain or compatibility handling for old runs. Never duplicate real irreversible effects for comparison. Meet Phase 46's frozen budgets and platform gates.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0010-cross-platform.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
