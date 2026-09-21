---
type: Phase
status: planned
epic: cross-platform
deps: [phase-49-sdks-and-embedding, phase-50-windows-lifecycle]
---

# Phase 51 — native distribution

## Goal

Package pinned native artifacts and SDK integration for macOS arm64/x86_64, Linux arm64/x86_64 and Windows x86_64, plus a server image.

## Boundary and acceptance

Install and run from artifacts on actual target runners, including Linux arm64; no hidden first-run interpreter fetch. Verify checksums/signatures and signing where available; disclose credential or runner blockers. Replaces former Phase 42's PyApp plan.

## Planning state

Outcome and dependencies only: implementation has not started. Derive this phase's design,
plan, tasks and history at its start from [its epic](../../epics/0010-cross-platform.md) and the
[target architecture](../../architecture/native-foundation.md). Do not invent later-phase task
lists while prerequisite code does not exist. [Phase identity map](../../planning/phase-map.md).
