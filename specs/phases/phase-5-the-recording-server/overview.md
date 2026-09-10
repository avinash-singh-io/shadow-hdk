---
type: Phase
phase: 5
name: the-recording-server
epic: 0002-the-workspace-and-driving-another-agent
status: not-started
topics: [mcp, recording, posture, observed, controlled, provenance, bridge]
deps: [phase-4-the-acp-bridge]
---

# Phase 5 — The RecordingServer

## Goal

**The mirror of Phase 4.** That phase let a child agent ask *us* for things. This offers *our*
registry **to** the child, as an MCP server — so a tool call it makes is a governed step with
provenance, rather than something that happened out of sight.

`09` §8 and `08` §4.6 put it exactly: *the recording MCP server is not a component to build — it is
`RecordingServer` whose tool handlers are judge then commit. **Recording is a consequence of
routing.***

## The idea, taken literally

A handler could re-implement judging and eventing. It does not. **It calls `run()`** with a
one-step composition, as a child of the parent run — and then judgement, the event stream, lease
carving, provenance and forwarding all arrive for free, because they are what a run already does.

```
child agent → MCP tools/call → RecordingServer handler
    → run(Composition((Invoke(call_id, tool, args),)), ports, options=ctx.spawn_options(…))
        → the same governed step as any other
        → Invoked / Observed on the parent's stream
    → the observation, back to the child as MCP content
```

Nothing about recording is a feature. It is what happens when a call is *routed* rather than made.

## What the child is offered

**The run's `visible()` registry — the same list the model sees.** A child cannot be handed a tool
the parent could not use itself, because it is literally the same computation: the registry filtered
by the governance port. A narrowing mode narrows the child too, without anybody wiring it.

## Scope

### In
- `packages/adapters/recording` — an MCP server over the run's visible registry
- Handlers that route through `run()`, so every call is judged, evented and leased
- `posture` — decided, and put where it belongs
- Proven against a **real MCP client** over a real transport

### Out
- Serving it to a *subprocess* child, which needs a listening transport (Phase 9, the wire)
- gVisor and Firecracker (Phase 11)

## Deliverables

| # | Deliverable | Verification |
|---|---|---|
| 1 | `RecordingServer` over the visible registry | `uv run pytest tests/adapters/recording` |
| 2 | A narrowing mode narrows the child, unwired | one test |
| 3 | Every call appears in the parent's stream as a governed step | one test |
| 4 | A refused call reaches the child as a refusal, not a crash | one test |
| 5 | `posture` on `Provenance`, defaulting to `controlled` | `tests/kernel` |
| 6 | A real `ClientSession` drives it end to end | the same |

## Acceptance criteria

- A real MCP client lists tools and gets exactly what `RunContext.visible()` returns.
- Changing the mode changes what the child is offered, with no code between the two.
- A tool the child calls produces `Invoked` and `Observed` in the **parent's** event stream, with the
  child's run id — so a host watching the parent sees what the child did.
- A refused call comes back to the child as an error it can read, and the tool is never executed.
- The lease bounds the child: a child that calls forever is stopped by the parent's ceiling.
