---
type: Status
---

# Project Status

> **Last Updated**: 2026-09-10
> **Current Phase**: Phase 0 — The runtime, the bare test goes green — `not started`
> **Latest Release**: None (every package 0.0.1; 0.1.0 at Phase 0's end)
> **Health**: On Track

## Summary

shadow-hdk is the generic agentic system designed in
`intent-ecosystem/vision/09-the-agentic-system.md`: a runtime that runs an agent over an open set of
components under a governance policy and hands what it produces to whoever is listening. It governs
effects, not names; the agent's plan is data compiled to a LangGraph graph; the runtime acts through
components and records through the sink. Three packages — kernel, runtime, adapters — one import
name, six ports. Intent Studio is its first user (lane P, joining at R3); any system that implements
the six ports is its intended user. The kernel exists and is green (`0ca2d2b`); Phase 0 builds the
runtime that turns the bare-harness test green.

## Completed Phases

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| 0 | The runtime, and the bare test goes green | Complete, unmerged (2026-09-10) | — |
| 1 | Real adapters, streaming, modes | Complete, unmerged (2026-09-10) | — |
| 2 | The spike — J1 | Complete, unmerged (2026-09-10) | — |
| 3 | The workspace, and code | Complete, unmerged (2026-09-10) | — |
| 4 | The ACP bridge | Complete, unmerged (2026-09-10) | — |

## Ad-hoc / Patch Releases

| Version | Date | Type | Summary |
|---------|------|------|---------|
| _(none yet)_ | | | |

## Active Phase

| Phase | Branch | Status | Progress |
|-------|--------|--------|----------|
| 0 — the runtime | `phase-0-the-runtime` | **complete, unmerged** | 6 / 6 groups. Superseded as the active row by Phase 1, which branches from it. |
| 1 — real adapters | `phase-1-real-adapters` | **complete, unmerged** | 4 / 4 groups. Superseded as the active row by Phase 2, which branches from it. |
| 2 — the spike | `phase-2-the-spike` | **complete, unmerged** | J1 answered. Superseded as the active row by Phase 3. |
| 3 — the workspace and code | `phase-3-workspace-and-code` | **complete, unmerged** | Superseded as the active row by Phase 4. |
| 4 — the ACP bridge | `phase-4-the-acp-bridge` | **complete, unmerged** | 3 / 3 groups. Superseded as the active row by Phase 5. Another agent as a governed component: fourteen client doors judged, refusals in the agent's own vocabulary, our clock over their runaway, money accumulated before converting. 302 tests; mypy strict over 61 files. What Codex and Claude Code do is still unmeasured. |
| 5 — the recording server | `phase-5-the-recording-server` | **complete, unmerged** | 3 / 3 groups. Superseded as the active row by Phase 6. Our registry offered to a child agent as an MCP server: what it does is on the parent's record because it was routed. Proven over a real `ClientSession` and over a real OS subprocess. 326 tests; mypy strict over 67 files. A child on another *machine* still needs a listening transport → Phase 9. |
| 6 — the compiler, complete | `phase-6-the-compiler-complete` | **complete, unmerged** | 3 / 3 groups. Superseded as the active row by Phase 7. A nested composite is a subgraph with a name of its own; a host can stop a run and the record says who asked (D15); a parked run survives the process that parked it, proven on a file. 343 tests; mypy strict over 70 files. Subgraphs cost 0.607 ms/step against D11's 1 ms. |
| 7 — sub-agents | `phase-7-sub-agents` | **complete, unmerged** | 3 / 3 groups. Superseded as the active row by Phase 8. Spawn, send, release over parked runs (D16): a held child is a checkpoint, not a resident object. `Await` now actually parks — it never had. The tenth event kind, `Held`. 354 tests; mypy strict over 73 files. The model-facing verbs move to Phase 8, because a `spawn` a model can call has to say what the child *is*, and that is a pattern. |
| 8 — patterns, skills, replay | `phase-8-patterns-skills-replay` | **complete, unmerged** | 5 / 5 groups. Superseded as the active row by Phase 9. Patterns and skills are TOML files a team can write (D17); a skill is checked against `visible()` before the first turn; D13's last mechanism is built (`describe`); a run replays for nothing; and compaction plus the `spawn` / `send` / `release` verbs land as meta-tools (D18). 401 tests; mypy strict over 79 files. |
| 9 — the wire | `phase-9-the-wire` | **in progress** | 2 / 5 groups. D19 the state holds JSON and D20 `Spent` (group 0); the ports invert over a loopback carrying JSON text, with D21 binding a context for a component that crossed (group 1). 417 tests; mypy strict over 83 files. Left: `--stdio`, `serve` which listens, and the schemas plus v0.1.0. |

## Upcoming Phases

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|-----------------|
| 1 | Real adapters, streaming, modes | Not Started | `adapters/langchain`, `adapters/mcp`, `adapters/modes`; the demo on real components |
| 2 | The spike | Not Started | J1 answered over `agent-client-protocol` |
| 3 | The workspace and code | Not Started | files and a subprocess sandbox as components |
| 4–5 | The ACP bridge, the RecordingServer | Not Started | your subscription answers the turn |
| 6–9 | The compiler complete, sub-agents, patterns, the wire | Not Started | R3's join; `v0.1.0` |

## Blockers

| ID | Description | Severity |
|----|-------------|----------|
| _(none)_ | | |

## Critical Items (P0)

| ID | Type | Description |
|----|------|-------------|
| _(none)_ | | |

## Next Actions

1. Phase 9, Group 1 — the protocol and the loopback: `initialize` refusing a version mismatch, the five inverted ports, and wire.md's acceptance test — *the in-process runtime suite passes through a loopback transport, or the wire is not done*
2. Phase 9, Groups 2–4 — `--stdio`, then `serve` which **listens** (Phase 5's debt), then the published schemas and v0.1.0 prepared. **Tagging is the owner's**
3. Phases 10–14 in roadmap order; the environment epic after
3. Carried to Phase 9, each with what would settle it: tokens reaching the observer (the tenth event kind arrived in Phase 7 as `Held`, so this still needs its own); a **listening** transport (streamable HTTP) for a child on another machine, since the recording server can only be connected to, never launched; and **TD-001**, our observation classes riding in graph state where a future LangGraph will block them

## Key Decisions Made

- D1–D13 in `specs/architecture/decisions.md`, settled at founding from `09` and the founding conversation; recorded on Epic 0001
- The name and the repository: `10-the-roadmap.md` §7d; the two-lane plan: §3b; the board: `intent-ecosystem/lanes/board.md`

## Recent Changes

- 2026-09-10 — **Phase 9 begins**: what crosses a boundary is settled before anything is built on it. A checkpoint *is* a wire, so the graph's state holds JSON rather than our classes — which closes TD-001 while it was still green — and `Spent` says what a step cost instead of leaving it in an output dict by convention
- 2026-09-10 — **Phase 8 complete**: patterns and skills are files a team writes, a big catalogue is names until the model asks, a run replays for nothing, and a model can summarise itself and keep a helper. Building the helper verbs found a Phase 7 bug — a held child was woken on the ceiling it started with, which a parent that had spent since could no longer afford
- 2026-09-10 — **Phase 7 complete**: a child can be kept between messages, and it is a checkpoint rather than an object left running. Building it found that `Await` had never parked — the architecture said `interrupt()` since Phase 0 and the compiler treated it like `Invoke`, so half the grammar's waiting was a type nothing exercised
- 2026-09-10 — **Phase 6 complete**: the compiler says *where*. A nested composite is a subgraph with its own checkpoint namespace, a host can stop a run and the record carries the words of whoever asked, and a parked run resumes from a file after the saver that wrote it is gone. Two steps sharing an id used to loop until the lease was spent; now the run ends and names the id
- 2026-09-10 — **Phase 5 complete**: a child agent uses the parent's registry through an MCP server, and what it did is on the parent's record because it was routed. The MCP topology is inverted — the parent spawns the child and serves over its pipes, because this server holds a live run and cannot be launched fresh
- 2026-09-10 — **Phase 4 complete**: another agent driven as a governed component. A mode written for the harness governs somebody else's agent without knowing it exists
- 2026-09-10 — **Phase 3 complete**: the agent can make things — a workspace it cannot write outside of, and a sandbox that says honestly what it is not. What the deployment is decides what the model can see
- 2026-09-10 — **Phase 2 complete**: J1 answered. ACP reports usage and sometimes a price; a turn always ends with a stop reason; there are two distinct ways to refuse; and nothing stops an agent looping on a denial, so a driver needs its own clock — which the lease already is
- 2026-09-10 — **Phase 1 complete**: one model adapter over every LangChain provider, proven live against HuggingFace; MCP components with effects derived from annotations; modes as data; the harness on real everything
- 2026-09-10 — **Phase 0 complete**: the runtime, the agent as a component, the basic adapters, the bare harness green with zero product code
- 2026-09-10 — founded: charter, principles, success criteria, roadmap, architecture, Epic 0001, Phase 0
- 2026-09-10 — momentum installed; joined `intent-ecosystem` as member `shadow-hdk`
- 2026-09-10 — the kernel, two invariants and the strict-xfail bare-harness test (`0ca2d2b`, `9befb80`)
