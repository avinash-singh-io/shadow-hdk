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

### [FEATURE] 2026-10-16 — The control lease
Topics: browser-pane, control-lease, governance, honesty-fields
Affects-phases: phase-69-the-browser-pane
Affects-specs: specs/architecture/adapters.md#batteries
Detail: Who holds the keyboard, per resource scope, with the handover on the record. Three choices
worth keeping. Reading is never withheld: a person at the keyboard does not blind the agent, and an
agent that cannot read cannot report what it saw happen. The withheld actions are **named** rather
than derived from the write list, with a control failing if the two disagree — deriving them would
let a widening of the contract escape the lease silently, which is this repository's most frequent
defect. And a handover with no run to record into still happens, because the lease is the kit's own
state and a host taking over between turns must not be refused for having no run.
Refused rather than failed, and said plainly: who drives is a decision, not an error. The refusal is
also decided before any browser is provisioned, so a product can rely on it without a running
Chromium. Six mutations bite.

---

### [FEATURE] 2026-10-16 — Frames out of an owned tab
Topics: browser-pane, screencast, cdp, backpressure
Affects-phases: phase-69-the-browser-pane
Affects-specs: specs/architecture/adapters.md#batteries
Detail: Verified against a real Chromium before anything was written on top of it: a debugging
session opened through the engine's own context delivers frames carrying the image, the browser's
metadata and the session id an acknowledgement needs. The acknowledgement *is* the backpressure —
without it the stream dries up after a few frames — and it is deferred out of the browser's
synchronous handler to the moment a viewer actually takes the frame, so the browser is told to
continue exactly when somebody is ready for more.
One slot, not a queue, with a count of what was superseded, because a viewer that falls behind wants
the page as it is rather than a record of how it was. The slot is consumed on handover: leaving a
frame in place would show the same image until a new one arrived, which reads as a stalled page
rather than an unchanged one, and those want different reactions.
The first mutation pass found two gaps. Nothing asserted that a frame is handed over once. And the
running-guard in `next` could not be made to fail, because stopping already empties the slot — so it
was removed rather than kept, since unprovable code is the kind that gets believed. Seven mutations
bite now.

---

### [FEATURE] 2026-10-16 — A person's input into the page
Topics: browser-pane, control-lease, origin-boundary
Affects-phases: phase-69-the-browser-pane
Affects-specs: none
Detail: Clicks and keys through the page's own debugging session, which is what keeps a person
inside the governed browser — the page they type into is the page whose traffic passes the origin
gateway, and that is the reason the pane is a screencast rather than a desktop. Refused unless the
lease is theirs, asked before anything is dispatched: a product able to send input without holding
the keyboard would have a pane that bypasses what the pane exists to make visible.
Three details that are the difference between working and nearly working. A click presses *and*
releases, since a press alone leaves the page holding a button nobody is pressing. Typing goes
character by character rather than as one paste, so a page that reacts per keystroke behaves as it
would under real hands. And an unknown action is refused by name before the browser's state is
consulted, so a caller's mistake is not hidden behind "no page is open". Five mutations bite.

---
