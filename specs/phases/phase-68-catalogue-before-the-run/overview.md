---
type: Phase
status: in-progress
tags: [catalogue-visibility, governed-launch, tool-attachment, offer-port, codex, mcp]
---

# Phase 68 — the catalogue before the run

Releases **0.49.0**. Closes the remainder of TD-023.

## Why

0.48.0 made a governed run say when its tools never reached the provider. It did not make them
reach it. The mechanism, established by measurement rather than argument:

A listing is served out of the **attached run**, and a run attaches **inside the turn**. So before
the first prompt there is nothing to list, and the honest answer is empty — which is exactly what a
provider that asks at startup receives. The change notification fires for roots and for a mode
change, never for a catalogue that has only now become available. Both sides then behave correctly
and the agent has no tools.

0.48.0 added the announcement, which makes a provider re-read, and that is enough when the provider
re-reads before composing. It is not enough when the provider composes from the list it already
holds. The continuous-integration gate showed exactly that: `we offered: ('read_file',)` while the
provider's request carried none of them. **The kit cannot see that request, so it cannot even name
it** — the one case left undeclared, and the reason this phase exists.

The fix is to remove the empty answer. If a provider's **first** listing is already correct, there
is no stale snapshot to compose from and no correction to arrive too late.

## Scope

A registry that can answer the real catalogue before a run attaches, using the same predicate a
run would, so that **what the model was offered and what the runtime will let it invoke cannot
drift apart** (`bindings.py`, and BUG-235 is what happens when they do).

What is known at open and what is not: the components, the mode and the session are known; only
the run is not. `RunContext.context()` already delegates to the session, and the step is already
documented as `None` "while the catalogue is read" — so this phase exposes a seam the design
anticipated rather than inventing one.

## Not in scope

The browser pane (ENH-053, phase 69). The token ceiling and compaction (ENH-052, phase 70). Any
change to what a mode shows or to how an effect is judged — this phase changes *when* a listing can
be computed, never *what* it contains.

## Acceptance

- A provider's first listing carries the run's tools, with no run attached and no notification.
- The pre-run listing and the in-run listing agree, asserted against the same predicate, so the
  drift BUG-235 describes cannot reappear.
- The real governed-SDK control passes **without** the declared gap, and the declaration is
  removed rather than left as dead tolerance.
- Every assertion mutation-checked; the full gate and exact-head continuous integration green.
