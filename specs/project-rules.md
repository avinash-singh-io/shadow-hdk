---
type: Rules
---

# Project Rules — shadow-hdk

> Project-specific constraints, read at session start (pointed to from `CLAUDE.md → Project
> Extensions`). These bind every agent identically; the generic momentum rules live in `CLAUDE.md`.

## Stack & commands

- Python **≥ 3.12**, **uv** workspace (never pip/poetry), **hatchling** builds, **LangGraph ≥ 1.2, < 2**.
- One import name, `shadow_hdk`, as a **PEP 420 namespace package** — `packages/*/src/shadow_hdk/<part>/`; never add `shadow_hdk/__init__.py`.
- **Gate** before any commit claims done: `uv run ruff check` · `uv run ruff format --check` · `uv run mypy` (strict) · `uv run pytest`. The bare-harness test is the Rule 12 verification evidence for this repository.
- **Commits** are Conventional (`feat(runtime): …`, `docs: …`); the hook enforces it.

## Architecture invariants — each one is a test

- **No product.** Nothing under `packages/` imports `intent.*` or any product. `tests/invariants/test_stands_alone.py`.
- **The kernel is pure.** No I/O, clock, logging, or framework import under `kernel/`. Frozen dataclasses and protocols only.
- **Layers point one way.** kernel ← runtime ← adapters. The runtime never imports an adapter; adapters never import each other.
- **Every contract round-trips through JSON.** A callable cannot cross a port even in-process.
- **No exception crosses `run()`.** A component raising is a `Failed` observation; a port raising ends the run `failed`.
- **The runtime never branches on a label, a name, or a product word.** It knows effects, leases, compositions, observations.
- **Kernel additions go by ADR** — a new effect field (scope-set or boolean only), step kind, event, or port — with a minor version bump and, for a port, a refuse-not-crash default.

## Boundary rule

**Mechanism here; policy and content in the product.** If a change needs to know what a claim, an
intent, a workspace, a mode name or a tool name *means*, it belongs on the other side of a port.

## Test-driven development — ENABLED (Rule 13)

- Every group starts red: the test is written and fails for the stated reason before the code exists.
- **Mutation-check every assertion**: change the code so the assertion should fail, confirm it does, revert. An assertion that cannot fail is deleted.
- Property tests for orders and lattices (`hypothesis`); contract suites for ports — every adapter subclasses the suite for the port it implements.
- Benchmarks run in CI and are reported; a regression past the budget is a failure.

## Two-lane coordination

This repository is **lane H** on `intent-ecosystem/lanes/board.md`. Pull-rebase the board before
reading or writing it; edit only lane H's rows; a contract change is a version bump here and a
pin change on the product side, recorded under *Pins*. Never edit a product repository from this lane.
