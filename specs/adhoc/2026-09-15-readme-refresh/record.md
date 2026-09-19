---
type: Ad-hoc Record
---

# Ad-hoc Work Record: 2026-09-15-readme-refresh

> **Type**: quick-task
> **Created**: 2026-09-15
> **Branch**: docs/readme-v030
> **Backlog**: none
> **Status**: shipped — `ca432d0` is on `main` (the v0.30 README); the record lagged, found by the post-0.33.0 audit 2026-09-20

## Current Behavior

The README still presented v0.30.0 as an unreleased candidate and mixed the front-page overview,
architecture reference, migration notes, and detailed API catalogue. A new reader could not quickly
tell what Shadow HDK is, what it deliberately does not own, or which public entry point to use.

## Expected Behavior

The README gives a correct v0.30.0 introduction to Shadow HDK as a progressive harness development
kit: a clear purpose and boundary, the main architecture principles, the four consumption levels,
honest production guarantees and limits, working starter examples, and links to the detailed
consumer, migration, package, architecture, roadmap, and release documentation.

## Unchanged Behavior

This is documentation only. It changes no public API, wire contract, release version, package
metadata, product integration, or architectural decision.

## Verification Evidence

- `git diff --check` — passed (no whitespace errors).
- `uv run pytest tests/test_the_readme_runs.py` — passed: 2 tests. This executes the README's
  effect-profile and model-free workflow examples as printed.
- `uv run ruff check` — passed.
- `uv run ruff format --check` — passed: 493 files already formatted.
- `uv run mypy` — passed: no issues in 443 source files.
- Each new internal README documentation target was checked to exist.

## History

### [NOTE] 2026-09-15 — README restructured around progressive consumption

Topics: documentation, public-positioning, shadow-hdk, v0.30.0
Affects-phases: none
Affects-specs: README.md
Detail: Replaced an outdated reference-style README with a concise architectural introduction that
separates the HDK's mechanism from product-owned meaning, distinguishes current facades from the
planned curated Shadow Harness, and retains executable public examples.

---
