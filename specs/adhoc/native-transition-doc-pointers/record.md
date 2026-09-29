---
type: Ad-hoc Record
---

# Ad-hoc Work Record: native-transition-doc-pointers

> **Type**: quick-task
> **Created**: 2026-09-21
> **Branch**: `codex/docs-shadow-native-roadmap`
> **Backlog**: none
> **Status**: in-progress

## Current Behavior

This repository contains both the released Python/LangGraph implementation history and copies of
the newly approved native architecture and Phase 46–58 roadmap. Without an ownership marker, an
agent could continue editing the future plan here after its canonical home moved to `shadow`.

## Expected Behavior

`shadow-hdk` remains the maintenance-supported implementation and historical record for releases
through Phase 45. Future architecture, decisions, epics and Phase 46–58 delivery are canonical in
the sibling `shadow` repository. Research and repository strategy are canonical in
`shadow-ecosystem`. Historical copies remain available here with explicit pointers.

## Unchanged Behavior

No package, public API, runtime behavior, release artifact, completed phase record or historical
decision changes. This work does not start Phase 46 and does not make the native runtime usable.

## Verification Evidence

Fresh on 2026-09-21:

- `momentum okf check .` — 235 Markdown files form an OKF v0.1 conformant bundle.
- `git diff --check` — clean.
- Local-link and transfer-marker validation — all links in 20 changed Markdown files resolve;
  all 13 transferred Phase 46–58 overviews carry canonical Shadow pointers.

No runtime test was run because this quick-task changes documentation only and explicitly leaves
runtime behavior unchanged.
