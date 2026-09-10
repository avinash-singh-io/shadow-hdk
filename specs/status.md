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
| 8 — patterns, skills, replay | `phase-8-patterns-skills-replay` | **in progress** | 3 / 5 groups. Patterns ship as TOML files a team can edit (D17); a skill declares what it needs and is checked against `visible()` before the first turn; D13's last mechanism is built — a big catalogue is names until the model calls `describe`. 379 tests; mypy strict over 76 files. Left: the recorded model port, then compaction and the model-facing spawn verbs. |

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

1. Phase 8, Group 3 — the recorded model port: a run's model calls replayed at no cost, and a changed prompt a miss rather than a silent re-record
2. Phase 8, Group 4 — compaction as a component whose proposal reaches the sink, and the `spawn` / `send` / `release` meta-tools with the pattern that shapes the child
3. Phase 9 onward in roadmap order; the environment epic after
3. Carried to Phase 9, each with what would settle it: tokens reaching the observer (the tenth event kind arrived in Phase 7 as `Held`, so this still needs its own); a **listening** transport (streamable HTTP) for a child on another machine, since the recording server can only be connected to, never launched; and **TD-001**, our observation classes riding in graph state where a future LangGraph will block them

## Key Decisions Made

- D1–D13 in `specs/architecture/decisions.md`, settled at founding from `09` and the founding conversation; recorded on Epic 0001
- The name and the repository: `10-the-roadmap.md` §7d; the two-lane plan: §3b; the board: `intent-ecosystem/lanes/board.md`

## Recent Changes

- 2026-09-10 — **Phase 8, three of five groups**: a pattern is a file a team can write, a skill says what it needs and is told no before it starts, and a catalogue too big to read whole is names until the model asks. A mutation that survived changed the skill design rather than adding a test — matching a component by interface name as well as id would have let a skill declare a need it could not invoke
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
