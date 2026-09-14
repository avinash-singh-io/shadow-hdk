---
type: Status
---

# Project Status

> **Last Updated**: 2026-09-15 — Phase 32 started; Epic 0008 continues
> **Current Phase**: **Phase 32 — one agent surface** is active on the stacked epic branch.
> Phase 31 now establishes typed provider/environment capabilities, evidence and host execution
> requirements before anything is built on their selection. Phase 33 (authority at the act) remains
> derived and independent after 31. The epic releases once as **v0.30.0**.
>
> 1,600 non-live tests; mypy strict over 422 files; one distribution, `shadow-hdk`, still at
> **0.29.1**, MIT, on PyPI. Phase 31 is pushed but intentionally unmerged and unreleased.
>
> **Latest Release**: **v0.29.1**, released 2026-09-14 — BUG-044 closed: `ask_person` answered `park` is kept, not answered `Parked()`; found by the React example wiring D88 to an input card. Before it **v0.29.0** — Phase 30, a product owns what it owns
> (D87–D94): `Conversation`, `Parked` and `turn(on_question="park")`, the agent streams, tokens
> on `Spent`, `shadow_hdk.testing`, `Questions`, `Routed`, typed refusals, `RunStore`,
> `ThreadRecord.version`, `idle_seconds`, a stream that reattaches. Contract change (additions;
> `RunOptions.approvals` typed on the port), so a *Pins* row. Before it **v0.28.0**, released 2026-09-14 — Phase 29, one app server behind every
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
that adopter, and it lives in the shared roadmap rather than here. **Thirty phases are built,
merged and released; Phase 31 is complete on the unreleased epic stack**: 1,600 non-live tests,
mypy strict over 422 files, one public distribution at 0.29.1. Epic 0008 is the v0.30.0
production-boundary release train.

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
| 30 | A product owns what it owns | Complete, merged | **v0.29.0** |

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
| 32 — one agent surface | `phase-32-one-agent-surface` | in progress | Group 0 — lock the strict RED lifecycle evaluator |

## Unreleased Epic Checkpoints

| Phase | Branch | Evidence | Release |
|-------|--------|----------|---------|
| 31 — a host knows what it can trust | `phase-31-a-host-knows-what-it-can-trust` | 1,600 full-suite passes; 422 typed files; docs/schema/benchmark green | waits for Phase 33 and v0.30.0 |

## Upcoming Phases

> Epic 0008 is scheduled under a strict test-first, per-feature release policy. Intent Studio may
> continue product-owned work, but its new Shadow execution integration waits for the verified
> v0.30.0 handoff after all three phases.

| Phase | Depends on | Makes true |
|------|------------|------------|
| 32 — one agent surface | 31 | CLI and API-model agents use one durable product-facing lifecycle |
| 33 — authority at the act | 31 | controlled irreversible effects are current-authority, journaled and recoverable |
| 34 — Shadow Harness, built to unfold | 32, 33 | the ready-made harness and HDK are progressive layers of one system |

## Blockers

| ID | Description | Severity |
|----|-------------|----------|
| _(none)_ | | |

## Critical Items (P0)

| ID | Type | Description |
|----|------|-------------|
| _(none)_ | | The audit's P0s (BUG-004–007, TD-009) closed in Phases 17–18; open now: ENH-005–008 (P2–P3) — see the backlog |

## Next Actions

1. Start Phase 32 from its derived strict-TDD plan; lock the one-agent lifecycle evaluator before implementation
2. Complete Phases 32–33 with fresh evidence at each boundary; one merge and one v0.30.0 release at epic completion
3. Hand v0.30.0 and its capability matrix/migration notes to Intent Studio; do not patch its execution layer in advance
4. Still conditional: a Linux host for the remaining containment proofs and a lawyer's read on AGPL at arm's length

## Key Decisions Made

- D1–D13 in `specs/architecture/decisions.md`, settled at founding from `09` and the founding conversation; recorded on Epic 0001
- D14–D22 settled per phase: D15 cancellation (6), D16 held children (7), D17 files and D18 compaction (8), D19 state-as-JSON, D20 `Spent`, D21 the crossed context (9). **D22 — the port set is open**: six is a count, not a constraint, settled by the owner 2026-09-10, which closes O4
- **D95–D106** are settled once in Epic 0008: one Shadow/two surfaces; typed capability-requirement evidence; provider/environment/authority separation; one agent surface; approval separate from authorization; revisioned act-time authority; crash-safe effect transactions, grants, uncertainty and journal; product ownership; standards at adapters
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
