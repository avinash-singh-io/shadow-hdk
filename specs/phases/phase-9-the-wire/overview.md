---
type: Phase
phase: 9
name: the-wire
epic: 0003-composition-at-scale
status: complete
topics: [wire, jsonrpc, sse, stdio, serve, schemas, d19, d20, td-001, v0.1.0]
deps: [phase-8-patterns-skills-replay]
---

# Phase 9 — The wire

## Goal

`specs/architecture/wire.md`, built. The runtime becomes reachable from another process or another
language, in two forms — `serve` over HTTP and `--stdio` — and the packages become releasable.

**The version is `v0.6.0`, not `v0.1.0`.** The roadmap named `v0.1.0` at founding. Since then six
contract changes have each moved every package together under D9 — `ModelPort.stream`,
`Provenance.posture`, `Ended.detail`, `Held`, `Spent`, and the state-holds-JSON change — so the
packages are at 0.6.0 and have been for a phase. Releasing as 0.1.0 would mean going backwards
past five recorded contract changes; the plan's number is the stale one.

The spec fixes the shape and this phase does not get to revisit it:

> The host **drives**; the runtime **calls back**. `run` and `resume` are host → runtime. The six
> ports invert: when the runtime needs a judgement, a model completion, a component invocation or a
> sink write, it issues a request the host answers. Events stream host-ward continuously.

And it fixes the acceptance test, which is the hardest sentence in the document:

> **The same suite runs both ways.** The wire passes the in-process runtime suite through a loopback
> transport, or the wire is not done.

## Three debts this phase inherits

| debt | from | what it is |
|---|---|---|
| a **listening** transport | Phase 5 | the RecordingServer can only be connected to, never launched, so a child on another machine has no way in. `serve` is that way in |
| tokens reach the observer | Phase 1 | an exit criterion carried, then carried again when `Held` took the tenth event slot in Phase 7 |
| **TD-001** | Phase 8 | our observation classes ride in graph state, where a future LangGraph will block them |

The first two are the phase's own work. The third is settled below, because it is not a
housekeeping item — it is a decision about what crosses a boundary, which is this phase's subject.

## D19 — the graph's state holds JSON, not our classes

`RunState.observations` holds `Observation` objects. That is convenient in-process and wrong at
every boundary they actually cross.

A checkpoint **is a wire**. It crosses a process (Phase 6 proved a run resuming from a file after
the saver that wrote it was gone), it crosses a version (a run parked by one build and resumed by
the next), and it crosses into a store the host chose and we know nothing about. LangGraph is
already warning that it will stop deserialising types it does not recognise, and the remedy it
offers — a host naming `shadow_hdk.kernel.observations` in its serializer's allowlist — pushes
our internals into every host's setup, which is precisely backwards for a package whose whole claim
is that the host owns the durable side.

So the state holds **JSON**, and the runtime loads observations back at its own edge. The types stay
ours; what crosses stays plain.

*Rejected:* the allowlist. It works, and it makes our module names part of every host's
configuration — a rename would then break somebody else's deployment.

*Rejected:* leaving it until it breaks. It is measured green today under
`LANGGRAPH_STRICT_MSGPACK=true`, which is exactly the window in which to move.

*Overturned by:* a state field whose JSON round-trip is lossy in a way that matters, which would
mean the kernel's contracts are not the whole story and the wire has a second vocabulary.

## D20 — `Spent`, the eleventh event kind: what a step cost, said out loud

Phase 1's exit criterion was *tokens reach the observer*, and they do not. `_usage_of` digs them out
of a `Completed` observation's output dict by convention — `output["usage"]["input_tokens"]` — and
charges the meter. An observer wanting to know what a run cost has to know that convention and parse
somebody else's payload.

`Spent(step, usage)` is emitted where the meter is charged. A meter, a UI and a bill can then read
one event kind instead of reverse-engineering an output.

*Rejected:* a field on `Observed`. Most observations cost nothing, and an optional field that is
usually absent teaches a reader to ignore it. A separate kind appears exactly when there is
something to say.

*Rejected:* leaving it in the output dict. That convention stays — it is how an adapter *reports*
cost — but reporting and recording are different jobs, and the record should not be a convention.

*Overturned by:* a cost that is not a model call — a component billing for something else — which
would mean `Usage` is the wrong shape and the event wants a broader one.

## What is NOT in this phase

- **A TypeScript client.** Schemas are published; a client generated from them is a *client*, never
  a port of the runtime (`09` §3b), and it is not this package's to ship.
- **Authentication beyond the run token.** wire.md fixes the token's shape; a host's own identity
  system is the host's.
- **Tagging the release.** The version is prepared and said to be ready. Tagging is the owner's.

## Exit criteria

- The in-process runtime suite passes **through a loopback transport**, with every port inverted
- `--stdio` speaks the same protocol to a real child process
- `serve` **listens**, and a client that did not launch it can run a composition and watch its events
- `initialize` refuses a version mismatch rather than degrading
- Schemas are published from `all_schemas()`, and a run's observations cross as JSON
- `Spent` reaches an observer with a model call's tokens on it
