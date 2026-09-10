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
(Rule 6). The suite is **565 tests**, mypy strict over **97 source files**, every package at
**0.6.0**.

| | phases | state |
|---|---|---|
| done | 0 – 16 | every task ticked; each left the gate green (11's live backend proofs await a Linux host; 13's policy is `[~]` for ADR-1) |
| under way | 18 — the audit's P1s | groups 1–2 of 5: BUG-008 and BUG-009 closed (D35, D36). Next: BUG-015, 010, 011, 012, TD-003, TD-009 |
| `[~]` | OPC-UA, ROS 2 (epic 0007) | need `asyncua` and a server, and a ROS distribution — not on this machine; shaped by `adapters/mqtt` |

Everything R0–R3 depends on is built **except the wire**, which is J2. Lane P can already embed the
runtime in-process; what Phase 9 adds is reaching it from another process or language.

**Decisions settled so far:** D1–D14 (`specs/epics/0001-the-bare-harness.md`), D15 cancellation
(phase 6), D16 held children (phase 7), D17 patterns and skills as files (phase 8), D18 compaction
as a meta-tool (phase 8), D19 the graph state holds JSON, D20 the `Spent` event and D21 the context a crossed component gets
(phase 9), D22 the port set is open, D23 a rule selects by name and D24 the check runs on the rules
(phase 10), D25 containment is proven at construction (phase 11), D26 a ground is data and the engine its
only interpreter (phase 12).

**Closed by the owner 2026-09-10:** the licence is **MIT** (O3), and the six-port question is
settled as **D22 — the port set is open**, six being a count rather than a constraint (O4). The
open spike was reframed from *what does a coding CLI do when refused* to the generic question and
answered by research rather than by spending a subscription: `specs/architecture/refusal.md`.

**Still with the owner:** ADR-1 and ADR-2, landing the linear stack, and the **first release tag**
at the end of Phase 9 — which is **v0.6.0**, not the `v0.1.0` this document said at founding. Six
contract changes have each moved every package under D9 since then, so the number the packages
carry is the true one and the plan's was stale.

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
| 9 | The wire | **DONE** · `phase-9-the-wire` | 6, 7 | R3 → J2 | `serve` (JSON-RPC 2.0 over HTTP/2 + SSE), `--stdio`; schemas published; **`v0.1.0`** |
| 10 | Effect rules | **DONE** · `phase-10-effect-rules` | 0 | R5 → J4 | rules as rows over profiles, intersection, the narrowing check as a library, mode files |
| 11 | Contained sandboxes | **DONE here** · live proofs `[~]` Linux · `phase-11-contained-sandboxes` | 3 | R9 | gVisor, Firecracker as `contained: true` components |
| 12 | Derivation | **DONE** · `phase-12-derivation` | 0 | R8 | total expressions over typed tables, fixed-point arithmetic, re-executable grounds |
| 13 | Leases on effects, driver supply chain | Complete, unmerged (mechanism; policy `[~]` ADR-1) | 7, 9 | R9 | `EffectPort` takes a lease; keys, signatures, receipts, revocation |
| 14 | Telemetry | Complete, unmerged | 0 | — | OpenTelemetry observer; file sink |
| — | **The environment** (epic 0007) | Phases 15 and 16 complete, unmerged; OPC-UA and ROS 2 `[~]` | 3, 7, 13 | — | protocol adapters for devices — MQTT, OPC-UA, ROS 2 — sensors as `reads: {world}`, actuators as irreversible writes; controlled vs observed posture |

## Epics

| Epic | Phases | Serves |
|---|---|---|
| 0001 the bare harness | 0, 1, 2 | R0–R1 |
| 0002 the workspace, and driving another agent | 3, 4, 5 | R1–R2 |
| 0003 composition at scale | 6, 7, 8, 9 | R3 |
| 0004 governance as rows | 10 | R5 |
| 0005 the body | 11, 13 | R9 |
| 0006 derivation | 12 | R8 |
| 0007 the environment | 15, 16 | — |

Only 0001 is created at founding; each later epic is brainstormed once when reached, its decisions
already settled by `09` where `09` speaks.

## Guiding Principles
1. Ship working software in every phase; each phase leaves every package releasable
2. Intent Studio's need orders the phases until the R3 join; the harness's own growth after
3. Defer scope, not quality — red tests first, contracts round-trip, the benchmark runs
4. A new capability is an adapter or a pattern file; a runtime branch on a name is a defect
