---
type: Phase
status: planned
epic: cross-platform
deps: [phase-48-components-and-strategies]
---

# Phase 49 — public apis and language integration

## Goal

Deliver Rust/Python embedding, Python/TypeScript authoring and managed-runtime clients, streaming, callbacks, lifecycle and wire compatibility.

## Boundary and acceptance

One behavior suite across supported surfaces. TypeScript native in-process embedding is not required; other languages use the documented wire. Select binding technology from Phase 46 evidence.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0010-cross-platform.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
