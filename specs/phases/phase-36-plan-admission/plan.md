---
type: Plan
status: in-progress
epic: the-harness-as-data
---

# Phase 36 — plan admission — Plan

```
# Execution:  G0 → G1 → G2 → G3 → G5 → G7
#                       ↘ G4 ↗        (G4 needs G1; G6 is independent; both join before G7)
#                       ↘ G6 ↗
```

> **Derived, not brainstormed.**
> The group breakdown is the one thing the epic CANNOT know — it depends on
> code that exists now and did not when the epic was written. Everything
> above the groups is derived; the groups themselves are authored here.

Depends on: phase-33-authority-at-the-act (complete, v0.30.0).

Run policy: release: per-phase · push: per-phase · tdd: strict. Every group: RED first (the
test fails for the stated reason), the code, a mutation check on each load-bearing assertion,
the records (history, backlog, changelog, this phase's tasks), the four-zero gate.

---

## Group 0 — The evaluator, frozen *(sequential, blocks all)*

The corpus is the phase's contract (Rule 11): versioned, RED before any implementation, and never
edited once a group is green — a v2 corpus is a new file.

- `test_plan_admission.py` under `tests/kernel/`: a frozen corpus of compositions × `PlanLimits` ×
  registrations with the expected `Admitted` / `PlanRefused(mismatches)` — over-depth, over-fan-out,
  over-steps, over-budget, an unregistered component, several reasons at once (the list is complete
  and in stable order), a one-step plan (trivially admitted), nested `FanOut` in `Until`.
- `PlanLimits.meet` property tests (hypothesis): idempotent, commutative, never widens, `meet` with
  the unbounded limit is identity.
- `test_plan_admission.py` under `tests/runtime/`: RED scenarios — a refused plan is never spawned (no
  `Invoked`, no `Spawned`); an `Ask`-worthy step parks the plan as one question and `Approve`
  runs it with the Phase 33 grant still requested at the act; a child's limits are the meet; the
  refusal reaches a `ScriptedModel` planner as an observation; run-after ends the planner's turn
  first; amend admitted / refused.
- Collection fails on the deliberately absent names (`shadow_hdk.kernel.planning`,
  `shadow_hdk.runtime.planning`), exactly as Phase 33 G0 did.

**Commit:** `test(admission): the frozen corpus and the RED scenarios`

---

## Group 1 — Kernel: limits, admission, the plan events

- `kernel/planning.py`: `PlanLimits(depth, fan_out, steps, seconds, cents)` — every field
  `int | None` where `None` is unbounded — with `meet` and `narrower_than` mirroring
  `EffectProfile`; `PlanMismatch(axis, step, required, found)`; `Admitted(plan_digest,
  authority_digest, limits)`; `PlanRefused(mismatches)`; `admit(composition, registrations,
  limits) -> Admitted | PlanRefused` — structural (depth, fan-out, step count, the `Until`
  bound counted) and existence, pure and total; `composition_digest()` canonical, the way
  `StagedEffect.digest` is.
- `kernel/events.py`: `PlanAdmitted` and `PlanRefused` events in the `Event` union
  (`plan_admitted`, `plan_refused`), carrying run, seq, at, the digest, and the mismatches.
- `kernel/contracts.py` + `schemas/`: the new types exported; round-trip tests; the API export
  invariant names them.

**Commit:** `feat(kernel): PlanLimits, admit(), the plan events (D107–D109)`

---

## Group 2 — Runtime: admission in `spawn`; the plan parks as one question

- `runtime/children.py::spawn`: before `run()` — `admit()` over the run's registrations and the
  effective limits; then each `Invoke` step's declared profile through `ports.governance.judge`
  with the run's context marked as admission; `Refuse` → `PlanRefused` event and a refused
  observation to the caller; `Ask` → one `Request` on the host's `Questions` handle for the
  whole plan (D121), the plan spawned on `Approve`, refused on `Deny`; `Allow` → `PlanAdmitted`
  then `run()` as today. A refused plan emits no `Spawned`.
- Effective limits: `RunOptions.plan_limits` (host default) and the run context's limits; a child
  receives `meet(parent, own)`; `spawn_options` carries it.
- `adapters/agent/component.py::carry_out`: a `PlanRefused` outcome becomes the tool result the
  model reads (D111) — "that plan was refused: …", every mismatch listed — never a trimmed plan.
- `runtime/items.py::Fold`: `plan_admitted` / `plan_refused` fold into an item a host can render
  (planned vs refused, with reasons).

**Commit:** `feat(runtime): admission in spawn — refused before compile, parked as one question`

---

## Group 3 — Planning is a component

- `runtime/planning.py`: `PlanComponents` on the `PersonComponents` precedent — one registration,
  `compose`, `EffectProfile()` (proposing is not an effect), whose `invoke` takes a composition
  and hands it to `children.spawn` through `current_run()`; offered through the registry like any
  component, so `Thread.tools()` lists it and a CLI sees it through the socket.
- `AgentComponent.compose`: the meta-tool routes through the same path (D110) — one admission,
  one event stream, no branch on provider kind.
- `serve`/`workshop`: the component in the shipped composition; a mode's `tools_offered` can
  withhold it (a `read-only` mode may still plan; the plan's steps are what the mode judges).
- Live: one turn on Claude Code where the CLI calls `compose` through the socket — admitted for a
  plan inside the limits, refused with the list for one outside. Budget: two turns.

**Commit:** `feat(runtime): compose is a registered component — a CLI plans through the socket (D110)`

---

## Group 4 — Limits on the mode, live *(needs G1; parallel with G2–G3)*

- `adapters/modes/registry.py`: `ModeSpec.plan: PlanLimits | None`; `mode_from_document` parses a
  `[plan]` table (`depth`, `fan_out`, `steps`, `seconds`, `cents`); `judge_mode_document`
  refuses a malformed one by name.
- Shipped defaults on the four modes — conservative, decided in the group with their RED tests
  and recorded in history: `read-only` and `ask` narrower than `workspace-write`, `full` widest.
- The narrowing check: a team's mode may only `meet` the host's; `widens()` extended to plan
  limits; `ModeRegistry.find` hands the run its effective limits; `modes/list` carries them.

**Commit:** `feat(modes): plan limits on the mode — data, live, narrowing only (D109)`

---

## Group 5 — A plan after its planner; amend *(needs G2, G3)*

- `Pattern.absorb: bool = True`; with `False`, `carry_out` spawns the admitted plan as a held child
  and returns; the planner's turn ends; the child runs on, its events on the thread's record,
  its questions on the host's handle (D112).
- Amend (D116): `Thread.amend(handle, composition)` in-process; the composition is admitted like
  the original (same limits, same governance dry-judge); on success the held child takes the new
  composition at its next park or step boundary — `resume` already "takes the plan back in"
  (`children.py`) — and `Composed` fires with it, `plan_admitted` naming the amendment; on refusal
  the running plan is untouched. The mechanism's exact boundary is measured in the group and
  recorded; a limitation found is filed, not hidden.

**Commit:** `feat(runtime): a plan runs after its planner; amend on the record (D112, D116)`

---

## Group 6 — ENH-020: unmapped behaviour is named, not dropped *(independent)*

- `adapters/jsonl/transport.py`, `adapters/acp`: the opener computes `unmapped_behaviour` and
  the returned session carries `unmapped: tuple[str, ...]`.
- `runtime/conversation.py`: read off the session at open and reopen (as `session_id` is);
  `Conversation.unmapped_behaviour`; `Thread.open`, `resume` and `set_mode` surface it.
- Wire: `thread/start`, `thread/resume`, `thread/set_mode` results carry `unmapped_behaviour`;
  TypeScript types generated.
- Backlog ENH-020 closed; `docs/packages/adapters-jsonl.md` and `providers.md` say what a host
  learns and what it should do (hide the model/effort controls for that provider).

**Commit:** `fix(providers): unmapped behaviour is named, not dropped (ENH-020)`

---

## Group 7 — Wire and TypeScript parity, docs, release *(sequential, last)*

- `wire/protocol.py`: `thread/amend`; `plan_admitted` / `plan_refused` over the event stream;
  `ERROR_KINDS` += `plan_refused`; `modes/list` limits; `RunOptions.plan_limits` reachable from
  `thread/start`; schemas regenerated; `clients/typescript` generated, `RemoteError.kind` switches
  on the new kind; `tests/wire` parity for every addition.
- Docs: the package guides under `docs/packages/` (kernel, runtime, adapters-modes, adapters-agent, wire), `docs/consuming.md`
  (a plan, end to end), `0.31.md` under `docs/migrations/`; architecture docs at `/sync-docs`.
- The example (`shadow-hdk-demo/react-app`) re-pinned to 0.31.0 with a chapter written from the
  live run: a plan refused with its reasons, a plan approved as one card, the CLI planning.
- Version 0.31.0; `tests/test_versions.py` `EXPECTED`; `uv lock`; changelog; status; the board's
  H row, Pins and Log line for lane P; tag; publish; the fresh-install smoke.

**Commit:** `docs: 0.31 — plan admission` · `chore(release): 0.31.0`
