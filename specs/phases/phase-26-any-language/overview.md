---
type: Phase
phase: 26
name: any-language
epic: 0015-any-language
status: in-progress
topics: [wire, thread, serve, stdio, http, typescript, handles, parity, store]
deps: [phase-25-the-hosts-controls]
---

# Phase 26 — Any language

**One harness behind a protocol powers every surface** (`planning/the-substrate.md` §1.1). OpenAI
pulled Codex's agent core into a server with a documented protocol because *"every new surface
re-implemented the agent"*; Anthropic's answer for a language its SDK does not cover is *"run the
CLI as a subprocess"*. Ours is the same shape, already half-built: the wire (D21) puts the loop
behind JSON-RPC and inverts the ports; the schemas are published and held by an invariant. What a
host in TypeScript, Go or Rust cannot do today is **hold a thread, answer an approval, switch a
mode, or read the store** — the host's controls (Phase 25) exist in-process only.

This phase carries them across. The wire's unit becomes the **thread**; every host handle crosses
— approvals, input requests, `set_mode`/`set_option`, `steer`/`interrupt`, cancellation — and the
parity invariant is extended from `RunContext` methods to handles and thread operations; the
store's CRUD crosses; activity streams beside events; `shadow-hdk serve` runs it over stdio
(Codex's default) or HTTP/SSE from one `harness.toml`; a TypeScript package is generated from the
schemas at build time with a thin client; and the studio is rewritten to consume the wire and
nothing local — the proof that a product in another language can.

## What this phase makes true

- A host in any language opens a thread, turns it, sees items and activity as they happen, answers
  the policy's approval requests and the agent's input requests, switches modes, forks and resumes,
  and reads and writes the store — over stdio or HTTP, with generated types.
- Nothing a Python host can do with a thread is out of a TypeScript host's reach: an invariant
  says so.
- The studio is a client of the wire, not of the runtime.

## Out of scope

- The facade (`Harness.load`) and batteries — Phase 27; `serve` reads only what it needs now.
- WebSocket — a product that needs it adds a transport; stdio and HTTP/SSE are the two every
  reference implementation ships.
- Generating clients for a third language — the schemas are the contract; TypeScript is the proof.
