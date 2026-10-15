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

### [ARCH_CHANGE] 2026-10-15 — One predicate, two context sources
Topics: catalogue-visibility, governance, offer-port
Affects-phases: phase-68-catalogue-before-the-run
Affects-specs: specs/architecture/runtime.md#the-governed-step
Detail: The catalogue predicate — refresh, judge each registration, keep what is not refused — is
lifted out of `RunContext` into one function, and a `Catalogue` reads it with no run attached from
what is known at open: the components, the policy, the mode and the host's attributes. Deliberately
one predicate rather than two implementations, because `bindings.py` is explicit that the listing
and the executor must not drift apart and BUG-235 is what that drift looks like. A control asserts
the pre-run and in-run listings are identical, which is the only reason the seam is safe to have.
Where there is no run id the conversation's own identity is told instead of a sentinel, so a policy
can still correlate a listing with the turns that follow. The first mutation pass found the D30 gap:
dropping the registration's posture and id from the pre-run context changed nothing that was
measured, which would have quietly reopened TD-007 on a new path. Now asserted, including that a
host setting those names cannot speak for the policy.

---
