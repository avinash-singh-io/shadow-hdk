---
type: Phase
phase: 23
name: a-host-in-any-language
epic: 0012-a-host-in-any-language
status: in-progress
topics: [host, wire, parity, socket, authentication, live-proof, codex, bug-019]
deps: [phase-21-the-visible-agent, phase-22-the-environment]
---

# Phase 23 — A host, in-process and in any language

This is the consumable line. Past it the runtime is something a host adopts; before it, something a
host watches being built.

Two hosts, and both have to be first-class:

**In-process.** A Python application imports the runtime and hands in its own governance, its own
sink, its own checkpointer, and a provider by key or by subscription. It renders the visible-agent
projection. Nothing about its domain reaches the runtime. This is what the ports were for from
Phase 0, and the example that proves it is generic — a host, not a product.

**Over the wire.** A host in another language drives the same runtime through the wire (D21) and
gets the same run: every event kind, the projection already folded, resume, the registry offered
outward. Phase 21 found that the agent adapter **cannot run over the wire at all** — four things
it needs from its context do not cross. Parity is not a slogan; it is those four crossing, and an
invariant that keeps the wire's published surface equal to the kernel's.

## What this phase makes true

**The agent runs over the wire.** `visible()`, `floor_met()`, `spawn_options()` and `children`
cross back to the runtime the way `propose` and `reasoned` already do — one record, one author. A
`single` pattern and an orchestrator with sub-agents both run with the host on the other side of a
socket, and produce the events they produce in-process.

**Parity is an invariant.** Every `RunContext` method either crosses or is listed with the reason
it cannot; every event kind is in the wire's published schemas; the projection crosses folded.

**The registry socket is authenticated (D44's debt).** A per-run token from `secrets`, carried in
the relay's environment, sent as the first line before any MCP traffic, checked before the relay is
served. A wrong token is refused and counted; the token never appears in a log or an event.

**A provider's child dies with the session that spawned it (BUG-019).** Two `claude -p` children
were found alive ten hours after their sessions ended, holding subscription seats. A session is a
step's obligation one level up (D35): however the thing that opened it ends — return, exception,
`KeyboardInterrupt` in a blocking `input()` — the child is ended.

**The live proof runs on demand.** A `workflow_dispatch` job and a documented command run the
subscription-backed proofs when somebody with the CLI asks; they skip, saying why, everywhere else.

**Codex is measured where it can be.** Installed locally into the scratchpad (never globally); its
version and CLI shape measured; its authentication left marked unverified if no login exists.

## What is deliberately not here

A UI. Any product's domain. Streaming model tokens over the wire (D14's one-chunk default holds;
token streaming is a later parity item, recorded).
