---
type: Status
---

# Project Status

> **Last Updated**: 2026-09-10 (Phase 16)
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
> 946 tests; mypy strict over 133 files; seventeen distributions at **0.13.0**, all MIT.
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
> **Latest Release**: **v0.13.0**, released 2026-09-10 — the first. Every package at 0.13.0, all MIT
> **Health**: On Track

## Summary

shadow-hdk is the generic agentic system designed in
`intent-ecosystem/vision/09-the-agentic-system.md`: a runtime that runs an agent over an open set of
components under a governance policy and hands what it produces to whoever is listening. It governs
effects, not names; the agent's plan is data compiled to a LangGraph graph; the runtime acts through
components and records through the sink. Three packages — kernel, runtime, adapters — one import
name, six ports. Any system that implements the six ports is its intended user, and this repository
plans for none of them in particular — which adopter reaches which capability when is a fact about
that adopter, and it lives in the shared roadmap rather than here. The kernel exists and is green (`0ca2d2b`); Phase 0 builds the
runtime that turns the bare-harness test green.

## Completed Phases

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| 0 | The runtime, and the bare test goes green | Complete, unmerged (2026-09-10) | — |
| 1 | Real adapters, streaming, modes | Complete, unmerged (2026-09-10) | — |
| 2 | The spike — J1 | Complete, unmerged (2026-09-10) | — |
| 3 | The workspace, and code | Complete, unmerged (2026-09-10) | — |
| 4 | The ACP bridge | Complete, unmerged (2026-09-10) | — |
| 5 | Checkpoints, and a parked run survives | Complete, unmerged (2026-09-10) | — |
| 6 | The compiler completed | Complete, unmerged (2026-09-10) | — |
| 7 | Sub-agents | Complete, unmerged (2026-09-10) | — |
| 8 | Patterns, skills, replay, compaction | Complete, unmerged (2026-09-10) | — |
| 9 | The wire | Complete, unmerged (2026-09-10) | — |
| 10 | Effect rules | Complete, unmerged (2026-09-10) | — |
| 11 | Contained sandboxes | Complete, unmerged (2026-09-10) | — |
| 12 | Derivation | Complete, unmerged (2026-09-10) | — |
| 13 | Leases on effects, driver supply chain | Complete, unmerged (2026-09-10) | — |
| 14 | Telemetry | Complete, unmerged (2026-09-10) | — |
| 15 | The environment contract | Complete, unmerged (2026-09-10) | — |
| 16 | MQTT | Complete, unmerged (2026-09-10) | — |

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
| 9 — the wire | `phase-9-the-wire` | **complete, unmerged** | 5 / 5 groups. The runtime is reachable from another process or another language: the ports invert over a loopback (D21), `--stdio` drives a child process, and **`serve` listens** — Phase 5's debt paid. Twelve schemas published and checked against the code. 460 tests; mypy strict over 87 files. **Releasable at v0.6.0** — tagging is the owner's. Superseded as the active row by Phase 10. |
| 10 — effect rules | `phase-10-effect-rules` | **complete, unmerged** | 3 / 3 groups. Rules as rows that intersect and only narrow (D23); a team rule that widens is refused at load, naming rule and field (D24); rules load from a file with a shipped example. A mutation found fail-closed open at N=0 — fixed. 501 tests; mypy strict over 90 files. Superseded as the active row by Phase 11. |
| 11 — contained sandboxes | `phase-11-contained-sandboxes` | **complete here, unmerged** | 3 / 3 groups. A sandbox proves containment at construction or refuses to exist (D25); gVisor and Firecracker as backends whose live proofs **skip** on this machine and are `[~]` for a Linux host. The leash moved into the runtime so no adapter imports another. 517 tests; mypy strict over 93 files. Superseded as the active row by Phase 12. |
| 12 — derivation | `phase-12-derivation` | **complete, unmerged** | 3 / 3 groups. A ground is data and one engine is its interpreter (D26): fixed-point at scale 12, units and denominators on every value, a total evaluator that answers indeterminate, a canonical fingerprint, and the engine as a component whose observation and proposal are the same claim. 565 tests; mypy strict over 97 files. Superseded as the active row by Phase 13. |
| 13 — leases on effects | `phase-13-effect-leases` | **complete, unmerged** | 3 / 3 groups. A driver signs what it declares and is checked at the registry on every refresh (D27): unsigned where required, unknown, revoked or forged is *absent* with the reason; a revoked key is refused as revoked however valid its signature. `Acted` is the sixth observation kind — the receipt of any world-effect; the lease is read at the moment of the act; `run/step` tells a resume re-run from a second act. The policy — which effects must be signed, who holds a key, what a warrant is — waits on ADR-1 as `[~]`. Contract 0.6.0 → 0.7.0. 608 tests; mypy strict over 101 files. Superseded as the active row by Phase 14. |
| 14 — telemetry | `phase-14-telemetry` | **complete, unmerged** | 3 / 3 groups. The run's shape as a trace over the OpenTelemetry API alone (D28): one span per run and per step, refusals/asks/spawns/holds as events, usage on the step, an act's receipt and never a payload; spans open lazily so a resumed run traces; nothing kept with no provider; a raising tracer counted, not hidden. A file sink in `basic` that fsyncs before it returns and reads back past a torn tail. No contract change. 638 tests; mypy strict over 105 files. Superseded as the active row by Phase 15. |
| 15 — the environment contract | `phase-15-environment-contract` | **complete, unmerged** | 3 / 3 groups (Epic 0007). Every observation carries the posture of what produced it, stamped by the runtime (D30, contract 0.7.0 → 0.8.0); governance is told posture and component at the step and at the catalogue, and `Controlled` makes *only controlled satisfies consent-before-effect* executable; one device contract with three roles and the fake first (D29, D31) — a sensor reads `world`, an actuator writes it with the lease read at the act and a receipt, a witness reports observed acts. 659 tests; mypy strict over 109 files. Superseded as the active row by Phase 16. |
| 16 — MQTT | `phase-16-mqtt` | **complete, unmerged** | 3 / 3 groups (Epic 0007). The first protocol adapter over the device contract: topics as sensors, actuators and witnesses over `paho-mqtt` on 3.1.1, the envelope in the payload (D32), proven against an `amqtt` broker on localhost the suite starts and stops — a broker that is not there, one that refuses us, one that leaves and comes back. The device contract moved into the runtime so no adapter imports another. A system-design review received mid-phase found two P1 races in the link; fixed as Group 3 with the claims tested directly. No kernel contract change. 691 tests; mypy strict over 114 files. |

## Upcoming Phases

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|-----------------|
| 1 | Real adapters, streaming, modes | Complete, unmerged | `adapters/langchain`, `adapters/mcp`, `adapters/modes`; the demo on real components |
| 2 | The spike | Complete, unmerged | J1 answered over `agent-client-protocol` |
| 3 | The workspace and code | Complete, unmerged | files and a subprocess sandbox as components |
| 4–5 | The ACP bridge, the RecordingServer | Not Started | your subscription answers the turn |
| 6–9 | The compiler complete, sub-agents, patterns, the wire | Not Started | R3's join; `v0.1.0` |

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
