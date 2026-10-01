---
type: Retrospective
status: complete
---

# Phase 62 — what a run carries into any provider — Retrospective

> Lane P's asks 5 and 11, the remainder of ask 4, and the defect planning it found. v0.41.0.

## What was delivered

- **BUG-229 fixed.** A key-backed model never received a mode's `system` — `ModelSession` stored the
  behaviour and nothing read it — and `thread.unmapped_behaviour` came back **empty**, which a host
  reads as *honoured in full*. Instructions and fragments now reach the system message,
  `Behaviour.model` reaches `ModelRequest.model`, and `effort`/`temperature` are **named** because a
  `ModelRequest` has nowhere to put them (D170).
- **One vocabulary for everything a run carries** (D166): a named, attributable `Fragment`. Q1's bare
  `<instructions>` became one of them.
- **One assembler for both provider kinds** (D167), which is what makes "identically for a CLI and a
  key-backed model" — lane P's words — a property rather than an intention.
- **A mode's words layer on the pattern's role** (D168), never replacing it: the pattern carries the
  loop's mechanics.
- **`root_instructions`** (D169, ENH-047): a root's `AGENTS.md`/`CLAUDE.md` as fragments a product
  composes. The ENH-012 default stays.
- **`markdown_skills`** (ask 11): a folder of `SKILL.md` as a `SkillSource`.

## What went well

- **Planning found the defect, before any code.** Lane P wrote *"a key-backed model takes
  instructions and skills directly"*; checking that sentence against the code is what turned up
  BUG-229. Reading the claim rather than accepting it was the highest-value hour of the phase.
- **The sentinel was re-measured rather than inferred**, on the version lane P actually ships.
- Not a YAML parser, deliberately — the same trade D158 refused for the patch format.

## What did not

- **A live measurement found a bug fourteen unit tests missed.** `instructions_in_prompt` and
  *carries fragments* were written as **one gate**, so Claude Code — which has `--system-prompt`, and
  therefore does not fold — received **no fragments at all**. Every unit test passed because every one
  used a dialect that folds. The sentinel measurement caught it: the model answered by summarising
  its own system prompt with the offered fragment nowhere in it. Two gates now, plus a test for a CLI
  that *has* the flag. Second time this epic that only a live run found the thing.
- The migration note's fenced Python failed `ruff format --check` at the landing gate again —
  third occurrence, now filed as **TD-017** rather than fixed a fourth time in silence.

## Verification Evidence

Captured 2026-10-01 on `staging` with phase 62 merged (the release tree for **v0.41.0**), macOS 26
(Darwin 27.0.0), Python 3.14.6. `pytest`'s exit code read directly rather than through a pipe.

### `uv sync --all-packages --all-extras` (the build command)

```
 + shadow-hdk-linux-sandbox==0.41.0 (from file:///…/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
556 files already formatted
Success: no issues found in 494 source files
```

### `uv run pytest`

```
2011 passed, 20 skipped, 23 deselected, 85 warnings in 173.92s (0:02:53)
pytest exit=0
```

Phase 61 left it at 1986; this phase adds 25. An earlier run of this gate reported **1 failed** — the
TD-017 backlog row named a migration note that arrives with a later release, and the document
invariant refuses a path a document names that is not in the tree. Reworded; the run above is the
clean one.

Then this retrospective made the identical mistake one paragraph later, by quoting that path while
describing the fix — and because it was written *after* the gate ran and never re-gated, nothing
caught it locally. CI did, on every job, at the v0.41.0 tag. The note is named without its path
here, and the lesson is in TD-017: a document is part of the tree the gate checks, so writing one
after the gate means the gate has not run.

### Mutation checks — nineteen, all biting

Six in G1/G2 (the behaviour not reaching the loop, the mode replacing the pattern's role, a fragment
losing its name and source, the mode's model ignored, `unmapped` emptied again — the lie itself — and
`unmapped` made a blanket claim) and seven across G3/G4 (attribution dropped, a large file dropped
rather than truncated, an unreadable file made fatal, an empty file becoming a fragment, a nameless
`SKILL.md` not taking its directory's name, one malformed skill taking the others down, a body-less
skill accepted).

### Live measurement — the sentinel, on the version lane P ships

```
uv run pytest tests/test_the_sentinel_on_the_shipped_cli.py -m live -q -s
[measured] the sentinel default, claude-code 2.1.284
[measured] the offered fragment, claude-code 2.1.284
2 passed in 26.49s
```

Measured against **claude-code 2.1.284**, not inferred from the 2.1.235 measurement of 2026-09-12
(BUG-031 is the precedent). A sentinel `CLAUDE.md` is still **not read** by a governed Claude Code,
and the same convention passed as a `Fragment` **is** followed. The pair matters: without the
positive, the negative would also pass if the model simply never answered the question.
