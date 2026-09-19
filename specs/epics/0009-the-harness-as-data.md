---
type: Epic
id: "0009"
slug: the-harness-as-data
status: planned
owner: Avinash
started: "2026-09-17T19:26:57.219Z"
phases: [phase-36-plan-admission, phase-34-the-harness-as-data, phase-37-the-durable-run-request]
policy_release: per-phase
policy_push: per-phase
policy_tdd: strict
---

# Epic 0009 — the-harness-as-data

## Objective

An agent or a developer proposes a plan or a whole harness as data; the host admits it under limits, capabilities and current authority; an admitted harness is saved with declared inputs, re-run on new data, scheduled, exported as a self-contained distribution with its runtime pinned inside, scaffolded for other languages as surfaces over one runtime, and composed into other harnesses - with the kernel's grammar, the record and the authority transaction unchanged.

## Decisions

> Settled once; never re-asked. Per-phase specs are derived from this table.

| # | Decision | Rationale |
|---|---|---|
| D107 | **A plan is a `Composition`; a harness is data.** No new grammar; a new step kind stays a kernel ADR | "a single call is a plan of one step" stays literally true; the reuse story needs no second workflow language |
| D108 | **Admission is whole-plan judgement, not authorization.** Structural → existence → effects; the mismatch list is complete; Phase 33 still authorizes each irreversible act at the act | Per-step judgement cannot see fan-out, depth, total cost or a missing tool; approval never carries authority forward (D99) |
| D109 | **Limits are order-bearing values** narrowing host → mode → parent by `meet`; carried on the mode as live data; the lease is the floor | New vocabulary enters only in a shape the narrowing proof covers; policy is data (D64, D66) |
| D110 | **Planning is a registered component**; the loop's `compose` meta-tool is sugar over it | D42/D55 precedent: a registry entry reaches a resident CLI through the socket; one path, no branch on provider kind |
| D111 | **A refused plan is an observation.** The planner re-proposes or asks; the runtime never trims a proposal | Principle 13 both ways: the host admits, the planner proposes, nobody edits the other's artifact |
| D112 | **A plan may run after its planner** — a pattern field; a run may outlive the turn that proposed it | Principle 12; the shape that survives a process |
| D113 | **A harness is a component**: its profile is the `meet` of its parts; invoked, admitted and composed like any component; declared parameters bound at instantiation | Recursion by design (`09` §6); reuse without a second mechanism |
| D114 | **A blueprint carries requirements and limits — never capabilities, credentials, tenant data or standing authority.** Selection and admission re-run at every instantiation | The same artifact on a different machine, for a different person, gets a different verdict — correctly (D41, D96, D99) |
| D115 | **A run request is durable and idempotent.** The scheduler owns timing, consumed behind a port, never authority | Build the loop, consume the rest (principle 5) |
| D116 | **Amend is a host handle**, on the record; admission applies to the amendment | Principle 7; `Composed` already fires on every change of the composition |
| D117 | **Deps re-derived:** 36 needs 33 only; 34 exists for the blueprint layer, not human presets; 35 is orthogonal and later | The phrase "or harness artifact" imported 34 into 36's deps; Code Mode is already a contained component; compaction is about context size |
| D118 | **A harness is a distribution** that ships with its runtime pinned inside; never a separate runtime to operate | The SQLite relationship: the file is portable, the engine is small, free and embedded; no dependency on any product |
| D119 | **One runtime, many language surfaces.** Generated client, port stubs and scaffold per language from the schemas; every surface passes the same contract suites over the wire. A native runtime in another language is a non-goal until an adopter needs in-process execution in it and the contracts are stable across two releases | N runtimes are N places for the guarantees to diverge; Temporal's shape — one runtime, the host's code in the host's language through inverted ports (D21) |
| D120 | **A harness runs on the Shadow runtime.** Export encodings are adapters; compile-to-X is admitted only when the field shares a target format | What survives export is the shape, not the guarantees; saying so up front stops a later phase promising "runs anywhere" and delivering `observed` |
| D121 | **One question for the plan.** An `Ask` at admission parks the plan as a single question; the acts inside still get their Phase 33 grants | A person approves *this plan*, not five cards; consent ≠ authority holds unchanged |

## Phases

| Phase | Builds | Depends on |
|---|---|---|
| 36 — plan admission | `PlanLimits` + `admit()` in the kernel; admission inside `children.spawn`; `plan_admitted` / `plan_refused` events and their fold; planning as a registered component; limits carried on the mode; run-after-planner as a pattern field; the amend handle; wire and TypeScript parity | 33 |
| 34 — the harness as data | Declared parameters on a composition; `HarnessSpec` → blueprint → preset → runnable; a harness as a component; harness admission with the capability check; bundle export/import (`harness.toml` + files + composition JSON); `shadow-hdk run <blueprint>`, `explain`, `check`; the reference presets from public parts only; `shadow-hdk bundle --as wheel \| oci \| binary \| dir \| scaffold:<lang>` with the kit pinned inside; generated clients and port stubs per language; reproducible builds | 36 |
| 37 — the durable run request | `RunRequest` with identity, idempotency key and retry/catch-up policy as data; create, renew, cancel; a run that is not a turn; recovery after process death on SQLite and Postgres; a trigger port with cron, queue and webhook reference adapters; timing consumed, never authority | 33, 34 |

Order is computed from `deps`: 36 → 34 → 37. Each phase releases on its own (v0.31.0, v0.32.0, v0.33.0).

## Non-goals

- Context engineering (35), UI-plane adapters (38), peers (39) and governed evolution (40) — later roadmap capabilities
- Any product concept: users, tenancy, domain schema, a message model, a UI, a marketplace or publishing service, billing
- A scheduler *service*; the epic ships the request contract and reference trigger adapters, and consumes timing
- A native runtime in another language, or a compile-to-X target (D119, D120)
- Exactly-once effects across an external system; planner strategies as code; a credential in any artifact

## Completion criteria

> Checkable. "It works" is not a criterion.

- [ ] A plan exceeding depth, fan-out, step count or budget share is refused **before** compilation with every mismatch listed; the same plan one unit inside the limits is admitted and spawned
- [ ] A plan naming an unregistered component is refused by name; nothing is invoked
- [ ] A plan containing a step the policy would refuse is refused at admission; a step the policy would ask about parks the **plan** as one question, and the irreversible act inside it still obtains a Phase 33 grant at the act
- [ ] A team mode can only narrow a host's `PlanLimits`; a child run's limits are `meet(parent, own)` — property-tested over arbitrary limits
- [ ] A resident CLI (Claude Code) proposes a plan through the registry socket and it is admitted or refused identically to the in-process loop — measured live
- [ ] A plan admitted with the run-after-planner field completes after its planner's turn has ended
- [ ] An amendment to a running composition is admitted or refused like the original and appears on the record as its own event
- [ ] A blueprint with declared parameters runs twice on different inputs and roots with the same digest and different records
- [ ] A blueprint is invoked as a component of another blueprint; its profile is the `meet` of its parts; admission applies recursively
- [ ] A bundle exported from one host runs on bare `shadow-hdk serve` on another with no product present; `explain` renders it without running it; `check` reports this machine's mismatches before the first run
- [ ] Two clean builds of one blueprint produce byte-identical wheel and OCI artifacts with one digest; the wheel installs into a fresh environment with `uv tool install` and runs on new inputs
- [ ] A scaffold for one non-Python language implements the ports in that language, drives the harness as a sidecar, and passes the contract suites over the wire
- [ ] A `RunRequest` created twice with one idempotency key yields one run; a process killed mid-run resumes the same logical run on SQLite and on Postgres without repeating a receipted effect
- [ ] A cron, a queue and a webhook reference adapter each create a `RunRequest`; catch-up and cancellation policy are data and are exercised
- [ ] The bare-harness test stays green with zero product words; every new public type appears in the JSON Schemas, the TypeScript client and the API export invariants
- [ ] The full non-live gate is green at each phase boundary; each phase ships as its own release with a re-pinned example chapter written from a live run

## Run policy

`release: per-phase`, `push: per-phase`, `tdd: strict` — a gate at each phase's end; no accumulated diff lands on one approval. Pre-work before Phase 36, on a docs branch: the board row and Pins for v0.30.0; TD-010/011 closed (shipped by Phase 33); the status header; ENH-020 as a quick-task → v0.30.1; the research note `specs/research/2026-09-18-what-belongs-in-the-kit.md` as this epic's opening evidence.

## Amendments

> Operator changes made during the run land here, newest last, and become
> inputs to the derivation of every not-yet-started phase.

- 2026-09-18 (Phase 36 G2, proposed by the lane, pending the owner) — **D108/D121 amended:** admission refuses only what no step can see — structure and existence — and *names* the steps the policy will ask about or refuse (`PlanAdmitted.asks`, `.refusals`); each step is still judged at its own invocation through the existing live/park paths. Raising the plan's question at admission collided with D57's park and asked twice for a one-step plan; refusing a plan for one refusable step broke BUG-012's promise. D121's "one question for the plan" is a host presentation over the named asks, not a runtime park.
- 2026-09-18 (Phase 36, proposed by the lane, pending the owner) — **ENH-020 folded into Phase 36 as Group 6** rather than a v0.30.1 quick-task: the honest fix is a public contract addition (the opener names unmapped behaviour; `Thread` and the wire surface it), and Rule 14 makes a contract change a phase.
- 2026-09-19 (Phase 44, the owner's order) — **ENH-030 and ENH-031 land in Phase 44, ahead of Phase 34.** The thread door's inversion for a host's components and the TypeScript host-side `ComponentPort` with a stdio sidecar are two of D119's language surfaces; a product needed them first. Phase 34 keeps the scaffold per language, the bundle and the remaining surfaces; the pinned sidecar binary is Epic 0010 Phase 42's, not this phase's.
