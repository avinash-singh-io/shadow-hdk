---
type: Tasks
phase: 23
---

# Tasks — Phase 23

## Group 1 — the agent over the wire
- [x] `visible()` crosses; a catalogue builds host-side from it
- [x] `floor_met()`, `spawn_options()` cross
- [x] `children.spawn` / `send` / `release` cross; a child's events reach the host
- [x] a `single` pattern runs over the loopback wire and emits `Reasoned`
- [x] an orchestrator spawns a sub-agent over the wire

## Group 2 — parity
- [x] the invariant: every `RunContext` method crosses or is named with a reason
- [x] every event kind is in the published schemas; `Step` is published

## Group 3 — the socket
- [x] a per-run token minted with `secrets`; the relay sends it first
- [x] a wrong token is refused and counted; the right one serves
- [x] the token appears in no log, event or `Available`

## Group 4 — a host
- [x] a host example under examples: governance, sink, checkpointer handed in; steps rendered; provider chosen
- [x] BUG-019: the child dies with the process, whatever ended it; proven in a subprocess
- [x] the coder example's REPL closes on `KeyboardInterrupt`

## Group 5 — on demand
- [x] `workflow_dispatch` live job; the documented command
- [x] Codex installed locally and measured (signed out — the signed-in shapes stay transcribed; owner-gated); `codex.toml` updated honestly

## Close
- [x] D51–D53; index
- [x] status, roadmap, changelog, README, board (board after landing)
