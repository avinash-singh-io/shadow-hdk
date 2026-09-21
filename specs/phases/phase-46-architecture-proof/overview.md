---
type: Phase
status: planned
epic: cross-platform
deps: [phase-45-truth-both-ways]
---

# Phase 46 — architecture proof and contract baseline

## Goal

Characterize the supported Python/wire behavior; prove a small native execution and recovery slice, Python embedding and managed-sidecar lifecycle; compare selected Goose reuse candidates without an upstream fork.

## Boundary and acceptance

Freeze representative scripted workloads and current baseline measurements; record binding/reuse choices and resource budgets before the full port. A failed foundational assumption returns to the owner; no unbounded research or production cutover.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0010-cross-platform.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
