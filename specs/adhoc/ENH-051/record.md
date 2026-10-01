---
type: Ad-hoc Record
---

# Ad-hoc Work Record: ENH-051

> **Type**: quick-task
> **Created**: 2026-10-01
> **Branch**: `docs/epic-0011-plan` (Epic 0011 Q1, ahead of phase 59)
> **Backlog**: ENH-051
> **Status**: shipped

Epic 0011's Q1 — the one part of lane P's ask 4 that was a capability gap rather than an answer.
Carried as a quick-task under Rule 14 because it is bounded to the dialect layer: no architecture
file moves, no ADR is needed, and no public contract changes shape.

## Current Behavior

`codex exec` maps no flag for `system`, `append_system` or `temperature`
(`providers/library/codex.toml`). `_behaviour_flags` therefore emitted nothing for them, and
`unmapped_behaviour` named them on `thread.unmapped_behaviour` — reported over the wire
(`wire/threads.py:424`) and honest, never silent, which is exactly what ENH-020 built it to be.

But naming is not delivering. **A product's instructions reached Claude Code and not Codex.** Lane
P's Build agent, Reviewer, Test fixer and Release writer all carry a role in a mode's `Behaviour`,
so on Codex every one of them had been running with no role at all — and the kit said so in a field
nobody was reading.

Found while planning Epic 0011, not reported: lane P asked *"What does `Behaviour` cover today, and
what is missing?"* and the answer turned out to be worse than the question assumed.

## Expected Behavior

The other half of D64. A dialect that maps no flag for instructions can still be handed them **in
the turn**, because whether that is true of a CLI is a fact about that CLI — so it is a field on its
record, not a branch above it.

- `Dialect.instructions_in_prompt: bool = False` — false by default, the conservative default this
  record keeps everywhere else. A CLI nobody measured is not handed a prompt shape somebody guessed.
- `kernel.providers.instructions_for_prompt(provider, behaviour)` — one pure derivation, beside
  `unmapped_behaviour` because the two answer the same question from opposite ends. Returns
  `<instructions>…</instructions>` or `""`.
- **Framed, not prefixed.** An unmarked prefix reads to a model as the person talking, which is how
  a mode's instructions get argued with instead of followed.
- **First turn only.** A resident CLI keeps them in its own memory; a non-resident one gets them
  back through its resume. Repeating them every turn would be paid for on every turn.
- **Never folded for a field the dialect maps a flag for.** A role sent twice is billed twice.
- `unmapped_behaviour` stops naming what is now delivered. `temperature` is still named: a turn's
  text cannot set a sampling parameter, and saying otherwise would be the lie this field exists to
  avoid.
- `codex.toml` sets `instructions_in_prompt = true`.

## Unchanged Behavior

- **Claude Code is untouched.** It maps `--system-prompt`, so `instructions_in_prompt` stays false
  for it and a test pins that. Its `unmapped` was already empty and still is.
- **A prompt with nothing owed is byte-for-byte what it always was** — asserted, not assumed.
- **No contract shape changes.** `Dialect` gains a defaulted bool, so every existing provider file
  parses unchanged; the parser reads `Dialect`'s fields reflectively and needed no edit.
- Protocol 3 unchanged. No new door, event, port or step kind. No kernel *event* field, so no ADR.
- `unmapped_behaviour` still names everything genuinely unhonourable — the paired negative test
  exists so that emptying the field would fail.

## Verification Evidence

Fresh in this session, 2026-10-01.

**RED first (Rule 13).** The test file was written before the code and failed for the stated reason:

```
TypeError: Dialect.__init__() got an unexpected keyword argument 'instructions_in_prompt'
```

**The full gate** (`pytest` exit code read directly, not through a pipe):

```
$ uv run ruff check           →  All checks passed!
$ uv run ruff format --check   →  538 files already formatted
$ uv run mypy                  →  Success: no issues found in 480 source files
$ uv run pytest -q             →  1911 passed, 20 skipped, 21 deselected in 167.47s   (exit 0)
```

Baseline before this work was **1897 passed**; +14 is the 13 new unit tests plus the paired negative
added to `test_unmapped_behaviour_is_named.py`. Deselected rose 17 → 21: the four new live tests.

**Mutation checks — all six bite** (project-rules: an assertion that cannot fail is deleted):

| Mutation | Test that failed |
|---|---|
| drop the `instructions_in_prompt` guard | `test_a_dialect_that_has_not_said_so_folds_nothing` |
| drop the mapped-by-flag skip | `test_a_cli_with_its_own_flag_is_not_told_twice` |
| never spend the owed instructions | `test_only_the_first_turn_carries_them` |
| keep naming delivered fields unmapped | `test_what_the_prompt_delivers_is_no_longer_named_unmapped` |
| claim a prompt can carry `temperature` | `test_temperature_stays_unmapped_because_a_prompt_cannot_carry_it` |
| prefix unmarked instead of framing | `test_the_instructions_are_framed_rather_than_prefixed_unmarked` |

**Live, against a real model** — because a green unit suite proves bytes reached a pipe, not that a
model read them:

```
$ uv run pytest tests/test_instructions_reach_a_live_model.py -m live -q
2 passed, 2 skipped in 15.43s
```

- **Passed:** Claude Code **2.1.284**, with `--system-prompt` removed from its record so the fold is
  the only way in. A real model obeyed a sentinel instruction it was handed in the turn. Its
  negative — same CLI, no instructions — passed too, so the positive is not vacuous.
- **Skipped, and this is the honest gap:** both Codex legs. `codex-cli 0.154.0` is logged in via
  ChatGPT on this laptop, but the account cannot use any model tried — `gpt-6.1-sol` (its own
  configured default), `gpt-5-codex`, `gpt-5`, `gpt-5.1-codex-max` and `o3` each answered *The
  '…' model is not supported when using Codex with a ChatGPT account*. The turn never reached a
  model, so nothing about the fold was measured there. The tests skip on that string rather than
  passing vacuously.

**What is therefore still unproven:** that the shipped `codex.toml` delivers end to end on a Codex
account that can run a model. The mechanism is proven live on another CLI and the argv is unit
tested, but the Codex lane itself is unmeasured here. Lane P can close that gap in one turn on their
own account, and the two skipped tests are the exact measurement to run.

## Also fixed while here

- Adding a `Dialect` field changed the published `Provider` contract, so `schemas/Provider.json` and
  `clients/typescript/src/schemas/Provider.ts` were regenerated (`test_schemas.py` caught it, which
  is what it is for).
- Two existing tests asserted the old behaviour and were updated rather than worked around, each
  gaining the paired negative that keeps the new assertion honest.
- Stale `__pycache__` from the workspace relocation was making tracebacks point at a path that no
  longer exists (`/Users/avinash/Workspace/Projects/shadow-hdk`); cleared.
