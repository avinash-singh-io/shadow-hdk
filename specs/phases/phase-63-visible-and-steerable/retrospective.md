---
type: Retrospective
status: complete
---

# Phase 63 — the loop is visible and steerable — Retrospective

> Lane P's asks 8 and 9, and Epic 0011's last phase. v0.42.0.

## What was delivered

- **`update_plan` as a registered component with no effects at all** (D171): the agent's own
  narration, admitted by every mode including `read-only`. An agent that had to ask permission to
  say what it intends would stop saying it, and a narration nobody can afford is worse than none.
  The revisions reach the record through `Invoked.inputs` with nothing extra built — which is the
  real argument for a component over a runtime concept.
- **A status is an open string** (D172), the cut `Provider.transport` makes: a plan's vocabulary
  belongs to the product.
- **`steer` answers `True` for a key-backed model** (D173): queued and delivered as the person's
  words before the next model call, never into a request already in flight. `False` still where
  there is nothing to steer, and a one-shot dialect still `False`.

## What went well

- **The row asked for a decision and got one.** ENH-045 said *decide first whether this is a battery
  the kit ships or a shape it documents*; the answer — a component, because of the boundary rule and
  because an empty profile is what makes narration affordable — is recorded as D171 rather than
  implied by the code.
- **The steer test asserts what the model was actually asked**, not `steer`'s return value. Returning
  `True` is the easy half and the half that could be wrong alone.

## What did not

- **A refusal was tested at the wrong layer, and a mutation found it.** `steer` with no turn running
  was asked of the *thread*, and `Conversation.steer` short-circuits on "is a turn running" before it
  ever reaches the provider — so making `_ModelSession.steer` return `True` broke nothing. There is a
  session-level test now, and a second one for the thread's own reason to refuse. Fourth
  mutation-found weakness in this epic; the recurring lesson is that a test which cannot say *which*
  layer refused is not testing the layer its name claims.
- **One assertion is defensive rather than mutation-sensitive** and says so: that a steer does not
  appear in the request already sent cannot realistically be made to fail, because a sent request
  cannot be retroactively changed. Recorded rather than counted as evidence.

## Verification Evidence

Captured 2026-10-01 on `staging` with phase 63 merged (the release tree for **v0.42.0**), macOS 26
(Darwin 27.0.0), Python 3.14.6. `pytest`'s exit code read directly rather than through a pipe.

### `uv sync --all-packages --all-extras` (the build command)

```
 + shadow-hdk-linux-sandbox==0.42.0 (from file:///…/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
559 files already formatted
Success: no issues found in 496 source files
```

### `uv run pytest`

```
2021 passed, 20 skipped, 23 deselected, 85 warnings in 180.38s (0:03:00)
pytest exit=0
```

### Mutation checks — six, all biting

Four on the plan (an effect claimed so `read-only` would refuse it, revisions uncounted, a status
turned into an enumeration, a wordless step accepted) and two on the steer (steers never folded in,
and `steer` answering `True` with no turn running — the last needing the test moved to the session
layer before it would bite).

## The epic, closing

Epic 0011 entered at **1897** passing tests and leaves at **2021** — 124 added across Q1 and phases
59–63, with **63 mutations** verified to bite.

Two defects nobody had reported were opened and closed: **ENH-051** (a product's instructions never
reached Codex) and **BUG-229** (a key-backed model never received them *and* the thread reported them
honoured — the worse of the two, because the field exists to say what was not honoured and it lied).

Three things worth carrying to `shadow`:

1. **A green unit suite proves bytes reached a pipe.** Twice a live measurement found what no unit
   test could — Q1's premise, and phase 62's one-gate bug where fragments never reached Claude Code
   because every unit test used a dialect that folds.
2. **The mutation pass is not a formality.** Six of 63 found assertions that could not fail: a safety
   claim that was only a docstring, a guard whose deletion still passed, a test refused for the wrong
   reason, an ordering that passed by luck, and a refusal tested at the wrong layer.
3. **Two of the twelve asks were answers, not builds**, and establishing that before writing code was
   the single highest-value hour.

Asks 10 (credential injection) and 12 (Phase 54 triggers) remain unscheduled, each for a stated
reason rather than by omission.
