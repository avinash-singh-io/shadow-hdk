---
type: Tasks
phase: 23
---

# Tasks — Phase 23

## Group 1 — the agent over the wire
- [ ] `visible()` crosses; a catalogue builds host-side from it
- [ ] `floor_met()`, `spawn_options()` cross
- [ ] `children.spawn` / `send` / `release` cross; a child's events reach the host
- [ ] a `single` pattern runs over the loopback wire and emits `Reasoned`
- [ ] an orchestrator spawns a sub-agent over the wire

## Group 2 — parity
- [ ] the invariant: every `RunContext` method crosses or is named with a reason
- [ ] every event kind is in the published schemas; `Step` is published

## Group 3 — the socket
- [ ] a per-run token minted with `secrets`; the relay sends it first
- [ ] a wrong token is refused and counted; the right one serves
- [ ] the token appears in no log, event or `Available`

## Group 4 — a host
- [ ] a host example under examples: governance, sink, checkpointer handed in; steps rendered; provider chosen
- [ ] BUG-019: the child dies with the process, whatever ended it; proven in a subprocess
- [ ] the coder example's REPL closes on `KeyboardInterrupt`

## Group 5 — on demand
- [ ] `workflow_dispatch` live job; the documented command
- [ ] Codex installed locally and measured; `codex.toml` updated honestly

## Close
- [ ] D51–D53; index
- [ ] status, roadmap, changelog, README, board
