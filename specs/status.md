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
| 3 — the workspace and code | `phase-3-workspace-and-code` | **complete, unmerged** | 3 / 3 groups. A workspace confined to a root (symlinks resolved before checking), a subprocess sandbox whose `contained` is a deployment fact, and the chain from that fact to what the model can see. 251 tests; mypy strict over 56 files. |

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

1. Phase 4 — the ACP bridge, on `phase-4-the-acp-bridge` branched from `phase-3-workspace-and-code`: Codex or Claude Code as a component, resident for the session. It starts knowing what Phase 2 measured — a fourteen-method client surface, two distinct ways to refuse, and the need for its own wall clock
2. Phase 5 — the RecordingServer: our registry offered to a child agent as an MCP server, every call an observation with `posture: observed`

## Key Decisions Made

- D1–D13 in `specs/architecture/decisions.md`, settled at founding from `09` and the founding conversation; recorded on Epic 0001
- The name and the repository: `10-the-roadmap.md` §7d; the two-lane plan: §3b; the board: `intent-ecosystem/lanes/board.md`

## Recent Changes

- 2026-09-10 — **Phase 3 complete**: the agent can make things — a workspace it cannot write outside of, and a sandbox that says honestly what it is not. What the deployment is decides what the model can see
- 2026-09-10 — **Phase 2 complete**: J1 answered. ACP reports usage and sometimes a price; a turn always ends with a stop reason; there are two distinct ways to refuse; and nothing stops an agent looping on a denial, so a driver needs its own clock — which the lease already is
- 2026-09-10 — **Phase 1 complete**: one model adapter over every LangChain provider, proven live against HuggingFace; MCP components with effects derived from annotations; modes as data; the harness on real everything
- 2026-09-10 — **Phase 0 complete**: the runtime, the agent as a component, the basic adapters, the bare harness green with zero product code
- 2026-09-10 — founded: charter, principles, success criteria, roadmap, architecture, Epic 0001, Phase 0
- 2026-09-10 — momentum installed; joined `intent-ecosystem` as member `shadow-hdk`
- 2026-09-10 — the kernel, two invariants and the strict-xfail bare-harness test (`0ca2d2b`, `9befb80`)
