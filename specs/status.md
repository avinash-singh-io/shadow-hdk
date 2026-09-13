---
type: Status
---

# Project Status

> **Last Updated**: 2026-09-14 (v0.28.0 — Phase 29, one app server behind every surface; D79–D86)
> **Current Phase**: **none — Phase 29 (one app server behind every surface) is complete and released as v0.28.0**: the record chooses its store (D79), a parked turn survives the host (D80), one thread one holder (D81), identity on the thread and scope on the rows (D82), batteries live (D83), the budget on the record (D84), the rules the field has (D85), operations and the per-run token closed (D86); BUG-041, BUG-042 and ENH-013 closed on the way. Before it: **Phase 28 (the workspace) is complete; v0.26.0 proved the
> packages as published artefacts (the providers wheel built for the first time, BUG-035; every
> wheel built and looked into; a clean-venv install serving); v0.26.1 readied the publish
> workflow for eighteen names, which never ran; v0.27.0 makes them one — `shadow-hdk` with
> extras (D78) — and is the first release published to PyPI.** Phase 28, released as v0.25.0:
> Opened from the owner's review and a demo run from outside the tree (`../harness-demo/`).
> The registries visible (D73); a child run judged in its parent's context (BUG-030, D74); the
> `ask` mode and every CLI built-in off (BUG-031, D75); the workspace as one or many roots,
> chosen per thread and added live, the environment and the provider following the mode
> (BUG-032, D76), minted skills kept. Next: Phase 30 (context engineering) and Phase 31
> (collaboration), the owner's call.
>
> 1,514 tests; mypy strict over 400 files; one distribution, `shadow-hdk`, at **0.28.0**, MIT, on PyPI.
>
> **Latest Release**: **v0.28.0**, released 2026-09-14 — Phase 29, one app server behind every
> surface (D79–D86): `[store] url` (sqlite | Postgres, the `[postgres]` extra), a parked turn
> resumed after a restart, a thread's hold, `principal`/`attributes` and `scope`, batteries as
> rows, `budget`/`spent` on the record, `ask` and `deny` rules in every mode, `/healthz` and
> `admin/*`. Contract change (new parameters and methods; the `ThreadStore` port grew), so a
> *Pins* row. Before it **v0.27.2**, released 2026-09-13 — the React example's approval cards:
> a call the mode asks about is one item, named and kept across its park (BUG-040). Before it
> **v0.27.1** — the example's first connect: the SSE stream opens with a frame (BUG-038), the
> TypeScript client runs in a browser and is a package (BUG-039). Before it **v0.27.0** — one distribution with extras (D78);
> BUG-036, BUG-037; mypy over the whole tree; the sdist declared; published to PyPI. Before it
> **v0.26.1** (the URLs and classifiers; the publish workflow, tagged but never released — it
> would have published eighteen names). Before it **v0.26.0** — the packages
> proven as published artefacts (BUG-035, the wheel invariant, the clean-venv proof). Before it v0.25.3 (BUG-034; the
> specs synced), v0.25.2 (D77 — `start_held`,
> `LineBuffer`, the root-name rule), v0.25.1 (a battery's process
> held, BUG-033; Claude Code from a clean scope, ENH-012) and **v0.25.0** — Phase 28, the workspace (D73–D76).
> Contract change (roots, `WorkspaceChanged`, `tools/list`, `skills/list`, `thread/add_root`,
> `AgentPort.open(resume=)`, the `ask` mode, a child's context), so a *Pins* row. Before it
> v0.24.0 (Phase 27, batteries and the facade, D70–D72), v0.23.0 (Phase 26, any language, D67–D69), v0.22.0
> (Phase 25, the host's controls, D61–D66), v0.21.0 (the words, mid-phase), v0.20.0 (the studio inline; seven bugs found by using it, D59,
> D60), v0.19.0 (hardening to Phase 24: D57 park, D58 live, `Questions`, Codex measured), v0.18.0 (Phase 24, the skill registry), v0.17.0 (Phase 23, a host —
> the consumable line), v0.16.0, v0.15.0, v0.14.0, v0.13.1. All MIT
> **Health**: On Track

## Summary

shadow-hdk is the generic agentic system designed in
`intent-ecosystem/vision/09-the-agentic-system.md`: a runtime that runs an agent over an open set of
components under a governance policy and hands what it produces to whoever is listening. It governs
effects, not names; the agent's plan is data compiled to a LangGraph graph; the runtime acts through
components and records through the sink. One distribution — kernel, runtime, wire, providers, serve, adapters — one import
name, six ports. Any system that implements the six ports is its intended user, and this repository
plans for none of them in particular — which adopter reaches which capability when is a fact about
that adopter, and it lives in the shared roadmap rather than here. **Twenty-eight phases are built,
merged and released**: 1,439 tests, mypy strict over 377 files, one distribution at 0.27.2.

## Completed Phases

> Every phase is merged and released. `main`, `staging` and the phase branches met at
> `c0bc9e7` on 2026-09-10; each phase carries a `phase/NN-*` tag, and the release column is
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
| 25 | The host's controls | Complete, merged | **v0.22.0** |
| 26 | Any language | Complete, merged | **v0.23.0** |
| 27 | Batteries and the facade | Complete, merged | **v0.24.0** |
| 28 | The workspace | Complete, merged | **v0.25.0** |
| — | the packages as published artefacts; published to PyPI | Complete, merged | **v0.26.0**, **v0.26.1** |
| — | one distribution with extras (D78); the React example's finds | Complete, merged | **v0.27.0**, **v0.27.1**, **v0.27.2** |
| 29 | One app server behind every surface | Complete, merged | **v0.28.0** |

## Ad-hoc / Patch Releases

| Version | Date | Type | Summary |
|---------|------|------|---------|
| v0.25.3 | 2026-09-13 | patch | BUG-034 the mode in `harness.toml`/`--mode`/`Harness(mode=)` is a mode id (`ask` included), refused by name at open; `requires` refuses an unknown environment name; the architecture specs synced to the tree |
| v0.25.2 | 2026-09-12 | patch | D77 one rule, one implementation: `start_held` the one place a session leader is started (an invariant refuses the next copy); `LineBuffer` the one framing; a root's name a rule, not an `exists()` guess |
| v0.25.1 | 2026-09-12 | patch | BUG-033 a battery's MCP server is a held session leader, ended with its group; ENH-012 Claude Code launched with no settings sources and no auto-memory — a run's instructions are the mode's behaviour only |
| v0.25.0 | 2026-09-12 | phase 28 | the workspace: one or many roots per thread, added live; the environment and the provider follow the mode; the `ask` mode; the registries visible; a child judged in its parent's context (D73–D76) |
| v0.24.0 | 2026-09-12 | phase 27 | batteries and the facade: a battery is a file (wigolo, ddgs), `Harness.load` and `harness.toml`, `budget`, the optimiser specified (D70–D72) |
| v0.23.0 | 2026-09-12 | phase 26 | any language: the thread, the handles and the store over the wire; `shadow-hdk serve`; the TypeScript client; the studio on the wire (D67–D69) |
| v0.22.0 | 2026-09-12 | phase 25 | the host's controls: Thread/Turn/Item/Activity, modes = policy + behaviour, rules and input, the Store (D61–D66) |
| v0.21.0 | 2026-09-12 | phase 25 (mid) | the record speaks the industry's words (D61) |
| v0.20.0 | 2026-09-12 | hardening | the studio inline; five scenarios; BUG-023–029 closed (D59, D60) |
| v0.19.0 | 2026-09-12 | hardening | BUG-020/021/022 closed (D57, D58); Codex measured; the studio |

## Active Phase

| Phase | Branch | Status | Progress |
|-------|--------|--------|----------|

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
| _(none)_ | | The audit's P0s (BUG-004–007, TD-009) closed in Phases 17–18; open now: ENH-005–008 (P2–P3) — see the backlog |

## Next Actions

1. Phase 29 (context engineering) and 30 (collaboration), the owner's call
2. Codex measured on `tools/list_changed`, `--resume` and its clean scope (`AGENTS.md`, `config.toml`) when a Codex turn is next spent
3. Owner-gated, unchanged: ADR-1, ADR-2, a Linux host for the containment proofs, a lawyer's read on AGPL at arm's length

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
- 2026-09-10 — the kernel, two invariants and the strict-xfail bare-harness test (`16eb1fd`, `4047434`)
