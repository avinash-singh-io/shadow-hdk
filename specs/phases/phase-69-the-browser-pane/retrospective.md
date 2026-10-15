---
type: Retrospective
---

# Phase 69 — the browser pane

Released as **0.50.0**. Builds ENH-053.

## What it changed

ADR 0001 built the browser pack headless and isolated, which left out the half a product needs: a
person watching the page, taking the keyboard when a flow needs a human, and opening their own
development server. Three mechanisms now, and no kernel change.

**A control lease**, per resource scope. The agent drives until a person takes the keyboard; acts on
the page are then refused by name, reading never is, and the handover goes on the record — because
while somebody else is driving, the agent's governance is not what gates the page, and that is a
fact a record must carry rather than a toggle in a user interface.

**Frames out of an owned tab**, acknowledged as the backpressure, one slot with a count of what was
superseded, handed over once, stopping idempotently. A screencast of the owned target rather than a
virtual desktop, and the deciding reason is governance: a desktop would let a person step outside
the governed browser and discard the origin boundary ADR 0001 spent three amendments earning.

**A person's input** through the page's own debugging session, which is what keeps them inside that
boundary. A click presses and releases; typing goes character by character, so a page reacting per
keystroke behaves as under real hands.

**A served job is browsable**: a verified listener becomes a url the origin policy already allows.
Verified only, because a url scraped from output is a guess; loopback only, because a job on a
routable interface is somebody else's reach into this run. The seam joins two halves and widens
nothing.

## What the mutations found

Four gaps, each in work that looked finished. A frame was not asserted to be handed over *once*. A
running-guard could not be made to fail and was removed rather than kept, since unprovable code is
the kind that gets believed. The preview seam's `verified` flag was never what refused its test
fixture, which lacked a host and port and was rejected for being incomplete. And a write action
could have escaped the lease, which is why the withheld list is named rather than derived.

## Verification Evidence

SHADOW_HDK_TEST_CODEX=1 SHADOW_HDK_BROWSER_TESTS=1 SHADOW_HDK_BROWSER_INSTALL_TESTS=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/hdk67-browser-binaries uv run --all-extras pytest -q — exit 0

```text
2424 passed, 32 skipped, 25 deselected, 85 warnings in 564.66s (0:09:24)
```

uv run ruff check · uv run ruff format --check · uv run mypy — exit 0

```text
All checks passed!
565 files already formatted
Success: no issues found in 565 source files
```

Mutation evidence: lease 6/6, frames 7/7, input 5/5, preview 3/3 — twenty-one biting, four of them
only after a gap the first pass exposed was closed.

Version lockstep at 0.50.0 across the four places the tree holds it.
