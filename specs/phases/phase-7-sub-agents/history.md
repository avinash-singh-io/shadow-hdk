---
type: History
phase: 7-sub-agents
---

# Phase 7 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D16: a held child is a parked run, not a resident object
Topics: sub-agents, held, d16, checkpoints, runtime
Affects-phases: phase-8, phase-9
Affects-specs: specs/architecture/runtime.md, specs/architecture/decisions.md

The obvious reading of `09` §6's *kept resident for the session* is an object: a child runtime left
alive with a queue, messaged through a handle. That is durable state in the runtime by another name
— it does not survive the process, it cannot be resumed by a different host, and it makes "the
session" something the runtime keeps alive rather than something a checkpoint describes. `09` §6
says the runtime owns nothing durable and is disposable by design.

Phase 6 built the alternative and proved it on a file. So a held child is a **parked run**: `spawn`
runs it until it parks, `send` is a `resume` with the message as the answer, `release` cancels it
and settles its lease. Holding costs a lease reservation and nothing else.

Two consequences. The holder remembers the **composition**, because `resume` takes it back in — that
is ephemeral parent state, which the runtime may own. And *without re-paying its brief* is exactly
what the checkpoint buys: the child wakes where it slept.

*Rejected:* a resident child object with an inbox. It reads simpler and is not — it needs a
lifetime, supervision, and an answer for host restart, all of which a checkpoint already gives.

*Overturned by:* a child whose work cannot be expressed as parking, such as one holding an open
socket per message. That child is a **component with a connection**, like the MCP adapter's held
server, and belongs on the component side rather than as a run.

### [DISCOVERY] 2026-09-10 — `Await` never parked
Topics: await, pending, grammar, compiler
Affects-phases: none
Affects-specs: specs/architecture/runtime.md#compiling-a-composition

`specs/architecture/runtime.md` has said since Phase 0 that `Await` compiles to *one node whose
observation may be `Pending`; the parked form is `interrupt()`*. The compiler treats it exactly like
`Invoke`. Measured before building anything on it: a component returning `Pending` from an `Await`
had its observation recorded and the run carried straight on to `Ended`.

`Pending` appeared in the suite only inside a round-trip contract test — it was serialised and
deserialised, and never once made a run wait. Half the grammar's waiting was a type.

Found because held children need a step that waits, which is Group 0.

---
