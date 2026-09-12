---
type: Status
---

# Project Status

> **Last Updated**: 2026-09-12 (the studio driven like a person would)
> **Current Phase**: **none — used, not built, and released as v0.20.0.** The studio's page shows
> the trace inline in the conversation, the environment beside it; five real tasks were driven
> through it on the owner's subscription (a CLI with tests, a playable Snake game, a refactor with
> a commit, a CSV report with `pip install` refused by the person, a read-only session) and
> **seven bugs were found live, reproduced under tests and closed**: `/dev/null` in the sandbox
> (BUG-023), parallel tool calls born exhausted (BUG-024), an exception group that named nothing
> (BUG-025), a question that named nothing (**D59**, BUG-026), a dead connection ending the
> conversation and the relay's thirty-second timeout (**D60**, BUG-027/028), read-only refusing
> the conversation (BUG-029). Three enhancements filed (ENH-006/007/008).
>
> Phases 21–24 are the four the owner asked for (v0.15.0–v0.18.0); 25 and 26 are the owner's to
> open. Open and deferred: ENH-002 (a TLS broker), ENH-003 (a second protocol adapter), ENH-005
> (Codex has no strict MCP mode — upstream), ENH-006 (a scratch in read-only), ENH-007 (nothing on
> screen while a long tool call is composed), ENH-008 (the CLI's own refused tools are invisible).
>
> **CI is green** and runs on every push.
>
> 1,201 tests; mypy strict over 213 files; seventeen distributions at **0.20.0**, all MIT.
>
> **Latest Release**: **v0.20.0**, released 2026-09-12 — the studio inline; seven bugs found by
> using it (D59, D60). Contract change (`Asked` says what it is about), so a *Pins* row. Before it
> v0.19.0 (hardening to Phase 24: D57 park, D58 live, `Questions`, Codex measured), v0.18.0 (Phase 24, the skill registry), v0.17.0 (Phase 23, a host —
> the consumable line), v0.16.0, v0.15.0, v0.14.0, v0.13.1. All MIT
> **Health**: On Track

## Summary

shadow-hdk is the generic agentic system designed in
`intent-ecosystem/vision/09-the-agentic-system.md`: a runtime that runs an agent over an open set of
components under a governance policy and hands what it produces to whoever is listening. It governs
effects, not names; the agent's plan is data compiled to a LangGraph graph; the runtime acts through
components and records through the sink. Three packages — kernel, runtime, adapters — one import
name, six ports. Any system that implements the six ports is its intended user, and this repository
plans for none of them in particular — which adopter reaches which capability when is a fact about
that adopter, and it lives in the shared roadmap rather than here. **Twenty-five phases are built,
merged and released**: 1,201 tests, mypy strict over 213 files, seventeen distributions at 0.20.0.

## Completed Phases

> Every phase is merged and released. `main`, `staging` and the phase branches met at
> `81d4b6a` on 2026-09-10; each phase carries a `phase/NN-*` tag, and the release column is
> the version that first shipped it. Several phases share a version because a version is a
> **contract** change (D9), not a phase boundary.

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| 0 | The runtime, and the bare test goes green | Complete, merged | **v0.1.0** |
| 1 | Real adapters, streaming, modes | Complete, merged | **v0.2.0** |
| 2 | The spike — J1 | Complete, merged | **v0.2.0** |
| 3 | The workspace, and code | Complete, merged | **v0.2.0** |
| 4 | The ACP bridge | Complete, merged | **v0.2.0** |
| 5 | Checkpoints, and a parked run survives | Complete, merged | **v0.3.0** |
| 6 | The compiler completed | Complete, merged | **v0.4.0** |
| 7 | Sub-agents | Complete, merged | **v0.5.0** |
| 8 | Patterns, skills, replay, compaction | Complete, merged | **v0.5.0** |
| 9 | The wire | Complete, merged | **v0.6.0** |
| 10 | Effect rules | Complete, merged | **v0.6.0** |
| 11 | Contained sandboxes | Complete, merged | **v0.6.0** |
| 12 | Derivation | Complete, merged | **v0.6.0** |
| 13 | Leases on effects, driver supply chain | Complete, merged | **v0.7.0** |
| 14 | Telemetry | Complete, merged | **v0.7.0** |
| 15 | The environment contract | Complete, merged | **v0.8.0** |
| 16 | MQTT | Complete, merged | **v0.8.0** |
| 17 | The audit — every P0 | Complete, merged | **v0.10.0** |
| 18 | The P1s | Complete, merged | **v0.12.0** |
| 19 | The P2s, and the documents | Complete, merged | **v0.13.0** |
| 20 | Providers — your key, or your subscription | Complete, merged | **v0.14.0** |
| 21 | The visible agent | Complete, merged | **v0.15.0** |
| 22 | The environment | Complete, merged | **v0.16.0** |
| 23 | A host, in-process and in any language | Complete, merged | **v0.17.0** |
| 24 | The skill registry | Complete, merged | **v0.18.0** |

## Ad-hoc / Patch Releases

| Version | Date | Type | Summary |
|---------|------|------|---------|
| v0.20.0 | 2026-09-12 | hardening | the studio inline; five scenarios; BUG-023–029 closed (D59, D60) |
| v0.19.0 | 2026-09-12 | hardening | BUG-020/021/022 closed (D57, D58); Codex measured; the studio |

## Active Phase

| Phase | Branch | Status | Progress |
|-------|--------|--------|----------|
| 25 — the host's controls | `phase-25-the-hosts-controls` | in progress | Groups 1–2 done (D61 the words, D62 the thread); Group 3 (activity) next |

## Upcoming Phases

> **Nothing is scheduled.** The roadmap's phases are done and the backlog holds no P0, P1 or
> P2. What is left needs something this machine or this session does not have, and each row
> names it rather than sitting as an undated intention.

| What | Waits on | Why it is not buildable here |
|------|----------|------------------------------|
| TD-007's other half — whether an irreversible step must produce an `Acted` whichever port it came through | **ADR-1** | A governance question, not a defect. The plumbing landed in Phase 19; the policy is the owner's to decide. |
| Which effects must be signed, who holds a key, what a warrant is | **ADR-1** | Same decision. Phase 13 built the mechanism and left the policy `[~]`. |
| Setting ownership on the six-rung ladder | **ADR-2** | Owner's. |
| Phase 11's gVisor and Firecracker containment proofs | a Linux host | The backends are built and refuse to exist unless containment is proven; the live proofs **skip** here. |
| ENH-003 — a protocol-adapter contract suite | a second protocol adapter | With one implementation, parametrising the MQTT tests is a rename rather than a contract. Needs an OPC-UA server or a ROS 2 distribution. |
| ENH-002 — TLS on `MqttLink` | a TLS broker | The dev broker has no TLS listener, so it cannot be proven here. |
| Unit cancellation in the derivation engine | a design decision | Recorded deferral, Phase 12. |
| A twelfth event kind for an unreachable port | a design decision | Filed in Phase 19; `unreachable` is readable today. |

## Blockers

| ID | Description | Severity |
|----|-------------|----------|
| _(none)_ | | |

## Critical Items (P0)

| ID | Type | Description |
|----|------|-------------|
| BUG-004 | Bug | The lease and `seq` reset on every resume — a parked run gets its whole ceiling back, and held children are orphaned. Reproduced. |
| BUG-005 | Bug | The assistant's tool calls are dropped from the transcript, so a strict provider rejects turn two. The agent loop is proven against `ScriptedModel` only. |
| BUG-006 | Bug | `resume` over the wire always raises (no checkpointer), and `serve` issues a session on a bare GET — the run token `wire.md` calls fixed is unbuilt. |
| BUG-007 | Bug | mypy strict silently skips `wire`, `contained` and `derivation`; nine real errors in `wire` today. The type gate has never covered them. |
| TD-009 | Tech Debt | CI has never run on a phase commit — zero PRs, two runs at founding. Every green gate so far is a local run reported by the session that wrote the code. |

## Next Actions

1. Phase 9, Group 1 — the protocol and the loopback: `initialize` refusing a version mismatch, the five inverted ports, and wire.md's acceptance test — *the in-process runtime suite passes through a loopback transport, or the wire is not done*
2. Phase 9, Groups 2–4 — `--stdio`, then `serve` which **listens** (Phase 5's debt), then the published schemas and v0.1.0 prepared. **Tagging is the owner's**
3. Phases 10–14 in roadmap order; the environment epic after
3. Carried to Phase 9, each with what would settle it: tokens reaching the observer (the tenth event kind arrived in Phase 7 as `Held`, so this still needs its own); a **listening** transport (streamable HTTP) for a child on another machine, since the recording server can only be connected to, never launched; and **TD-001**, our observation classes riding in graph state where a future LangGraph will block them

## Key Decisions Made

- D1–D13 in `specs/architecture/decisions.md`, settled at founding from `09` and the founding conversation; recorded on Epic 0001
- D14–D22 settled per phase: D15 cancellation (6), D16 held children (7), D17 files and D18 compaction (8), D19 state-as-JSON, D20 `Spent`, D21 the crossed context (9). **D22 — the port set is open**: six is a count, not a constraint, settled by the owner 2026-09-10, which closes O4
- **Licensed MIT** 2026-09-10 (O3), declared in every package and verified in the built wheels
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
