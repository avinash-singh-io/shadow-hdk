---
type: Evidence
phase: phase-66-the-short-list
group: G5-C
---

# C — stored plan limits, confirmed before implementation

Read at `bab76ba` on 2026-10-04. Pattern already has an optional PlanLimits value. Both child
spawn and deferred-plan admission consume it and meet it with the host's limits (D109).
The loader omits plan from KEYS and never parses the value. A stored row naming it is therefore
skipped as malformed. This is row-to-existing-admission wiring, as the approved G2 design states.

Add plan to the loader and parse with the existing contract loader, as ceiling already does.
Do not add absorb or offload_over. Model and effort remain on the mode. No redesign is needed.

D190: a coding tool, a support desk and a research assistant would each use this. Whole-plan
shape limits are generic; no tool meaning enters the kernel or runtime. The behaviour proof
must count whether planned work ran under a stored bound, not merely assert the parsed field.

## Verification

Six cases failed before implementation on the unknown plan key; ten new cases pass and the
existing admission tests pass beside them. Ten anchored mutations bite, including each axis,
unset limits, malformed limits, refusal and execution under a bound, and both excluded knobs.
The clean installed 0.46.0 wheel passes all ten new cases outside the checkout. All 165 Python
package source files match the wheel. Schemas and TypeScript contracts regenerate without drift.
Full gate with disposable PostgreSQL enabled: 2,248 passed, 8 skipped, 24 deselected, exit 0.
