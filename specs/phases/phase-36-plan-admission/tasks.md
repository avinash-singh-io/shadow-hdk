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
- [ ] `kernel/planning.py`: `PlanLimits` + `meet` + `narrower_than`; `PlanMismatch`; `Admitted`; `PlanRefused`; `admit()`; `composition_digest()`
- [ ] `kernel/events.py`: `PlanAdmitted`, `PlanRefused` in the `Event` union
- [ ] `kernel/contracts.py` + `schemas/`: exported, round-trip, API export invariant
- [ ] Mutation check on each corpus assertion (drop the depth check → the over-depth case must fail)
- [ ] Verify: `uv run pytest -q tests/kernel` · `uv run mypy src/shadow_hdk/kernel`

## Group 2 — Runtime: admission in spawn
- [ ] `children.spawn`: `admit()` → dry-judge each step → Refuse / Ask (one question) / Allow → `run()`; no `Spawned` on refusal
- [ ] `RunOptions.plan_limits`; effective limits on the context; a child receives the meet
- [ ] `AgentComponent.carry_out`: a refused plan becomes the tool result the model reads (D111)
- [ ] `Fold`: `plan_admitted` / `plan_refused` items
- [ ] Mutation check: remove the pre-compile check → the *never spawned* assertion fails
- [ ] Verify: `uv run pytest -q tests/runtime tests/adapters/agent`

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
