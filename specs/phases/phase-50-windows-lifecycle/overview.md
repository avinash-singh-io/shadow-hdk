---
type: Phase
status: planned
epic: cross-platform
deps: [phase-47-native-core-and-runtime]
---

# Phase 50 — windows lifecycle and capabilities

## Goal

Deliver native Windows process supervision and evidence-backed capability reporting for selected environments; preserve equivalent lifecycle semantics across operating systems.

## Boundary and acceptance

Missing requested confinement refuses explicitly. Native Windows confinement hardening remains a separately scoped follow-up, not silently declared complete through WSL2. Supersedes the lifecycle portion of former Phase 43.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0010-cross-platform.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
