# Phase 69 history

Append only. Entry types: `[DECISION]` `[SCOPE_CHANGE]` `[DISCOVERY]` `[FEATURE]`
`[ARCH_CHANGE]` `[EVALUATOR]` `[NOTE]` — as phase 68's log sets out.

---

### [DECISION] 2026-10-16 — A screencast of the owned target, not a virtual desktop
Topics: browser-pane, screencast, cdp, origin-boundary
Affects-phases: phase-69-the-browser-pane
Affects-specs: specs/decisions/0001-optional-workbench-packs.md#decision
Detail: Settled by research on 2026-10-04 and recorded here as the phase's starting decision. The
owned engine can open a CDP session through its own context, so frames cost no new dependency;
they arrive per tab, matching the tab identity the engine already keeps; and the approach works on
both platforms the gate runs, where an Xvfb and VNC stack is Linux-only. The deciding reason is
governance rather than convenience: a whole virtual desktop would let a person step outside the
governed browser and discard the origin boundary ADR 0001 spent three amendments earning, where a
screencast-driven page still passes through the gateway.
One correction carried forward: ENH-053 said the engine *already* opened a CDP session. That was
true of the replacement candidate retired in 0.48.0 and is no longer true of the tree. The
conclusion survives — Playwright exposes it — but the premise was stale and is fixed in the row.

---
