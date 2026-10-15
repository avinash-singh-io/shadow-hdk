---
type: Retrospective
---

# Phase 70 — the token ceiling

Released as **0.51.0**. Closes ENH-052 and the audit's H33/H34.

## What it changed

A lease capped steps, seconds and cents and not tokens, so a product budgeting in tokens could not
cap a run and a long thread walked into the model's context window with nothing to stop it. Phase 65
recorded that debt in the same change that created it.

`Ceiling` gains `max_tokens`, enforced inside the predicate that already stops a run out of money
rather than beside it, and reported by `remaining`. Three judgements. **Unknown is unknown** — a
ceiling enforced on numbers a provider never gave would exhaust runs for arithmetic nobody did,
which is worse than no ceiling. **A carve clamps rather than raises**, like the clock and unlike
money, because a parent near its limit would otherwise refuse every child for asking a round number
and the parent's own meter still stops the run. **Cache tokens count**, since D141's tokens are
tokens and a budget ignoring them lets a warm cache run past what was charged.

And the loop now folds its own transcript when the budget is nearly gone, before the request is
built — afterwards there is no room left to send what the fold produced. The threshold rides on the
pattern and defaults to never, because folding is lossy. H34 closed with it: `compact` was in no
shipped pattern's meta tools, so the one way compaction could happen was unavailable everywhere a
product starts from. `reflect-until` offers it now, being the pattern whose transcript grows.

## What the gate caught that scoped runs did not

Four failures, all consequences of changing a kernel contract: three published schemas and a
TypeScript client gone stale, and a wire control comparing the whole serialized budget — which is
exactly why it compares the whole shape, so a field appearing is seen rather than assumed. The
remedy was regeneration, not argument.

**And the fold's call site was written and left uncalled.** Every control passed, because each
invoked the method directly. Third time in this release train — a wait in 0.48.0, a hand-over in
0.49.0, this. The control that catches it reads the turn loop's source, since one that calls the
method cannot tell the difference.

## Verification Evidence

SHADOW_HDK_TEST_CODEX=1 SHADOW_HDK_BROWSER_TESTS=1 SHADOW_HDK_BROWSER_INSTALL_TESTS=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/hdk67-browser-binaries uv run --all-extras pytest -q — exit 0 (recorded below after the regeneration)

uv run ruff check · ruff format --check · mypy — exit 0; schemas and the TypeScript client
regenerated and checked in; `tsc` and the client build exit 0; version lockstep at 0.51.0 across the
four places.

Mutation evidence: ceiling 7/7, compaction 5/5 — twelve biting, two of them only after a gap the
first pass exposed.
