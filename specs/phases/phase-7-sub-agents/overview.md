---
type: Phase
phase: 7
name: sub-agents
epic: 0003-composition-at-scale
status: not-started
topics: [sub-agents, spawn, send, release, held, branch-cancel, await, pending, d16]
deps: [phase-6-the-compiler-complete]
---

# Phase 7 — Sub-agents

## Goal

`09` §6 states the whole of it in four sentences:

> A sub-agent is a component of label `agent`. Invoking it spawns a child runtime with the brief as
> input, a lease carved from the parent's, and governance narrowed to the parent's denials. A child
> can be **held**: kept resident for the session and messaged again without re-paying its brief. A
> child can be **cancelled** at branch granularity. Three operations: **spawn, send, release**.

Spawning has existed since Phase 0 (D2 — a run started inside a step is a child). The other two
have not, and neither has holding. This phase builds them.

## D16 — a held child is a parked run, not a resident object

The obvious reading of "kept resident for the session" is an object: a child runtime left alive in
memory with a queue, messaged through a handle. That is wrong here for a reason the design has
already settled twice.

`09` §6 says the runtime **owns nothing durable** and is **disposable by design**. A resident object
is durable state in the runtime by another name: it does not survive the process, it cannot be
resumed by a different host, and it turns "the session" into something the runtime has to keep
alive rather than something a checkpoint describes. Phase 6 built the alternative and proved it on
a file — a run parks, and a resume continues it without the process that parked it.

**So a held child is a parked run.** `spawn` starts it and lets it run until it parks or ends;
`send` is a `resume` with the message as the answer; `release` cancels it and settles its lease.
Holding costs a lease reservation and nothing else, and a host that dies loses no child it could
not restore from its own checkpointer.

Two consequences worth naming:

1. **The holder remembers the composition.** `resume` takes the composition back in (`09` §6), so
   the parent's `Children` registry keeps it alongside the run id. That is ephemeral parent state,
   which the runtime is allowed to own.
2. **"Without re-paying its brief" is what the checkpoint buys.** The child does not re-run the
   steps it already took; it wakes where it slept, which is exactly what Phase 6 measured.

*Rejected:* a resident child object with an inbox. It reads as simpler and is not: it needs its own
lifetime, its own supervision, and a story for what happens when the host restarts — three things a
checkpoint already answers.

*Overturned by:* a child whose work cannot be expressed as parking — something holding an open
socket per message, say. That would mean the child is a **component with a connection**, like the
MCP adapter's held server, and belongs on the component side rather than as a run.

## Branch-level cancel

Each held child gets its own `Cancellation` (D15) rather than inheriting the parent's. Cancelling
one child stops it and leaves its siblings and its parent running; cancelling the parent's handle
still stops every child that inherited it.

**What is not offered, and why:** cancelling one arm of a `FanOut` *within a single graph*. The
arms are nodes of one LangGraph invocation, and stopping one without the others is not something
the engine offers — D12 says the engine executes and we compile, so this is a place we take what it
gives. A composition that needs independently killable branches spawns them as children, which is
what "branch granularity" means here.

## What this phase found first

`Await` never parked. The architecture has said since Phase 0 that its parked form is `interrupt()`,
and the compiler treats it exactly like `Invoke`: a component returning `Pending` had its
observation recorded and the run carried on to `Ended`. `Pending` appeared only in a round-trip
contract test — nothing had ever exercised it. Held children need a step that waits, so Group 0
makes `Await` park.

## Exit criteria

- A component returning `Pending` from an `Await` parks the run under its handle; a resume delivers
  the answer as that step's observation
- A parent can spawn a child that parks, send it a message it answers without re-running its earlier
  steps, and release it
- Cancelling one held child leaves its siblings and its parent alone
- The record says a child is held, and what it is holding
