---
type: Status
---

# Project Status

> **Last Updated**: 2026-09-11 (Phase 20)
> **Current Phase**: **Phase 19 COMPLETE — every P0, P1 and P2 the audit filed is closed.** The
> exception is ENH-003, deliberately deferred to the first OPC-UA or ROS adapter, which needs a
> server or a ROS distribution that is not on this machine.
>
> Phase 19 closed **BUG-016** (57% of the runtime's per-step overhead was Pydantic rebuilding the
> same schema; 1.36 → **0.594 ms/step**), **BUG-013** (the derivation engine total, canonical and
> NFC-normalised), **BUG-014** (the record survives a crash), **TD-004** (every port held to its
> contract), **TD-005** (what grows with traffic bounded, what does not argued), **TD-006** (six
> leaks, one cause: `RuntimeStop` was an `Exception`, so every adapter's `except Exception`
> swallowed a lease, a cancellation and a port failure alike — **contract 0.13.0**), **TD-007's
> plumbing**, and **TD-008** (the documents, kept honest by an invariant).
>
> **Ten of the audit's own claims were wrong and are corrected on the record** — understated,
> misplaced, already fixed, or not reproducible. Every row was reproduced before it was touched, and
> that changed the fix in about a third of them.
>
> **CI is green** and runs on every push. It had never run on any of 141 commits until this phase
> widened a trigger that only fired on branches nothing has ever landed on.
>
> 949 tests; mypy strict over 147 files; seventeen distributions at **0.13.0**, all MIT.
>
> **LANDED AND RELEASED, 2026-09-10.** The owner approved the merge end to end. The linear stack
> fast-forwarded onto `staging` and then onto `main` — no merge commit, because `main` was a strict
> ancestor — and `main`, `staging` and `phase-19-the-p2s` are all at `81d4b6a`. **v0.13.0 is tagged
> and released.** CI is green on `main`. This is the first release this repository has had.
>
> **Nothing further is buildable here.** What remains open is **ADR-1** (which gates TD-007's other
> half — whether an irreversible step must produce an `Acted` whichever port it came through) and
> **ADR-2**. The merge and the tag are done. Recorded deferrals: unit
> cancellation in the derivation engine, a twelfth event kind for an unreachable port, ENH-002 (a
> TLS broker), ENH-003 (a second protocol adapter), and Phase 11's live gVisor and Firecracker
> proofs (a Linux host).
> **Latest Release**: **v0.14.0**, released 2026-09-11 — Phase 20, providers: bring your own key or
> your own subscription; the socket; BUG-018 fixed three times and guarded once. Contract change
> (`AgentPort`, `Provider`), so a *Pins* row. Before it, **v0.13.1**, released 2026-09-11 — a patch. BUG-017 (the wire listener left
> quietly), the README rewritten from its Phase 0 state, and three stale tables in this file
> corrected. **No contract change, so no *Pins* row** (D9): every package moves to 0.13.1
> together because they are pinned to each other by equality, not because anything a host
> depends on moved. All MIT
> **Health**: On Track

## Summary

shadow-hdk is the generic agentic system designed in
`intent-ecosystem/vision/09-the-agentic-system.md`: a runtime that runs an agent over an open set of
components under a governance policy and hands what it produces to whoever is listening. It governs
effects, not names; the agent's plan is data compiled to a LangGraph graph; the runtime acts through
components and records through the sink. Three packages — kernel, runtime, adapters — one import
name, six ports. Any system that implements the six ports is its intended user, and this repository
plans for none of them in particular — which adopter reaches which capability when is a fact about
that adopter, and it lives in the shared roadmap rather than here. **All twenty phases are built,
merged and released**: 949 tests, mypy strict over 147 files, seventeen distributions at 0.13.0.

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

## Ad-hoc / Patch Releases

| Version | Date | Type | Summary |
|---------|------|------|---------|
| _(none yet)_ | | | |

## Active Phase

| Phase | Branch | Status | Progress |
|-------|--------|--------|----------|
| _(none)_ | — | — | Phases 0–19 are complete, merged and released. What each phase did is in its own `specs/phases/<phase>/history.md`; this table holds lanes that are **in flight** (Rule 15), and none are. |

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
