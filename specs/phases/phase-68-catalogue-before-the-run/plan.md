---
type: Plan
---

# Plan — phase 68, the catalogue before the run

## Reference specs

`specs/architecture/runtime.md` (the governed step; modules), `specs/architecture/adapters.md`
(batteries; the modes adapter), `specs/decisions/0001-optional-workbench-packs.md`. Read as a
stable reference; gaps are logged as `[ARCH_CHANGE]` and synced at completion (Rules 9 and 10).

## What the code already gives us

- `RunContext.visible()` refreshes the registry, then judges each registration with a context from
  `session.context_for("<catalogue>", registration)` and keeps what is not refused.
- `Session.context_for` is cheap: the session's own attributes, plus the registration's posture and
  id. It needs no run, no step and no meter.
- `Conversation` holds its ports, its registry source, its mode and its `LeaseMeter` at open.
- `RunContext.step` is already documented as `None` "while the catalogue is read".

So the predicate is separable from the run. What a run adds to the judged context is the turn's own
keys — and that is the whole risk, stated below.

## The risk this phase exists to manage

`bindings.py` says the listing and the executor must resolve against the same registry so that
*what the model was offered* and *what the runtime will let it invoke* cannot drift apart. BUG-235
is what happened when a narrowing was applied to one and not the other. A listing computed without
a run has a context missing the turn's keys, so a policy keyed on them could judge differently.
Therefore: one predicate, used by both paths, and a control that asserts the two agree.

## Groups

### Group 0 — the seam, with the predicate shared
A run-less catalogue reader built from what is known at open: the registry source, the governance
port, the mode and the host attributes. It computes the listing by the **same** function the run
uses, so there is one predicate and not two.
*Verification:* focused controls that the reader returns the run's tools with no run attached.
*Commit:* `feat(runtime): a catalogue readable before a run attaches`

### Group 1 — the two paths proved to agree
A control that computes the listing both ways — before a run and inside one — against the same
components and mode, and asserts they are identical. This is the BUG-235 guard for this phase and
the reason the seam is safe.
*Verification:* the agreement control, plus a mutation that makes one path narrower.
*Commit:* `test(runtime): the pre-run and in-run catalogues are the same catalogue`

### Group 2 — the registry answers it
`RecordingServer` serves the run's listing when a run is attached, and the reader's when one is
not, so a provider asking at startup gets the real catalogue. The empty answer disappears.
*Verification:* the socket controls; a relay that lists before any turn receives the tools.
*Commit:* `feat(recording): answer the real catalogue before a run attaches`

### Group 3 — the declaration removed
The governed-SDK control's declared gap (`read_too_late`) and its narrowness controls are deleted,
because the case they described cannot occur once the first listing is correct. Deleting it is the
acceptance: a tolerance left in place would hide the next regression.
*Verification:* the real governed-SDK control passes with no skip path; its gap controls are gone.
*Commit:* `test(jsonl): delete the declared gap, now that the first listing is correct`

### Group 4 — release 0.49.0
Full gate, benchmarks, schemas and client, wheel and sdist with the artifact asserted, installed
controls outside the checkout, exact-head continuous integration, then land and publish.
*Verification:* the gate set recorded in the retrospective's evidence section.
*Commit:* `chore(release): 0.49.0`

## Not in scope

What a mode shows, or how an effect is judged. This phase changes *when* a listing can be
computed, never *what* it contains — which is also why Group 1 is not optional.
