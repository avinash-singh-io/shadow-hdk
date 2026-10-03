---
type: Retrospective
phase: phase-66-the-short-list
status: in-progress
---

# Phase 66 — 0.45.0 checkpoint, phase still open

The first train checkpoint adds E, ships the previously gated unreleased changes and applies the
mandated DDL-free PostgreSQL default. C, D and H6–H8 remain for separate releases. This is release
verification evidence, not a claim that the phase is complete or that the candidate is published.

## What held

The existing model loop supplies binding, dependency checking and instruction delivery. The host
only resolves a stored opaque name and wires that existing mechanism. Unsupported pre-binding is
reported; governed skill choosing still works on CLI providers. No new decision was needed.

D190: a coding tool, a support desk and a research assistant would each use this. The generic
runtime only merges opaque unsupported contributions; the adapter names the binding. No operation
name was added to kernel or runtime. D184's migration table was updated before this checkpoint.

## What the mutations found

A direct Pattern default was not initially covered; an assertion now catches its mutation. The
internal pool default was redundant because public adapters supply the flag explicitly, so the
redundant default was removed. All twenty retained mutations bite, including procedure text being
lost, the stored binding being ignored, dependency checking being bypassed, reporting being lost,
DDL being executed by default and reopen skipping verification.

## Verification Evidence

Fresh verification on 2026-10-04:

- Baseline: 2,200 passed, 29 skipped, 24 deselected; lint, format and strict types passed.
- E started red: eight failed on the missing stored-row support. Reporting separately started red
  with its fold removed. PostgreSQL defaults started red: four failed, two compatibility cases passed.
- New targeted tests: 17 passed. Disposable PostgreSQL 16 server database/store checks: 37 passed,
  including restricted-role open, close, reopen and data operations.
- Final gate: lint clean, 548 files formatted, strict types clean over 515 files;
  **2,238 passed, 8 skipped, 24 deselected**, 85 pre-existing warnings, exit 0 in 202.89 seconds.
  The skipped cases require live external accounts or tools; database cases were enabled.
- Twenty anchored mutation checks with the repository helper: all BITES. Raw results:
  [`g5-e-mutations.txt`](evidence/g5-e-mutations.txt).
- The kit wheel and sdist build. A clean virtual environment outside the checkout resolves 0.45.0;
  imports come from its installed package, and all **17 new cases pass against that wheel**.
- Published schemas and TypeScript contracts regenerated without drift. No wire property was added.
- Full gate output: [`0.45-gate.txt`](evidence/0.45-gate.txt).

## Remaining release gate

Owner protected landings, release tag and GitHub Release, then fresh-install and seven-file
publication verification for both distributions. Follow the lane P reply. Continue with C only
once this release checkpoint has landed and published; then D and individually confirmed H6–H8.

## 0.46.0 checkpoint — C, phase still open

The owner authorized preparation of the remaining separate checkpoints without waiting for
publication. This supersedes the earlier waiting instruction; each candidate freezes independently
and must land and publish parent-first. C uses the approved existing PlanLimits parser and existing
child admission. No new decision, kernel type or port was required. D and H6–H8 remain.

### Verification Evidence

Fresh verification on 2026-10-04: lint clean, 549 files formatted, strict types clean over 516
files; **2,248 passed, 8 skipped, 24 deselected**, exit 0 in 195.26 seconds, with disposable
PostgreSQL enabled. Ten C cases pass on the clean installed 0.46.0 wheel outside the checkout.
Ten mutations bite. All 165 Python source files match the wheel; schemas and TypeScript
contracts regenerate without drift. The kit wheel and sdist build. Raw gate and mutation outputs:
[`0.46-gate.txt`](evidence/0.46-gate.txt), [`g5-c-mutations.txt`](evidence/g5-c-mutations.txt).

Protected landing, release and seven-file publication verification remain with the owner.
