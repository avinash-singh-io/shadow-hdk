---
type: Research
date: 2026-09-18
status: adopted — Epic 0009 is derived from it
topics: [planning, admission, harness-as-data, blueprint, distribution, languages, sub-agents, durability, scope]
---

# What belongs in the kit — dynamic planning re-derived, the harness as data, and the line around the substrate

**The question** (the owner, 2026-09-17/18): Phase 36 *dynamic planning* is on the roadmap with
`deps: 34, 35`. Why? What is it for? And — since the kit is a substrate that products compose
harnesses from, and the owner's vision is an agent that composes a harness for each intent, saves
it, re-runs it on new data, schedules it, and ships it anywhere — what must be *in* the kit, what
must *never* be, and how does a product consume it at any depth?

**The method.** Read the tree, not the row: the grammar (`kernel/composition.py`), the `compose`
meta-tool (`adapters/agent/component.py:474`), the child registry (`runtime/children.py`), the
`Composed` and `Spawned` events, the patterns shipped as files, Phase 33's authority types; then the
roadmap's principles 4, 5, 7, 8, 12, 13, 15 and the admission rule of the 09-14 research note. Every
claim below names the primitive it rests on.

## 0. The test for entry — four checks, all must pass

1. **Field or port.** ≥2 of the eight reference runtimes have it, *or* every product would
   otherwise reimplement it (the admission rule, `2026-09-14-what-a-harness-development-kit-owes-its-products.md` §0).
2. **Mechanism, not meaning.** It never names a user, a tenant, a domain object, a business rule
   or a screen; the bare-harness test stays green with zero product words.
3. **Shape.** New vocabulary enters only as a value with a *narrower-than* order (so `meet` and the
   narrowing proof still hold), a port, an adapter, a pattern file or a data type. A runtime branch
   on a provider, product or use-case name is a defect (principle 4).
4. **Loop or consumed.** If it is not the loop — governance by effects, leases, the sink, the
   record — it is consumed behind a port, never built (principle 5).

## 1. Dynamic planning, re-derived — what it needs, primitive by primitive

| a planner needs | the primitive | since |
|---|---|---|
| a typed plan a developer could also write | `Composition` — `Invoke · Sequence · FanOut · Until · Await` | Phase 0 |
| a way for a model to author one | the `compose` meta-tool → `load(json, Composition)` | Phase 8 |
| who may plan at all | a pattern: `single` offers no `compose`; `orchestrator-workers` does — data | Phase 8 |
| running it safely | a child run with a lease carved from the parent's *remaining*; every step judged on effects | Phases 6–7, 23 |
| the plan on the record | `Composed` — "emitted every time the composition changes, so plan-versus-actual comes for free" | Phase 0 |
| authority to admit against | `AuthoritySnapshot` with a digest | Phase 33 |
| declared effects without invoking | every `Registration` carries an `EffectProfile`; `GovernancePort.judge(effects, context)` takes a profile, not a call | Phase 0 |

Nothing in the table comes from Phase 34 or 35. The deps entered through one phrase in the row —
*"the same typed composition **or harness artifact**"*. Proposing a harness (which tools, modes,
patterns to assemble) is *self-configuration*: 34's consumer, not planning's prerequisite. Code
Mode (35) is already covered by "program has three forms: a composition, a derivation, code in a
sandbox" — code is a `contained` component judged as an effect; compaction is about context size.
**Phase 36 depends on 33 alone.** (D117)

## 2. The purpose — the judgement no step can make

Per-step judgement is blind to every property of the *whole* plan: that a step is the 40th parallel
worker, the fourth level of nesting, that the plan costs more than the lease has left, that step 7
names a tool not in the registry. Today a bad plan is accepted and dies of `lease_exhausted` halfway
— silently, because a lease ending a run is not an error (`component.py:497` records the bite).

So the phase is **admission**: structural limits (depth, fan-out, size), existence (every named
component registered), effects (what per-step judgement would refuse, refused *before* anything
runs), and the plan as a proposal a person can see, approve and later compare with what happened.
It is *not* authorization — Phase 33 still re-reads authority at every irreversible act, so an
admitted plan never carries authority forward (D99 applied to plans). It is *not* a workflow
engine — "a single tool call is a plan of one step" stays literally true. (D107, D108)

## 3. The design, on the kit's own principles

- **Kernel — no new plan type; one new limit type.** The plan *is* the `Composition`. `PlanLimits`
  (depth, fan-out, steps, shares of seconds/cents) carries a narrower-than order so it composes by
  `meet` like effect profiles. Admission is a pure function `admit(composition, registrations,
  limits) → Admitted | PlanRefused(mismatches)`, total and deterministic, mirroring Phase 31's
  `check_compatibility` — refusal is data, the list complete. (D108, D109)
- **Runtime — one place, true for every caller.** Admission inside `children.spawn`, before
  compilation, so it holds whoever authored the plan — the kit's loop, a CLI through the socket, a
  sub-agent, a host over the wire — the way D42 made every effect route through the registry.
  Effects are dry-judged through the run's existing `GovernancePort`; `Refuse` refuses the plan;
  `Ask` parks the **plan** as one question (D121); the irreversible act inside still gets its
  Phase 33 grant. Events `plan_admitted` / `plan_refused` are additive kinds folded into an `Item`.
- **Limits live on the mode, as data** (D64/D66): `ModeSpec.plan`; the shipped modes carry
  defaults; a team's mode can only narrow; a child gets `meet(parent, own)`; `RunOptions.lease`
  stays the hard ceiling. A person at a card can *allow this plan*; nobody can widen a limit.
- **Vendor-agnostic — planning is a component** (D110). Today `compose` is a meta-tool of
  `AgentComponent`, so only the kit's own loop can plan. The precedent is D55: the skills registry
  became a component "so choosing is on the record and reaches every host." A registered `compose`
  component with an empty profile (proposing is not an effect; running is) reaches Claude Code or
  Codex through the socket; the meta-tool becomes sugar; one path, no branch on provider kind.
- **A refused plan is an observation** (D111): the same shape a refused step has today; the
  planner re-proposes, splits, asks or stops; the runtime never trims a proposal. Re-proposals are
  bounded by the lease and the pattern's `max_turns`.
- **A plan may run after its planner** (D112): `carry_out` today absorbs the child into the
  planner's transcript; a pattern field lets the plan run as its own run after `done` — the shape
  that survives a process.
- **Amend is a host handle** (D116): the composition "can be changed mid-flight by the agent or by
  a person" (`09` §5) and `Composed` already fires on every change; the handle is plumbing, and
  the amendment is admitted like the original.

## 4. Naming — sub-agent, run, parent/child

Two levels, both real: a **sub-agent** is a *component* of label `agent` (what you invoke); a
**run** is one governed execution with its own id, lease, checkpoint and events;
**parent/child** is the relation between runs (`Spawned{run_id, child_run_id, lease}`;
`children.py` is the runtime's registry of held child *runs*). The field's word for the thing is
sub-agent (Claude Code, ADK) or handoff (the Agents SDK); for the execution, subgraph or child
run. D61 settles the host-facing surface: *a plan spawns runs; a run may invoke sub-agents; runs
have parents.*

## 5. Long-running, multi-phase, multi-agent — what the substrate already carries

The owner's scenario in the grammar that exists: `Sequence(FanOut(researchers), FanOut(auditors,
inputs = Binding(ref = research handles)), Until(revise, tests pass, 5), Invoke(synthesize,
handles of every phase))`. Phases are `Sequence`; parallel agents `FanOut` of `Invoke` on agent
components; loops `Until`; waiting on a person or a slow job `Await`; background code a
`contained` component; a file handed over an environment root. **Context between phases is
dataflow**: outputs are handles the next phase binds; large results land in the environment as
files with a handle and preview (Phase 21); each sub-agent starts from a brief plus bound inputs
and returns proposals with provenance — context isolation by construction.

Durability today: every child run is checkpointed; a parked run survives the host (D80); a parent
comes back holding its children (D37); the lease survives a park (D33); one holder (D81); the
checkpointer behind `RunStore` (D93); an irreversible act mid-run reconciles to a receipt or an
explicit `unknown` (Phase 33); a failed worker is an observation while siblings continue;
cancellation is branch-level (D15).

What is missing for "start it and close the laptop for three days": **a run that is not a turn**
— a durable, idempotent run *request* with renewal, retry, catch-up and cancellation, timing
consumed behind a port (Phase 37, D115); the plan running after its planner (D112); a redirect
handle (D116). Nothing needs a new step kind — and that is the test: the day a scenario does, it
is a kernel ADR.

## 6. The harness as data — reuse, and the anatomy of a blueprint

The owner's reuse story — build it, save it, re-run it on new data, schedule it, export it, publish
it, embed it — is the middle of Phase 34's ladder: a saved workflow is a **blueprint** (a harness
as data with declared inputs); a **preset** is a blueprint with defaults; a **runnable harness** is
a blueprint instantiated on one machine, for one person, on one set of data. Two facts make every
listed use fall out: *a harness is data*, and *a harness is a component* (its profile the `meet`
of its parts; invoked, admitted recursively, composed into another). (D113)

| a blueprint contains | it never contains |
|---|---|
| the composition with declared parameters; patterns and modes (roles, behaviour, limits); component references (verbs, MCP, skills); requirements (provider, environment); budget and limits; evidence and a digest | a credential; a tenant's data; a standing grant of authority; capabilities (it *requires*, the machine *proves*) |

At every instantiation the inputs and roots, the capabilities and the authority are bound on the
target — selection and admission run again. A saved harness is a proposal every time, never a
grant. (D114) Improvement is a versioned proposal behind a locked evaluator (Rule 11; Phase 40).

## 7. Self-contained — a harness is a distribution

A blueprint is data and data needs an interpreter; the kit is that interpreter, the way LangGraph
is for a graph or Temporal for a workflow. What makes that a dependency rather than lock-in: the
runtime is one MIT distribution, small, embeddable in-process, as a sidecar (`serve --stdio`) or
as a service — and **a harness ships with it pinned inside**. `shadow-hdk bundle --as wheel | oci
| binary | dir` emits a locked, reproducible artifact with generated entry points (`run`, `serve`,
`explain`, `check`); the consumer installs *the harness* (`uv tool install …`, `docker run …`),
never "a Shadow runtime". What stays on the target by design: Python or a container runtime, the
person's CLI sign-in or a key (never bundled, D41), the OS sandbox proved at first run, and
`check` naming what this machine cannot meet before the first run. (D118)

## 8. Other languages — one runtime, many surfaces

"Runs on a different language" is two different things. **The surface** — the product, its tools
and its policy in Go/TypeScript/Java, the loop in the harness process beside it — costs a
generator per language: a client and port stubs from the published schemas, a scaffold per
language/framework, the harness as a sidecar, inverted ports over the wire (D21) so the host's
governance and components run in the host's language. Temporal's shape. **The runtime** — the
loop reimplemented in another language — costs a second implementation held to parity forever, and
N implementations are N places for the guarantees to diverge. The kit gives the first in full and
keeps the second possible (every kernel type is a JSON Schema that round-trips in CI) but unbuilt
until an adopter needs in-process execution and the contracts have held across two releases.
Components are already language-neutral (MCP; code in the sandbox). Export encodings are
adapters; compile-to-X waits for a shared target format. (D119, D120)

## 9. The map — what the kit holds, layer by layer

| layer | in the kit today | to add (Epic 0009) | never — the product's, or consumed |
|---|---|---|---|
| kernel | effects and the meet · the grammar · observations · leases · events · ports · capabilities/requirements/evidence · authority, staged effects, grants, journal · records · rules · workspace · JSON Schema for all | `PlanLimits` + `admit()` · declared parameters · `HarnessSpec` · `RunRequest` · `plan_admitted`/`plan_refused`/`amended` | any product type; a message model; a user; a schema |
| runtime | the governed step · `run`/`resume` · spawn/send/release · `Conversation` · `Thread` · `Approvals`, `Parked`, `ask_person` · `Fold`→`Item` · `StreamSession` · offer/relay · checkpoints behind `RunStore` · the meter | admission in `spawn` · a harness as a component · run-after-planner · the amend handle · request lifecycle (timing consumed) | a scheduler service · an authorization engine · rate limiting, CORS, metrics endpoints |
| adapters | models · agents (JSONL, ACP, `ModelAgent`) · components (callable, MCP, environment, recording, devices, derivation) · governance (modes, rules, `Routed`) · stores · sinks · OTel | a trigger adapter (cron/queue/webhook) · the bundle adapter (OCI at the edge) · client and stub generators per language · (later: UI plane, memory, peers) | a vendor's semantics in the kernel; a credential store; a sandbox built rather than proven |
| data the host supplies | patterns · modes · rules · skills · providers · batteries · budgets · vocabulary | blueprints · presets · plan limits on a mode · evaluator corpora | the settings ladder; entitlements; who may author what |
| facade | `harness.toml` · `Harness` · `ServeHost`/`a_thread` · `serve` · protocol v3 + TypeScript client · `shadow_hdk.testing` | `shadow-hdk run <blueprint>` · `explain` · `check` · `bundle` · the Shadow Harness reference presets from public parts only | a marketplace; billing; a UI |

## 10. The ladder — as simple as one line, as deep as a port

| depth | you touch | you control | the kit keeps |
|---|---|---|---|
| 0 · run a preset | `shadow-hdk run coder --input repo=.` | the inputs | everything |
| 1 · configure | `harness.toml`; modes, rules, skills, providers, batteries, budgets as data | policy and behaviour, live | the loop, the record, the environment, admission |
| 2 · compose | `Harness(...)` / `a_thread(...)` with handed pieces | which pieces | how they run together |
| 3 · own | `Thread` / `Conversation` / `run()` over your ports and stores (proven by the suites) | composition, state, the record's home | the governed step, leases, events, admission, authority at the act |
| 4 · extend | a new adapter, transport, provider file, pattern; a step kind only by ADR | the edges | the kernel's semantics |

Every rung is the rung below with one thing handed in; a product can stop anywhere and drop one
rung for one piece without leaving the others.

## 11. The never list

Users, tenancy, organisations (opaque `principal`/`attributes`, D82) · a domain model or message
schema (D62) · an authorization engine (plugs behind `GovernancePort`/`AuthorizerPort`) · a
scheduler, queue, marketplace, billing, UI · planner strategies as code · exactly-once, full
containment, "controlled" by name · a credential, ever (D41) · any string a product would fork to
change (principle 8).

## 12. The plan — Epic 0009

Phases, ordered by `deps`: **36 plan admission** (33) → **34 the harness as data** (36) →
**37 the durable run request** (33, 34). Released per phase, `tdd: strict`. D107–D121 settled in
`specs/epics/0009-the-harness-as-data.md`. Pre-work: this note; the roadmap re-derived; TD-010/011
closed (shipped by Phase 33); the board's row and Pins for v0.30.0; ENH-020 → v0.30.1.

**Open for the phase brainstorms, not for this note:** the exact `PlanLimits` fields and their
defaults on the four shipped modes; whether a plan `Ask` and a step `Ask` share one card kind on the
wire; the bundle manifest's exact fields; which non-Python language proves the scaffold first
(TypeScript, because the client exists); the `RunRequest` renewal interval and what a missed
window means for a cron trigger. Each is a phase group's RED corpus, derived when the phase starts.
