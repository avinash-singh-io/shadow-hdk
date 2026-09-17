---
type: Tasks
status: in-progress
epic: the-harness-as-data
---
# Phase 36 — plan admission — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12).
> **TDD strict:** no task may be marked `[x]` without a recorded red→green.

## Group 0 — The evaluator, frozen *(blocks)*
- [x] `plan-admission-v1.json` under `tests/benchmarks/` (9 cases, 3 meet rows) and `test_plan_admission.py` under `tests/kernel/`: the frozen corpus, its digest pinned by `test_the_corpus_is_frozen`
- [x] `PlanLimits.meet` property tests (idempotent, commutative, never widens, unbounded is identity)
- [x] `test_plan_admission.py` under `tests/runtime/`: refused never spawned; admitted then spawned; unregistered refused by name; a refused effect refuses the plan; Ask parks the plan as one question and Approve runs it (the write inside asked again at its step); child limits are the meet of the host's and the pattern's; refusal reaches the planner with every reason; run-after closes the planner's step first; amend is a resume — admitted, or refused with the parked run untouched
- [x] Verify RED: collection fails on the absent names (`ImportError: cannot import name 'PlanLimits'`) — 2026-09-18; each scenario fails for its stated reason as its group lands

## Group 1 — Kernel
- [x] `kernel/planning.py`: `PlanLimits` + `meet` + `narrower_than`; `PlanMeasure` + `measure()`; `leaves_of()`; `PlanMismatch`; `Admitted`; `PlanRefused`; `admit()`; `composition_digest()`
- [x] `kernel/events.py`: `PlanAdmitted`, `PlanRefused` in the `Event` union (eighteen kinds; the three kind-count tests updated)
- [x] `kernel/contracts.py` + `schemas/` + `clients/typescript/src/schemas`: four contracts registered with examples, republished, regenerated; `tsc --noEmit` green
- [x] Mutation check: depth check removed → 2 corpus cases fail; existence check removed → 2 fail; `meet` widened → 2 property tests fail; restored (a stale `.pyc` from a same-second, same-size edit had to be dropped)
- [x] Verify: `uv run pytest -q tests/kernel tests/wire/test_schemas.py tests/invariants` → 242 passed · `uv run mypy src/shadow_hdk/kernel` → clean · ruff clean — 2026-09-18

## Group 2 — Runtime: admission in spawn
- [x] `children.spawn` → `Children.admit()`: `admit()` for structure and existence, then each leaf's declared effects dry-judged in the child's own context (BUG-030) — **named** on `PlanAdmitted.asks` / `.refusals`, never pre-empted (D108/D121 amended, see history); `PlanNotAdmitted` raised after `plan_refused` is on the record; no `Spawned` on refusal
- [x] `RunOptions.plan_limits`; `Session.plan_limits`; `spawn_options` meets the parent's with the caller's; `Pattern.plan` met at admission
- [x] `AgentComponent.carry_out`: a refused plan is the tool result the model reads (D111); the `spawn` helper verb composes only what is offered and reports a refused delegation; the offer returns a refused one-call plan as the error the CLI always read
- [x] `Item.plan` on the fold — attached to the open or current step, never opening one; the OTel observer accounts for both kinds with safe metadata
- [x] Wire: `context.children.spawn` carries `limits`, `proposed_by`, `step`; `plan_refused` in `ERROR_KINDS`, named by the runtime side and re-raised as `PlanNotAdmitted` on the host side; the parity table names the four new `RunContext` seams
- [x] Mutation check: admission removed from `spawn` → 6 scenarios fail; restored
- [x] Verify: `uv run pytest -q -m 'not live'` → 1,731 passed, 3 deselected (G5's), 2 pre-existing README failures (BUG-054) · `uv run mypy` → 446 files clean · ruff clean — 2026-09-18

## Group 3 — Planning is a component
- [x] `runtime/planning.py::PlanComponents` (`compose`, `plan` label, empty profile, the `Composition` schema as input) on the `PersonComponents` precedent; held to `ComponentPortContract`
- [x] One path: the loop's `compose` meta-tool and the component both enter `children.spawn`; the loop treats the plan-labelled registration as its meta-tool and never shows it as a second tool — `single` stays unable to plan (tested); the offer gives a plan proposal the parent's remaining steps rather than a tool call's two
- [x] `serve`/`workshop` offers it beside `ask_person`; `Thread.tools()` lists it; a mode's `tools_offered` may withhold it
- [x] Live: **Codex CLI 0.154.0** — Claude Code was signed out on this machine (`loggedIn: false`, the owner's to fix); the first ready CLI proposed `fan_out(read_a, read_b)` through the socket, two admissions on the record, both `read_file` steps ran through our registry, the reply named both contents; 2 turns, 4 steps, 17.4 s, 57,471/324 tokens, unpriced. The Claude Code half of the measurement is owed
- [x] Verify: `uv run pytest -q tests/runtime tests/serve tests/invariants` green · `uv run pytest -m live tests/test_a_cli_plans_through_the_socket.py` → 1 passed · mutation (a refusal reported as success) bites — 2026-09-18

## Group 4 — Limits on the mode
- [x] `ModeSpec.plan`; `[plan]` in mode documents (`plan_limits_from`): malformed refused by name; an axis left out is the named policy's, never unbounded; a table wider than the policy it names is refused (`widens policy 'ask' — …`)
- [x] Shipped defaults `PLAN_OF`: read-only (3, 8, 64) = ask (3, 8, 64) < workspace-write (4, 16, 128) < full (4, 32, 256) — generous ceilings, the lease the floor; recorded in history
- [x] `widens_plan()` beside `widens()` (an unset axis is wider than any bound); `Conversation.plan_limits` = host's `meet` the current mode's, read at every turn and on settle; `set_mode` changes it live; `Thread.open/resume(plan_limits=)`. `modes/list` carrying the limits is G7's wire work
- [x] Mutations: the widening refusal removed → 1 fails; the turn ignoring the mode's limits → 2 fail; restored
- [x] Verify: `uv run pytest -q tests/adapters/modes` → 103 passed · full non-live 1,755 passed · mypy 450 files clean — 2026-09-18

## Group 5 — After the planner; amend
- [x] `Pattern.absorb`: with `False` the loop admits the plan and **defers** it (`Children.defer`); the step closes on the record, then `run_deferred` spawns it as the same run's child — the planner is told it is admitted, never its results
- [x] Amend is a resume: the checkpoint's new `plan` channel carries the composition (seeded in the initial state, written by every node); `resume` compares digests and admits a different plan as an amendment — `Composed` + `plan_admitted(amendment)`, or `plan_refused` with the parked run untouched. `runtime.parked_composition()` lets a settle resume on the shape it parked with (it used to rebuild a one-step plan)
- [x] `Amend(composition, answer)` is an answer kind: `Thread.amend` = `settle` with it; whoever holds the plan (`compose`, the loop's component) wakes the held child on the amended composition via `Children.amend`; refused, `compose` parks again on the same question and the record keeps it
- [x] `compose` parks honestly when a step inside its plan asks (D57): the question becomes the call's own, the handle kept, the answer sent into the held plan on resume — a settle reserves the thread's remaining budget, since the run below may hold many steps
- [x] Measured: the amended composition takes effect from the parked step (`w`, then the new `after`); a refused amendment re-parks with the question open; the mutations (no amendment admission → 4 fail; deferred never runs → 1 fails) bite
- [x] Verify: full non-live 1,761 passed (BUG-054's two deselected) · mypy 451 files clean · ruff clean — 2026-09-18

## Group 6 — ENH-020
- [x] JSONL/ACP openers report `unmapped` on the session (`AgentSession.unmapped`, default none; `unmapped_behaviour` moved to `kernel.providers` — an adapter may not import another); `Conversation.unmapped_behaviour` read off the session at every open, so `set_mode`'s reopen re-reads it; `Changed.unmapped`; `Thread.unmapped_behaviour` names it at open, resume and after `set_mode`
- [x] `thread/start`, `thread/resume`, `thread/set_mode` results carry `unmapped_behaviour`; `Started`/`setMode`/`addRoot` typed in the TypeScript client (`tsc --noEmit` green); the parity table excuses the property by naming where it crosses
- [x] ENH-020 closed in the backlog; `adapters-jsonl.md`, `providers.md`, `wire.md` updated
- [x] RED first: five tests failed on `'JsonlSession' object has no attribute 'unmapped'` / `'Thread' object has no attribute 'unmapped_behaviour'`; mutation (the JSONL opener stops reporting) → 1 fails; restored
- [x] Verify: `uv run pytest -q tests/adapters/jsonl tests/adapters/acp tests/wire tests/invariants tests/runtime tests/serve` → 899 passed, BUG-054's two the only failures; full non-live 1,766 passed (BUG-054's two deselected) · mypy 451 files clean · ruff clean — 2026-09-18

## Group 7 — Parity, docs, release
- [x] `thread/amend` (`admitted`, `mismatches`, `events`); plan events on the stream (the `Event` union is the contract — tested crossing); `ERROR_KINDS` += `plan_refused` (G2); `modes/list` rows carry `plan`; `thread/start` and `thread/resume` take `plan_limits` and return it, `thread/set_mode` returns it; the serve host reads the wire's words; schemas regenerated (no drift); TS client: `ModeRow`, `Amended`, `thread.amend`, `plan_limits` — `tsc` and build green; `tests/wire/test_a_plan_crosses_the_wire.py` (3); the parity tables: `Thread.amend` crossing, `Thread.plan_limits` excused by where it crosses. Protocol stays `3` (additive)
- [x] BUG-055 found by the amend wire test and closed: the executor drains LangGraph's replayed answers (`replays` on the park payload); `Thread.settle` keeps a question the run parks on again; `compose` re-keeps its whole record — two runtime scenarios + the wire one RED first; mutation (no draining) → 2 fail
- [x] Package guides (kernel, runtime, adapters-modes, wire, adapters-jsonl, providers), `consuming.md` (*a plan, end to end*), `docs/migrations/0.31.md`; `codex.toml`'s relay comment; BUG-054 closed — the README's Python and TypeScript snippets run as printed again. `/sync-docs` for the architecture docs: next, before `/complete-phase`
- [ ] The demo (`shadow-hdk-demo/react-app`) re-pinned to 0.31.0 from PyPI with a chapter from the live run — **after the publish**, as 0.29.1's was; cannot be true before it
- [x] Version 0.31.0, `EXPECTED` (with its docstring entry), `uv lock`, README release status + docs links, changelog, status row. The ecosystem board's H row + Pins + Log: the owner's word (that repository sits on another session's branch)
- [x] Verify: ruff check clean · ruff format clean · mypy 452 files clean · `uv run pytest -q -m 'not live'` (nothing deselected) → 1,771 passed, 14 skipped; one MCP process-lifetime test flaked under full load and passed alone and in the two earlier full runs · `npm run generate && npm run check && npm run build` green, schemas unchanged · `momentum okf check .` conformant (194 files) · the fresh-install smoke: the 0.31.0 wheel built, installed into a clean venv, imported, and answered `initialize` on protocol 3 — 2026-09-18
