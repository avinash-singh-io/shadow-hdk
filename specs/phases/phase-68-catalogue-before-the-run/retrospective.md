---
type: Retrospective
---

# Phase 68 — the catalogue before the run

Released as **0.49.0**. Closes TD-023.

## What it changed

A listing was served only out of the attached run, and a run attaches inside the turn — so a
resident provider that asked for its tools at startup was told, correctly, that there were none,
and composed its first request from that. 0.48.0 announced the catalogue when it became available,
which helps a provider that re-reads before composing and not one that does not; the gate caught
exactly that, reporting `we offered: ('read_file',)` against a request carrying none of them.

This phase removes the empty answer instead of correcting it afterwards. The catalogue predicate —
refresh, judge, keep what is not refused — is one function now, read either from a run or from an
open conversation, and the registry answers from the latter when no run is attached. A first
listing that is already right leaves no stale snapshot to compose from.

## What the mutations taught, twice

The first pass found a **D30** gap: dropping the registration's posture and id from the pre-run
context changed nothing that was measured, which would have reopened TD-007's rule — the policy is
told what it is judging, and the host cannot speak for it — on a brand-new path.

The second pass repeated 0.48.0's own lesson almost verbatim. Deleting the call from the open path
left every control green, because each invoked the wiring method directly. **A method existing is
not a method being called**, which is precisely how that release's wait came to be inert. A control
now drives the real open path, and the catalogue's identity is asserted with it.

## Verification Evidence

SHADOW_HDK_TEST_CODEX=1 SHADOW_HDK_BROWSER_TESTS=1 SHADOW_HDK_BROWSER_INSTALL_TESTS=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/hdk67-browser-binaries uv run --all-extras pytest -q — exit 0

```text
2392 passed, 29 skipped, 25 deselected, 85 warnings in 300.55s (0:05:00)
```

uv run ruff check · uv run ruff format --check · uv run mypy — exit 0

```text
All checks passed!
539 files already formatted
Success: no issues found in 557 source files
```

The declared gap deleted, which is this phase's acceptance: the governed-SDK control asserts the
tools arrive with no tolerance path at all, and its narrowness controls are gone with it. A
tolerance kept past its cause is how the next regression hides.

```text
tests/adapters/jsonl/test_the_declared_catalogue_gap_stays_narrow.py — deleted
read_too_late — deleted, 0 references
tests/adapters/jsonl + tests/runtime — 638 passed, 1 skipped
```

Version lockstep at 0.49.0 across all four places the tree holds it — the distribution, the kit's
dependency line on the helper, the crate, and the helper's own distribution.
