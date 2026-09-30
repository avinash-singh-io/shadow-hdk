---
type: Ad-hoc Record
---
# ENH-042 (in part) · ENH-048 — a change names a region, and a move is a move

> **Type**: quick-task
> **Created**: 2026-09-30
> **Branch**: feat/ENH-042-a-change-names-a-region
> **Backlog**: ENH-042 (the edit half), ENH-048
> **Status**: shipped — v0.36.0

Designed through `/brainstorm-phase` and then carried as a quick-task rather than a phase: phases
46–58 are `shadow`'s and the retired identities are not reassigned, so a phase here would have
minted a new identity in a repository whose own roadmap says start nothing here — for two
operations, no ADR and no kernel change. This repository exists now to remove the product's
bottleneck; the successor harness is `shadow`.

**Two premises were checked and found false during the brainstorm**, and both shrank the work:

- *"The record needs before/after capture before an edit can be legible."* It does not. `old` and
  `new` are the call's own inputs, and `Invoked.inputs` already puts them on the record while
  `ApprovalRequested.inputs` already puts them on the approval card (D80, BUG-026). A host sees
  what an edit would do **before** approving it, without reading the disk. ENH-044 remains open for
  *whole-file* writes and deletes, where the inputs do not say what was there before.
- *"`EffectProfile.reversible` is a claim with no mechanism behind it."* It is a lattice position
  for narrowing — `reversible True < False`, *irreversible is the wider effect* — read by
  `narrows()` to decide whether a mode admits an act. It claims a write can be written over and a
  delete cannot be undeleted. Both true. Nothing to mechanise, and no ADR.

## Current Behavior

`write_file` was the only way to change anything, so a governed agent rewrote a whole file to alter
one line: slow, expensive, and on a large file the model drops content it never meant to touch —
the file comes back shorter and nobody notices until later. And nothing moved a file: `grep -c
"rename\|move_file"` over `src/` returned **0**, so refactoring meant shelling out to `mv`, a `run`
effect — irreversible, wider than the act deserves, and one `ask` stops a person for.

## Expected Behavior

- `edit_file(path, edits[])` replaces regions in order, **all of them or none**.
- An `old` that is **absent** is refused: the model is working from a picture of the file that is
  out of date, and applying the rest of the batch would act on that picture.
- An `old` that appears **more than once** is refused, naming the count: it did not say which one
  it meant, and taking the first is how an agent edits the wrong line and reports success.
- Both refuse **before anything is written**, so a failed edit leaves the file that was there — the
  one state the model and the record already describe.
- `move_file(from, to)` refuses a destination that exists. That refusal is what keeps a move
  honestly `write`-class: nothing is destroyed, so it is reversible by moving back.
- **Refused is a decision; Failed is the world saying no.** The destination check and the match
  rules are decisions, so they refuse; a missing file is the filesystem's answer, so it fails —
  the vocabulary `read_file` already uses for the same cause.

## Unchanged Behavior

No kernel change: `Operation` is the same five literals and `effects_of` is untouched — both new
operations derive as `write`, so `read-only` withholds them before governance is asked and every
mode judges them exactly as it judges `write_file`. No new record machinery. No adapter must
implement anything: both are built on `_read`/`_write`/`_delete`, and `_move` is an *overridable*
hook with a base fallback (`LocalEnvironment` takes it, which makes the move atomic and lets it
carry bytes the text round-trip could not). The seven existing operations, protocol 3 and every
port are unchanged.

## Out of scope, deliberately

A cross-file patch and a background shell (the rest of ENH-042); before/after capture (ENH-044);
undo (ENH-043); and everything in the walk's items 6–10. Two gaps found while auditing and filed
rather than built: **ENH-049**, `Message.content` is text so nothing visual reaches a model — a
kernel change needing an ADR; **ENH-050**, no symbol navigation.

## Verification Evidence

RED first (Rule 13): `tests/adapters/environment/test_a_change_names_a_region.py` — **13 failed, 1
passed**. Green after: 14 passed. Two of those tests were rewritten during the red phase: they had
expected `Refused` for a missing file, which would have given `edit_file` a different vocabulary
from `read_file` for the same cause.

The gate is **CI**, run `36693323307` on `feat/ENH-042-a-change-names-a-region`, **green on the
first run, every job**:

```
macos · native (Landlock) · bubblewrap · check 3.12 · check 3.13 · check 3.14
wheels: x86_64/aarch64 × manylinux_2_17/musllinux_1_2 · sdist · installed
```

Locally: `ruff check` clean, `ruff format --check` clean over 534 files, `mypy` strict clean over
477 source files, `tests/adapters/environment` 113 passed.

**Stated honestly:** the local benchmark failed again during this work — 3.427 ms/step against a
3.0 ms budget — on a laptop at load average **26.9**. That is TD-015, not this change, which
touches only the environment component; CI's own run of the same code passed.
