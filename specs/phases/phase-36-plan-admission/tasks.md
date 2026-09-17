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
- [ ] `runtime/planning.py::PlanComponents` (`compose`, empty profile) on the `PersonComponents` precedent
- [ ] `AgentComponent.compose` routes through the component path; `Thread.tools()` lists `compose`
- [ ] `serve`/`workshop` offers it; a mode's `tools_offered` may withhold it
- [ ] Live: one turn on Claude Code — the CLI plans through the socket; admitted inside the limits, refused with the list outside (≤ 2 turns; spend recorded in history)
- [ ] Verify: `uv run pytest -q tests/runtime tests/serve` · `uv run pytest -m live -k plan -rs`

## Group 4 — Limits on the mode
- [ ] `ModeSpec.plan`; `[plan]` in mode documents; malformed refused by name
- [ ] Shipped defaults on the four modes, with RED tests; recorded in history
- [ ] `widens()` extended; `ModeRegistry.find` hands the run its effective limits; `modes/list` carries them
- [ ] Verify: `uv run pytest -q tests/adapters/modes tests/serve`

## Group 5 — After the planner; amend
- [ ] `Pattern.absorb`; with `False` the planner's turn ends first and the child runs on as a held run
- [ ] `Thread.amend(handle, composition)`: admitted like the original; the held child takes it at its next boundary; `Composed` + the plan event; refusal leaves the plan untouched
- [ ] The boundary actually measured and recorded; any limitation filed as a backlog row
- [ ] Verify: `uv run pytest -q tests/runtime`

## Group 6 — ENH-020
- [ ] JSONL/ACP openers report `unmapped`; `Conversation` reads it at open and reopen; `Thread.open/resume/set_mode` surface it
- [ ] Wire results carry `unmapped_behaviour`; TypeScript generated
- [ ] ENH-020 closed in the backlog; `adapters-jsonl.md`, `providers.md` updated
- [ ] Verify: `uv run pytest -q tests/adapters/jsonl tests/runtime tests/wire`

## Group 7 — Parity, docs, release
- [ ] `thread/amend`; plan events on the stream; `ERROR_KINDS` += `plan_refused`; `modes/list` limits; `thread/start` takes plan limits; schemas regenerated; TS client generated; `tests/wire` parity
- [ ] Package guides, `consuming.md`, `0.31.md` under `docs/migrations/`; `/sync-docs` for the architecture docs
- [ ] The example re-pinned to 0.31.0 with a chapter written from the live run
- [ ] Version 0.31.0, `EXPECTED`, `uv lock`, changelog, status row, the board's H row + Pins + Log
- [ ] Verify: `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest -q -m 'not live'` · `cd clients/typescript && npm run generate && npm run check && npm run build` · `momentum okf check .` · the fresh-install smoke
