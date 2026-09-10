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

### [ARCH_CHANGE] 2026-09-10 — Group 1: spawn, send, release, and a tenth event
Topics: sub-agents, held, d16, d9, contract, held-event
Affects-phases: phase-8, phase-9
Affects-specs: specs/architecture/runtime.md, specs/architecture/decisions.md

`RunContext.children` holds the three operations. What the registry keeps is only what a resume
needs and a checkpoint cannot supply: the composition (because `resume` takes the plan back in), the
checkpointer the child parked with, and the child's own `Cancellation` — which is what makes branch
granularity mean anything, since releasing one child must say nothing about its siblings.

The event stream grows a tenth kind, `Held`. Without it a host would infer holding from the
*absence* of `Ended`, and a child that died silently looks exactly the same. Contract change, so
every package moves to **0.5.0** (D9) and it earns a row under *Pins*.

### [DISCOVERY] 2026-09-10 — two things D16 claimed that measurement corrected
Topics: leases, held, await, d16
Affects-phases: none
Affects-specs: none

Both were written into the overview before anything was built, and both were wrong.

**Holding is not a reservation.** The overview said holding costs a lease reservation. It does not:
a parked run settles what it did not spend back to its parent on the way out, so a parent holding a
child with a ceiling of ten gives up the two steps that child actually took. The test asserts both
halves — exactly the steps spent, and far less than the ceiling — because only the second says the
reservation was released.

**Waiting is a step that happened.** An `Await` component is called, answers `Pending`, and *then*
the run parks. A child that parks on its second step has invoked two, not one. The first version of
the test asserted one and failed, which is how the cost above turned out to be two rather than one.

### [DISCOVERY] 2026-09-10 — `Command(resume=None)` raises inside LangGraph 1.2
Topics: langgraph, resume, release
Affects-phases: none
Affects-specs: none

`release` first woke a child with `None`, since the value is never read: the cancellation check is
the first thing a re-run node does, so the run ends `cancelled` without consuming anything. LangGraph
raises on it — `cannot access local variable 'resume_is_map' where it is not associated with a
value` — so the child ended `failed` and reported a variable name instead of saying it was let go.

It now sends a word. Recorded because the fix looks arbitrary without the reason.

### [SCOPE_CHANGE] 2026-09-10 — the model's verbs move to Phase 8, and the mailbox stays here
Topics: meta-tools, d3, patterns, mailbox
Affects-phases: phase-8
Affects-specs: none

The plan had `spawn` / `send` / `release` as **pattern meta-tools** in Group 2. D3 says meta-tools
belong to the Pattern — and that is exactly why they cannot land here. A model-facing `spawn` has to
say what the child *is*: a brief, then a wait, then whatever the role does between messages. That
shape is a pattern, and patterns are Phase 8's subject. Shipping the verbs now would mean inventing
a child shape in the adapter and calling it a default.

What could land, and did, is the thing every such pattern will need: the **mailbox** — the component
a held child waits on — in `adapters/basic`, so a held child's shape is a convention rather than
three lines each host writes under its own name. Its effect profile is empty, and a test proves that
matters: under a mode allowing nothing at all, a child can still be held. A mutation run found that
survivor first — nothing checked the profile, and the docstring was the only thing claiming it.

### [DISCOVERY] 2026-09-10 — our observation classes ride in graph state (TD-001)
Topics: langgraph, checkpoints, serde, tech-debt
Affects-phases: phase-9
Affects-specs: none

A held-child test surfaced a LangGraph warning: it is deserializing
`shadow_hdk.kernel.observations.*` from a checkpoint, and a future version will block it.

Measured rather than guessed: `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q` is green over 353
tests, so nothing breaks today. Two remedies, both in TD-001: a host builds its checkpointer's
serializer with `allowed_msgpack_modules` naming our module, which pushes our internals into every
host's setup; or `RunState` holds plain JSON and the runtime loads it back. The second is the design
answer and belongs with Phase 9 defining what crosses the wire.

---
