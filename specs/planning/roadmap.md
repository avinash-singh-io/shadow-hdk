---
type: Roadmap
---

# Roadmap — shadow-hdk

> **Start Date**: 2026-09-10

## Vision

A governed, composable agent runtime any system can adopt by implementing six ports — from one
deterministic agent with a few tools to dynamic multi-agent work acting on the physical world —
growing only by adapters and pattern files, never by runtime branches.

## Order

**Intent Studio first.** Lane P (`intent-ecosystem/vision/10-the-roadmap.md` §3b) depends on this
repository at R1–R3; those phases come first and carry the product release they serve. Everything
after the R3 join is the harness's own growth, pulled forward the moment a product asks. Ordering is
computed from each phase's `deps`, never from this list.

## Where this stands — 2026-09-10

**Nine phases done, one under way, five plus an epic to go.** Every phase is on its own branch,
each branched from the one before, **all pushed and none merged** — landing is the owner's gate
(Rule 6). The suite is **417 tests**, mypy strict over **83 source files**, every package at
**0.6.0**.

| | phases | state |
|---|---|---|
| done | 0 – 8 | every task ticked; each left the gate green |
| under way | 9 — the wire | groups 0–1 of 5 (D19, D20, D21) |
| not started | 10 – 14, the environment epic | |

Everything R0–R3 depends on is built **except the wire**, which is J2. Lane P can already embed the
runtime in-process; what Phase 9 adds is reaching it from another process or language.

**Decisions settled so far:** D1–D14 (`specs/epics/0001-the-bare-harness.md`), D15 cancellation
(phase 6), D16 held children (phase 7), D17 patterns and skills as files (phase 8), D18 compaction
as a meta-tool (phase 8), D19 the graph state holds JSON, D20 the `Spent` event and D21 the context a crossed component gets
(phase 9).

**Open, and needing the owner:** the licence (O3), ADR-1 and ADR-2, the six-port reading (O4), and
running `spikes/acp/drive_real.py` against a real Codex or Claude Code — which needs a global npm
install and a paid turn, so it is recorded unmeasured with the command that would settle it. The
**v0.1.0 tag** at the end of Phase 9 is the owner's too.

## Timeline

| Phase | Name | Status | deps | Serves | Key Deliverables |
|-------|------|--------|------|--------|------------------|
| 0 | The runtime — the bare test goes green | **DONE** · `phase-0-the-runtime` | — | R0 | `run(composition, ports)`; compile to LangGraph; the governed step; leases, events, proposals, children; the agent as a component with the `single` pattern; `basic` adapters incl. `callable`; testing doubles; replay determinism; the benchmark |
| 1 | Real adapters, streaming, modes | **DONE** · `phase-1-real-adapters` | 0 | R1 | `adapters/langchain` (one `ModelPort` over LangChain's providers — OpenAI-compatible, Anthropic, Ollama, HuggingFace, …) with `stream`; `adapters/mcp` (annotations → half a profile); `adapters/modes`; the demo on real components |
| 2 | The spike | **DONE** · `phase-2-the-spike` | 0 | R1 → J1 | half a day over `agent-client-protocol`: does a refused tool call end a CLI's turn cleanly; does ACP report usage |
| 3 | The workspace and code | **DONE** · `phase-3-workspace-and-code` | 1 | R1/R3 | `adapters/workspace` (files within a root, `writes: {workspace}`); `adapters/sandbox_subprocess` (run code with limits; `contained` per deployment) — the agent writes files, pages and code |
| 4 | The ACP bridge | **DONE** · `phase-4-the-acp-bridge` | 1, 2 | R2 | Codex or Claude Code as a component, resident for the session |
| 5 | The RecordingServer | **DONE** · `phase-5-the-recording-server` | 1, 4 | R2 | an MCP server exposing the registry to a child agent; every call an observation with `posture: observed` |
| 6 | The compiler, complete | **DONE** · `phase-6-the-compiler-complete` | 0 | R3 | nested composites as subgraphs, checkpoint namespaces, `resume`, cancellation, host checkpointers |
| 7 | Sub-agents | **DONE** · `phase-7-sub-agents` | 6 | R3 | spawn · send · release; held children; branch-level cancel; `run.*` events |
| 8 | Patterns, skills, replay | **DONE** · `phase-8-patterns-skills-replay` | 7 | R3 | `plan-and-execute`, `orchestrator-workers`, `critic-pair`, `reflect-until`; skill file loader; compaction component; recorded model port; catalogue compaction (`describe`) |
| 9 | The wire | **IN PROGRESS** · 2 / 5 groups · `phase-9-the-wire` | 6, 7 | R3 → J2 | `serve` (JSON-RPC 2.0 over HTTP/2 + SSE), `--stdio`; schemas published; **`v0.1.0`** |
| 10 | Effect rules | Not started | 0 | R5 → J4 | rules as rows over profiles, intersection, the narrowing check as a library, mode files |
| 11 | Contained sandboxes | Not started | 3 | R9 | gVisor, Firecracker as `contained: true` components |
| 12 | Derivation | Not started | 0 | R8 | total expressions over typed tables, fixed-point arithmetic, re-executable grounds |
| 13 | Leases on effects, driver supply chain | Not started | 7, 9 | R9 | `EffectPort` takes a lease; keys, signatures, receipts, revocation |
| 14 | Telemetry | Not started | 0 | — | OpenTelemetry observer; file sink |
| — | **The environment** (epic) | Not started | 3, 7, 13 | — | protocol adapters for devices — MQTT, OPC-UA, ROS 2 — sensors as `reads: {world}`, actuators as irreversible writes; controlled vs observed posture |

## Epics

| Epic | Phases | Serves |
|---|---|---|
| 0001 the bare harness | 0, 1, 2 | R0–R1 |
| 0002 the workspace, and driving another agent | 3, 4, 5 | R1–R2 |
| 0003 composition at scale | 6, 7, 8, 9 | R3 |
| 0004 governance as rows | 10 | R5 |
| 0005 the body | 11, 13 | R9 |
| 0006 derivation | 12 | R8 |
| 0007 the environment | later | — |

Only 0001 is created at founding; each later epic is brainstormed once when reached, its decisions
already settled by `09` where `09` speaks.

## Guiding Principles
1. Ship working software in every phase; each phase leaves every package releasable
2. Intent Studio's need orders the phases until the R3 join; the harness's own growth after
3. Defer scope, not quality — red tests first, contracts round-trip, the benchmark runs
4. A new capability is an adapter or a pattern file; a runtime branch on a name is a defect
