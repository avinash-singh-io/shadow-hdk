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

**Ordering is computed from each phase's `deps`, never from this list.** A phase runs when what it
needs exists; where two are free at once, the one that closes a gap in the runtime's own story comes
first.

**Adopters do not appear in this document.** The harness is a library: it is finished when its own
contracts hold, not when somebody has used them. Which release of which product a phase happens to
unblock is a fact about that product, and it lives in the shared roadmap
(`intent-ecosystem/vision/10-the-roadmap.md`) with the joins on `intent-ecosystem/lanes/board.md`.
Keeping it there is what stops this plan from being re-ordered by somebody else's schedule — and
what stops a capability from being called done because one caller happens not to need the rest of
it.

## Where this stands — 2026-09-10

**Phases 0–18 are done. Every phase branch is pushed and none is merged** — landing is the owner's
gate (Rule 6). The suite is **837 tests**, mypy strict over **132 source files**, all seventeen
distributions at **0.12.0**, all MIT.

| | phases | state |
|---|---|---|
| done | 0 – 16 | every task ticked; each left the gate green (11's live backend proofs await a Linux host; 13's policy is `[~]` for ADR-1) |
| done | 17 — the audit's P0s | all four closed: the lease reset at every pause (D33), an assistant message never carried its tool calls, resume over the wire always raised (D34), and the gate itself silently skipped three packages |
| done | 18 — the audit's P1s | **COMPLETE, groups 1–5 of 5.** BUG-008, BUG-009 (D35, D36), BUG-015 (D37), BUG-010 (D38, contract 0.12.0), BUG-011, BUG-012, TD-003, TD-009 |
| open | the P2s | BUG-013, BUG-014, **BUG-016**, TD-004…TD-008 — what remains buildable without the owner |
| `[~]` | OPC-UA, ROS 2 (epic 0007) | need `asyncua` and a server, and a ROS distribution — not on this machine; shaped by `adapters/mqtt` |

**Decisions settled so far:** D1–D14 (`specs/epics/0001-the-bare-harness.md`), D15 cancellation
(phase 6), D16 held children (phase 7), D17 patterns and skills as files, D18 compaction as a
meta-tool (phase 8), D19 the graph state holds JSON, D20 the `Spent` event, D21 the context a
crossed component gets (phase 9), D22 the port set is open, D23 a rule selects by name, D24 the
check runs on the rules (phase 10), D25 containment is proven at construction (phase 11), D26 a
ground is data and the engine its only interpreter (phase 12), D27 a driver signs what it declares
(phase 13), D28 telemetry carries the shape and never payloads (phase 14), D29 the world is a scope
and a device a component, D30 posture is on the record and in front of governance, D31 one device
contract and three roles (phase 15), D32 the envelope is the payload (phase 16), D33 what a run has
spent rides in the checkpoint, D34 a wire session owns a checkpointer (phase 17), D35 a step owns
the process tree it starts, D36 containment is proven by what is denied, D37 a parent that parks
comes back holding its children, D38 a parked step resumes where it parked (phase 18).

**Closed by the owner 2026-09-10:** the licence is **MIT** (O3), and the six-port question is
settled as **D22 — the port set is open**, six being a count rather than a constraint (O4).

**Still with the owner:** ADR-1 and ADR-2; landing the linear stack — **the pull request is prepared
and not opened**, in `specs/adhoc/TD-009/`; and the first release tag, which is **v0.12.0**. Twelve
contract changes have each moved every package under D9, so the number the packages carry is the
true one and this plan's founding `v0.1.0` was stale.

**The latency budget holds, and for a while it did not.** CI ran for the first time on 2026-09-10
and found the runtime costing **1.36 ms of overhead per step** against D11's ≤ 1 ms. The cause was
`contracts.py` rebuilding a `TypeAdapter` on every call — 57% of the whole per-step cost — and
caching it restored **0.594 ms/step**. The gate that missed it keeps its 3× slack deliberately: a
runner is 2.1× this machine and the drift was 2.4×, so a stopwatch cannot separate them. A count of
adapters can, and does.

## Timeline

| Phase | Name | Status | deps | Key Deliverables |
|-------|------|--------|------|------------------|
| 0 | The runtime — the bare test goes green | **DONE** · `phase-0-the-runtime` | — | `run(composition, ports)`; compile to LangGraph; the governed step; leases, events, proposals, children; the agent as a component with the `single` pattern; `basic` adapters incl. `callable`; testing doubles; replay determinism; the benchmark |
| 1 | Real adapters, streaming, modes | **DONE** · `phase-1-real-adapters` | 0 | `adapters/langchain` (one `ModelPort` over LangChain's providers — OpenAI-compatible, Anthropic, Ollama, HuggingFace, …) with `stream`; `adapters/mcp` (annotations → half a profile); `adapters/modes`; the demo on real components |
| 2 | The spike | **DONE** · `phase-2-the-spike` | 0 | half a day over `agent-client-protocol`: does a refused tool call end a CLI's turn cleanly; does ACP report usage |
| 3 | The workspace and code | **DONE** · `phase-3-workspace-and-code` | 1 | `adapters/workspace` (files within a root, `writes: {workspace}`); `adapters/sandbox_subprocess` (run code with limits; `contained` per deployment) — the agent writes files, pages and code |
| 4 | The ACP bridge | **DONE** · `phase-4-the-acp-bridge` | 1, 2 | Codex or Claude Code as a component, resident for the session |
| 5 | The RecordingServer | **DONE** · `phase-5-the-recording-server` | 1, 4 | an MCP server exposing the registry to a child agent; every call an observation with `posture: observed` |
| 6 | The compiler, complete | **DONE** · `phase-6-the-compiler-complete` | 0 | nested composites as subgraphs, checkpoint namespaces, `resume`, cancellation, host checkpointers |
| 7 | Sub-agents | **DONE** · `phase-7-sub-agents` | 6 | spawn · send · release; held children; branch-level cancel; `run.*` events |
| 8 | Patterns, skills, replay | **DONE** · `phase-8-patterns-skills-replay` | 7 | `plan-and-execute`, `orchestrator-workers`, `critic-pair`, `reflect-until`; skill file loader; compaction component; recorded model port; catalogue compaction (`describe`) |
| 9 | The wire | **DONE** · `phase-9-the-wire` | 6, 7 | `serve` (JSON-RPC 2.0 over HTTP/2 + SSE), `--stdio`; schemas published. The tag is the owner's and is now **`v0.12.0`** — twelve contract changes have moved every package under D9 since this row was written |
| 10 | Effect rules | **DONE** · `phase-10-effect-rules` | 0 | rules as rows over profiles, intersection, the narrowing check as a library, mode files |
| 11 | Contained sandboxes | **DONE here** · live proofs `[~]` Linux · `phase-11-contained-sandboxes` | 3 | gVisor, Firecracker as `contained: true` components |
| 12 | Derivation | **DONE** · `phase-12-derivation` | 0 | total expressions over typed tables, fixed-point arithmetic, re-executable grounds |
| 13 | Leases on effects, driver supply chain | **DONE** (mechanism; policy `[~]` ADR-1) | 7, 9 | `EffectPort` takes a lease; keys, signatures, receipts, revocation |
| 14 | Telemetry | **DONE** | 0 | OpenTelemetry observer; file sink |
| — | **The environment** (epic 0007) | **DONE** for phases 15 and 16; OPC-UA and ROS 2 `[~]` | 3, 7, 13 | protocol adapters for devices — MQTT, OPC-UA, ROS 2 — sensors as `reads: {world}`, actuators as irreversible writes; controlled vs observed posture |
| 17 | The audit's P0s | **DONE** · `phase-17-the-audit` | 16 | the lease survives a park (D33); an assistant message carries its tool calls; resume over the wire, `initialize` required, callbacks timed out, `serve` loopback-only (D34); the gate widened to every package |
| 18 | The audit's P1s | **DONE** · `phase-18-the-p1s` | 17 | the workspace confined against hard links; a step owns its process tree (D35); containment proven by what is denied (D36); a parent keeps its children across a park (D37); a parked step resumes where it parked and the human's answer decides (D38); the ACP purse charges the step and a deaf child is killed; five agent promises kept; packaging pinned and typed; **CI made to run at all** |
| 19 | The P2s | **IN PROGRESS**, groups 1–2 of 4 · `phase-19-the-p2s` | 18 | **BUG-016** the adapter cache (0.594 ms/step, back inside D11, and CI green for the first time); **BUG-013** a derivation answers rather than raises and one quantity has one identity; **BUG-014** a crash costs the record nothing. Next: TD-004…TD-008 |

## Epics

| Epic | Phases |
|---|---|
| 0001 the bare harness | 0, 1, 2 |
| 0002 the workspace, and driving another agent | 3, 4, 5 |
| 0003 composition at scale | 6, 7, 8, 9 |
| 0004 governance as rows | 10 |
| 0005 the body | 11, 13 |
| 0006 derivation | 12 |
| 0007 the environment | 15, 16 |
| — the audit | 17, 18, 19 |

Only 0001 is created at founding; each later epic is brainstormed once when reached, its decisions
already settled by `09` where `09` speaks.

## Guiding Principles
1. Ship working software in every phase; each phase leaves every package releasable
2. `deps` order the phases; nothing else does, and no adopter's schedule does
3. Defer scope, not quality — red tests first, contracts round-trip, the benchmark runs
4. A new capability is an adapter or a pattern file; a runtime branch on a name is a defect
