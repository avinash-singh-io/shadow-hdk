---
type: Retrospective
status: complete
epic: production-boundary
---

# Phase 31 retrospective — A host knows what it can trust

## Outcome

Phase 31 establishes one evidence-backed selection decision at every construction door. Provider
facts, effective environment facts and host requirements are different immutable types. Unknown
never satisfies an explicit requirement; a refusal carries every mismatch and the evidence used.
The same accepted selection or typed refusal now reaches direct Python, `Harness`, `ServeHost`,
protocol 2 and the generated TypeScript client. Existing callers that state no requirements retain
the 0.29.1 behavior without that compatibility default being represented as a safety claim.

This is the first checkpoint of Epic 0008. It is complete, pushed and unreleased. Intent Studio was
not modified, and no phase tag or package release was created.

## Test-first evidence

| Group | RED observed before implementation | GREEN evidence |
|---|---|---|
| 0 — capability algebra | import failed because `CapabilityEvidence` and the capability vocabulary did not exist | 32 focused kernel/schema tests; Ruff and mypy green |
| 1 — provider truth | seven failures covered absent facts, nested validation paths, shipped matrices and detection exposure | 90 provider/kernel tests; Ruff and mypy green |
| 2 — environment truth | strict requirements could not produce a typed incompatibility | 83 broader environment tests; 12 focused live-file passes; one expected inverse-platform skip; Ruff and mypy green |
| 3 — every construction door | seven failures named missing host/facade arguments, retained selection and wire discovery/check methods | 229 serve/wire/client tests with one expected skip; TypeScript generation/build, Ruff and mypy green |
| 4 — docs and closeout | document/schema/parity checks were run against the unsynchronized contract | 53 focused checks before closeout; 55 explicit document/decision/schema/benchmark checks on the final docs |

## Final verification evidence

- Build environment: `uv sync --all-packages --all-extras` — 137 packages resolved, 130 checked.
- Lint: `uv run ruff check .` — all checks passed.
- Formatting: `uv run ruff format --check .` — 473 files already formatted.
- Types: `uv run mypy` — no issues in 422 source files.
- Full non-live suite: `uv run pytest -q` — 1,600 passed, 12 skipped, 12 live deselected.
- Explicit invariants: documents, decision index, schema drift and benchmark — 55 passed.
- Wire parity checkpoint — 6 passed.
- Project policy: `momentum config validate` — project and active-run policies valid.
- Spec bundle: `momentum okf check .` — 185 Markdown files conformant.
- Backlog learnings: 75 rows and 33 documents scanned; no recurring pattern inferred.

## Findings closed during the phase

- BUG-045: the schema publisher's default escaped the one-distribution repository. The exact target
  is now tested and the accidental external generated directory was removed after inspection.
- BUG-046: the configured build command removed optional adapter dependencies before full
  pytest/mypy collection. The command now installs all packages and all extras, matching CI.
- BUG-047: two historical files violated current OKF metadata rules. Only their classification
  metadata changed; their historical content remains intact.

## What changed in the plan

No epic decision changed. The generated momentum run manifest said `release=per-phase` despite the
epic's `policy_release=per-feature`; the epic and the owner's explicit instruction remained
authoritative. Consequently this checkpoint has no tag, version bump, protected-branch landing or
Intent Studio handoff. The final approval will cover the accumulated Phase 31–33 diff and v0.30.0
candidate.

## What carries forward

Phase 32 consumes the accepted capability selection for both API-model and CLI agent paths. Phase
33 keeps capability facts separate from authority: a compatible provider/environment pair still
cannot authorize an irreversible effect. Both phase specifications are derived with strict TDD
groups and one final epic release boundary.
