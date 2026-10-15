# Phase 68 history

Append only. Entry types:

| Type | When |
|---|---|
| `[DECISION]` | an ADR was created, or its status or decision changed |
| `[SCOPE_CHANGE]` | scope was added to or reduced |
| `[DISCOVERY]` | a bug, debt or enhancement was found and filed |
| `[FEATURE]` | a feature was added to the phase plan |
| `[ARCH_CHANGE]` | an architectural pattern or integration approach changed |
| `[EVALUATOR]` | a locked evaluator was defined or its set changed |
| `[NOTE]` | anything else worth a future reader's time |

---

### [NOTE] 2026-10-15 — Why this phase is separate from 0.48.0
Topics: catalogue-visibility, tool-attachment, governed-launch
Affects-phases: phase-68-catalogue-before-the-run
Affects-specs: none
Detail: 0.48.0 made a governed run *say* when its tools never reached the provider; it did not make
them reach it. One case was left undeclared because the kit cannot see it from inside: the gate
reported `we offered: ('read_file',)` while the provider's request carried none of them, so it had
read the catalogue too late to use it. The fix is to remove the empty answer rather than to correct
it afterwards — a first listing that is already right leaves no stale snapshot to compose from.
Held out of 0.48.0 deliberately: computing a listing outside a run touches how visibility is judged,
and `bindings.py` is explicit that the listing and the executor must not drift apart, which is a
design change and not a line in a release.

---
