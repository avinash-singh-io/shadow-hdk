---
type: Phase
status: in-progress
tags: [browser-pane, screencast, control-lease, preview, cdp, resource-scopes]
---

# Phase 69 — the browser pane

Releases **0.50.0**. Builds ENH-053.

## Why

ADR 0001 built the browser pack headless and isolated, which is right for governance and leaves out
the half a product needs: a person watching the page the agent is working on, taking the keyboard
when a flow needs a human, and opening their own development server. Every current agent system
that does this does one of two things — stream a screencast of the owned page, or stream a whole
virtual desktop — and the choice is not a matter of taste here.

## The transport, and why

**A screencast of the owned target, not a virtual desktop.** The owned engine can open a CDP
session through its own context, so frames cost no new dependency; frames arrive per tab, which
matches the tab identity the engine already keeps; and it works on both platforms the gate runs,
where an Xvfb and VNC stack is Linux-only. Decisively, a whole desktop would let a person step
outside the governed browser entirely and discard the origin boundary that ADR 0001 spent three
amendments earning — where a screencast-driven page still passes through the gateway.

Known limits to design around rather than discover: frames must be acknowledged for backpressure
and only the newest kept, and the stream reaches only the window's real device scale factor, so it
blurs under viewport emulation.

## The shape

Mechanism here, policy and content in the product (the boundary rule). Three pieces, no kernel
change:

- **Frames out** of an owned target, over the transport the kit already serves.
- **An input seam in**, so a person's click reaches the page.
- **A control lease** naming who may drive, with the transition on the record.

The lease is the load-bearing idea. While a person drives, the agent's governance is not what gates
the page, so that is a fact the record must carry rather than a toggle in a user interface — the
same reasoning that made a dropped agent report itself rather than vanish. The product keeps the
pane, the take-over button, the allowed origins and the launch configuration.

## Also in scope

The **preview seam**: a person's own development server is nearly built already — the background
jobs of phase 67 and the gateway's loopback default are the two halves, and only the join is
missing.

## Not in scope

The token ceiling and compaction (ENH-052, phase 70). Any widening of what the gateway allows: a
person driving is still inside the origin boundary, and this phase does not touch it.

## Acceptance

- Frames leave an owned tab and stop when its resource scope closes.
- A person's input reaches the page only while the lease is theirs, and the record says who drove.
- A development server started as a background job is reachable in the governed browser without
  the host naming an origin by hand.
- Every assertion mutation-checked; the full gate and exact-head continuous integration green.
