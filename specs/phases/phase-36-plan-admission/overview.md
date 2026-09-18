---
type: Phase
status: complete
epic: the-harness-as-data
tags: [planning, admission, limits, modes, component, amend, wire, unmapped-behaviour]
deps: [phase-33-authority-at-the-act]
---

# Phase 36 — plan admission

> **Derived, not brainstormed.**
> Generated from `specs/epics/0009-the-harness-as-data.md` on 2026-09-17 with no
> operator interview (Epic D10). Every decision below was settled when the
> epic was written and is NOT re-litigated here. Decisions are durable;
> plans are perishable — this file is the perishable half.

## Goal

A proposed composition is admitted or refused **as a whole, before anything compiles**: structural
limits (depth, fan-out, steps, budget), the existence of every named component, and a dry
judgement of each step's declared effects — with every mismatch named, as data. Admission is not
authorization: Phase 33 still authorizes each irreversible act at the act. A plan reaches the
runtime through a registered `compose` component, so a resident CLI can plan exactly as the kit's
own loop does; a plan may run after its planner; a running composition can be amended on the
record. Limits are live data on the mode. And, folded in from ENH-020, a behaviour field the
provider cannot take is named at open, never dropped.

Today a plan the lease cannot afford is accepted and dies of `lease_exhausted` halfway — silently,
because a lease ending a run is not an error (`adapters/agent/component.py:497`). After this phase
that plan is refused before its first step, with the reason on the record.

## Inherited decisions

> From the epic record. Never re-asked.

- D107 — **A plan is a `Composition`; a harness is data.** No new grammar; a new step kind stays a kernel ADR _("a single call is a plan of one step" stays literally true; the reuse story needs no second workflow language)_
- D108 — **Admission is whole-plan judgement, not authorization.** Structural → existence → effects; the mismatch list is complete; Phase 33 still authorizes each irreversible act at the act _(Per-step judgement cannot see fan-out, depth, total cost or a missing tool; approval never carries authority forward (D99))_
- D109 — **Limits are order-bearing values** narrowing host → mode → parent by `meet`; carried on the mode as live data; the lease is the floor _(New vocabulary enters only in a shape the narrowing proof covers; policy is data (D64, D66))_
- D110 — **Planning is a registered component**; the loop's `compose` meta-tool is sugar over it _(D42/D55 precedent: a registry entry reaches a resident CLI through the socket; one path, no branch on provider kind)_
- D111 — **A refused plan is an observation.** The planner re-proposes or asks; the runtime never trims a proposal _(Principle 13 both ways: the host admits, the planner proposes, nobody edits the other's artifact)_
- D112 — **A plan may run after its planner** — a pattern field; a run may outlive the turn that proposed it _(Principle 12; the shape that survives a process)_
- D113 — **A harness is a component**: its profile is the `meet` of its parts; invoked, admitted and composed like any component; declared parameters bound at instantiation _(Recursion by design (`09` §6); reuse without a second mechanism)_
- D114 — **A blueprint carries requirements and limits — never capabilities, credentials, tenant data or standing authority.** Selection and admission re-run at every instantiation _(The same artifact on a different machine, for a different person, gets a different verdict — correctly (D41, D96, D99))_
- D115 — **A run request is durable and idempotent.** The scheduler owns timing, consumed behind a port, never authority _(Build the loop, consume the rest (principle 5))_
- D116 — **Amend is a host handle**, on the record; admission applies to the amendment _(Principle 7; `Composed` already fires on every change of the composition)_
- D117 — **Deps re-derived:** 36 needs 33 only; 34 exists for the blueprint layer, not human presets; 35 is orthogonal and later _(The phrase "or harness artifact" imported 34 into 36's deps; Code Mode is already a contained component; compaction is about context size)_
- D118 — **A harness is a distribution** that ships with its runtime pinned inside; never a separate runtime to operate _(The SQLite relationship: the file is portable, the engine is small, free and embedded; no dependency on any product)_
- D119 — **One runtime, many language surfaces.** Generated client, port stubs and scaffold per language from the schemas; every surface passes the same contract suites over the wire. A native runtime in another language is a non-goal until an adopter needs in-process execution in it and the contracts are stable across two releases _(N runtimes are N places for the guarantees to diverge; Temporal's shape — one runtime, the host's code in the host's language through inverted ports (D21))_
- D120 — **A harness runs on the Shadow runtime.** Export encodings are adapters; compile-to-X is admitted only when the field shares a target format _(What survives export is the shape, not the guarantees; saying so up front stops a later phase promising "runs anywhere" and delivering `observed`)_
- D121 — **One question for the plan.** An `Ask` at admission parks the plan as a single question; the acts inside still get their Phase 33 grants _(A person approves *this plan*, not five cards; consent ≠ authority holds unchanged)_

## Scope

**In:**

- Kernel: `PlanLimits` with a narrower-than order and `meet`; `admit(composition, registrations,
  limits)` — pure, total, deterministic — yielding `Admitted` or `PlanRefused(mismatches)`;
  `PlanMismatch` typed like `CapabilityMismatch`; a canonical composition digest; `plan_admitted`
  and `plan_refused` event kinds; JSON Schemas for all of it
- Runtime: admission inside `children.spawn` before compilation — structural and existence via
  `admit()`, effects dry-judged through the run's own `GovernancePort`; `Refuse` refuses the plan,
  `Ask` parks the **plan** as one question through the host's `Questions` handle (D121), `Allow`
  spawns as today; a refused plan returned to its author as an observation (D111); the fold
  carries plan items; effective limits `meet` down to a child
- Planning as a registered component (`compose`, empty effect profile) offered through the
  registry, so a resident CLI plans through the socket; `AgentComponent`'s meta-tool becomes sugar
  over it (D110)
- Limits on the mode: `ModeSpec.plan`, parsed from mode documents, defaults on the shipped four,
  a team mode narrows only, read live (D109)
- A plan that runs after its planner: a pattern field; the planner's turn ends, the child runs on
  as a held run on the record (D112)
- Amend: a host handle that proposes a new composition for a running plan; admitted like the
  original; on the record (D116)
- ENH-020: the JSONL/ACP openers report behaviour fields the provider maps no flag for; `Thread`
  surfaces them on open, resume and `set_mode`, and the wire carries them
- Wire and TypeScript parity for every new event, method and result; `0.31.md` under `docs/migrations/`;
  the package guides; the example re-pinned with a chapter written from a live run; **v0.31.0**

**Out:**

- Declared parameters, `HarnessSpec`, blueprints, bundles, scaffolds — Phase 34
- The durable run request, triggers, retry and catch-up — Phase 37
- Generative UI, a plan *editor*, any product rendering — Phase 38 and the product
- Planner strategies: how an agent decides what to plan stays a pattern file
- Any new step kind in the grammar (a kernel ADR, not this phase)

## Deliverables

| Deliverable | Verification |
|---|---|
| Frozen admission corpus (legal / illegal plans × limits × registrations → expected outcome) and the RED runtime scenarios | `uv run pytest -q tests/kernel/test_plan_admission.py tests/runtime/test_plan_admission.py` — collection fails on the absent names first, then RED for the stated reasons |
| `PlanLimits`, `meet`, `admit()`, `Admitted`, `PlanRefused`, `PlanMismatch`, the composition digest, the two events, their schemas | kernel unit + property tests; JSON round-trip; `uv run python -m shadow_hdk.kernel.contracts` regenerates `schemas/` with no drift |
| Admission in `spawn`; the plan parks as one question; a refused plan is an observation; the fold | runtime tests with `ScriptedModel`/`ScriptedAgent`; a mutation removing the pre-compile check makes the *never spawned* assertion fail |
| `compose` as a registered component; the meta-tool as sugar | registry tests; `Thread.tools()` lists it; one live turn on Claude Code planning through the socket (`uv run pytest -m live -k plan -rs`) |
| `ModeSpec.plan`, mode documents, shipped defaults, narrowing check, live read | modes tests; the `widens()` property extended; `modes/list` shows limits |
| Run-after-planner (pattern field) and the amend handle | runtime tests: the planner's turn ends first; an amendment admitted/refused like the original; `Composed` + the plan event on the record |
| ENH-020 named, not dropped | jsonl/acp tests: a Codex-shaped provider with `Behaviour(system=…)` names `system` on open; `Thread.open/resume/set_mode` and `thread/*` results carry it |
| Wire + TypeScript parity, docs, migration note, release | `tests/wire` parity tests; `npm run generate && npm run check && npm run build`; `tests/invariants`; four-zero gate; `momentum okf check .`; v0.31.0 tagged and published; the example re-pinned |

## Acceptance criteria

> Checkable. "It works" is not a criterion.

1. A plan exceeding depth, fan-out, step count or budget is refused **before** compilation with every mismatch listed (axis, step, required, found); the same plan one unit inside the limits is admitted and spawned. No `Invoked` event precedes a refusal.
2. A plan naming an unregistered component is refused by name; nothing is invoked.
3. A step the run's policy would refuse refuses the plan at admission; a step it would ask about parks the **plan** as one question on the host's `Questions` handle; answered `Approve`, the plan spawns and the irreversible act inside it still obtains its Phase 33 grant at the act — the approval is on the record, the grant is separate.
4. `PlanLimits.meet` is idempotent, commutative and never widens, property-tested over arbitrary limits; a child run's effective limits are `meet(parent, own)`; a team mode cannot widen the host's.
5. A resident CLI (Claude Code) proposes a plan through the registry socket and it is admitted or refused with the identical events and observation as the in-process loop — measured live, one turn.
6. With the run-after field set, the planner's turn ends before the plan's child run completes; the child is a held run on the thread's record and its events reach the host.
7. An amendment to a running plan is admitted or refused like the original; on success `Composed` fires with the new composition and a plan event names the amendment; on refusal the running plan is untouched.
8. A refused plan reaches its author as an observation in the same shape as a refused step; the runtime never alters the proposal.
9. A `Behaviour` field the provider maps no flag for is named on `Thread.open`, `resume` and `set_mode` and on the wire; nothing is silently dropped (ENH-020 closed).
10. Every new event, result and error kind crosses the wire and the generated TypeScript client identically; the bare-harness test stays green; schemas show no drift; the four-zero gate and OKF are green; v0.31.0 is released with the migration note and the example's chapter written from the live run.

## Acceptance at completion — 2026-09-18

Each criterion above, and what it came to. The criteria are left as written; two came out
differently from the text and say so here rather than being edited to match what was built.

| # | verdict | evidence |
|---|---|---|
| 1 | met | `tests/benchmarks/plan-admission-v1.json` (9 cases, digest pinned) + `tests/runtime/test_plan_admission.py`; a mutation removing the check makes *never spawned* fail |
| 2 | met | the existence axis; the refusal keeps the wording a CLI and a model already read |
| 3 | **amended** | Admission **names** a step's ask or refusal (`plan_admitted.asks` / `.refusals`); it does not pre-empt it. Raising the plan's question at admission broke D57's park where no `Questions` handle exists and asked twice where one does; refusing a plan for a step the step itself can refuse broke BUG-012's promise that the planner sees every result. Each step is still asked, parked or refused live at its own invocation, and the irreversible act inside still obtains its Phase 33 grant. D121's single question becomes a host presentation. Recorded as Epic 0009's amendment, **pending the owner's confirmation** |
| 4 | met | hypothesis properties for `meet`; `spawn_options`; `widens_plan` refuses a mode that widens |
| 5 | **met on Codex, owed on Claude Code** | Codex CLI 0.154.0 proposed `fan_out(read_a, read_b)` through the socket; two admissions on the record, both steps through our registry; 2 turns, 4 steps, 17.4 s. Claude Code is signed out on this machine (`loggedIn: false`) — the owner's to fix; the identical-events half is proven for one CLI, not yet two |
| 6 | met | `Pattern.absorb=False` → `Children.defer` → `run_deferred` after the step closes |
| 7 | met | `tests/runtime/test_a_plan_is_amended_on_the_record.py` (5) and the wire's refused-then-admitted pair |
| 8 | met | `Refused(str(refused))` to the offer, the tool result to the model, `PlanNotAdmitted` to a caller |
| 9 | met | ENH-020 closed; session, thread and wire tests |
| 10 | met, less the example's chapter | four-zero gate, OKF, schemas without drift, `npm run generate/check/build`; the demo's re-pin to 0.31.0 **consumes the kit from PyPI**, so its chapter follows the publish, as 0.29.1's did (ENH-021) |

## Run policy (inherited)

release: per-phase · push: per-phase · tdd: strict
