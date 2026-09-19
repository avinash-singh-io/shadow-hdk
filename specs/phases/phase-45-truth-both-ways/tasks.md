---
type: Tasks
status: in-progress
---
# Phase 45 — truth both ways — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12). Every group opens RED and no task is marked `[x]`
> without a recorded red→green (Rule 13, strict). Live measurements are recorded, never assumed.

## Group 1 — What a turn really cost (ENH-023, D141)
- [x] RED — 2026-09-20: 12 tests failed on the absent `Usage.cache_read_tokens`, `Spent.cache_read_tokens` and `Dialect.cache_read_tokens_at` (5 + 3 + 2 + 2 by reason)
- [x] `Usage.cache_read_tokens`/`cache_write_tokens`; `Spent.cache_read_tokens`/`cache_write_tokens`; `Dialect.cache_read_tokens_at`/`cache_write_tokens_at`; the JSONL session; LangChain; the meter's count/spent/restore; the two provider files with the measured lines; schemas and TS regenerated; the package docs
- [x] Verify — 2026-09-20: 12 green; `tests/kernel tests/runtime tests/adapters/jsonl tests/adapters/langchain tests/wire tests/invariants tests/providers` 971 passed; mypy 464 files clean; ruff clean; schemas republished (Event, Item, ModelResponse, Provider) and the TS types regenerated without drift; mutation — the meter not counting the cache → 2 fail

## Group 2 — Why a turn really failed (ENH-024, D139; BUG-059)
- [x] RED — 2026-09-20: 7 failed on the absent `Turn.session_gone`, `Dialect.session_gone_matches`, the absent kind, and the flood test **timing out at 60 s** — BUG-059 reproduced before it was fixed; the runtime file could not import `SessionGone`
- [x] `Turn.session_gone`; `Dialect.session_gone_matches` (+ `failed_text_at = "errors"` on Claude Code); the stderr reader; `TurnRecord.failure`; the conversation and thread; `SessionGone`; `error_data`, `ERROR_KINDS`, `_turn_json`; the TS client; BUG-059 filed and closed
- [x] Verify — 2026-09-20: 10 green; `tests/adapters/jsonl tests/runtime tests/wire tests/serve tests/invariants tests/providers tests/kernel` 1,023 passed; mypy 467 files; ruff clean; schemas and TS regenerated, the client type-checks and builds; mutations — matches ignored → 2 fail; `failure` unwritten → 2 fail. BUG-060 found on the way (a provider's failed turn recorded `completed`) and closed with it

## Group 3 — A host's words per turn; a second CLI's behaviour (ENH-037, D140; ENH-028)
- [ ] RED: the turn's words on that turn's judgements only; a rule scoped by them; reserved names; `resume(attributes=)`; the wire's two parameters; Codex argv with `-m` and `-c model_reasoning_effort="…"`; `unmapped_behaviour` shrinks; a malformed template
- [ ] `BehaviourArg.template`; `argv_for`; the loader; `codex.toml`; `Conversation.turn(attributes=)`; `Thread.turn/resume(attributes=)`; the wire; the TS client
- [ ] Verify: green; mutations — words leaking to the next turn → 1 fails; template unrendered → 1 fails

## Group 4 — The ceiling stands (ENH-038, D138); the matrix (ENH-032); a provider is a file, by a test
- [ ] RED: an uncontained reach refused under shipped `read-only` and `workspace-write`, asked under a product mode; the invariant catches a planted vendor name
- [ ] `_looking` ceiling `contained=True`; the modes guide's section; `ci.yml` matrix 3.12/3.13/3.14; `.python-version` 3.14; classifiers; the invariant
- [ ] Verify: green; the invariant's mutation; CI green on the three legs for the pushed commit — run URL: _(…)_

## Group 5 — The live proofs, the docs, the release
- [ ] Live: Phase 36's proof on Claude Code; Codex with `model`/`effort` measured; cache tokens on both CLIs measured — recorded in `history.md` (a skip recorded as a skip)
- [ ] Docs: the 0.34 note under `docs/migrations/`; `docs/for-a-product.md` (two ports one surface; §2, §8, §9; per-turn words); `docs/packages/adapters-langchain.md` (endpoints, local desktop); `docs/packages/wire.md`; the TS README
- [ ] Backlog rows closed; BUG-059; `specs/decisions/index.md` D138–D141; `[ARCH_CHANGE]` entries
- [ ] Version 0.34.0, `EXPECTED`, `uv lock`, changelog, status row
- [ ] Verify: the four-zero gate on 3.12 and 3.14; the TS gate; `momentum okf check .`; the wheel fresh; CI green; `/complete-phase` → STOP at the gate
