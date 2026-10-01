---
type: Retrospective
status: complete
---

# Phase 60 — the write-class toolset completes — Retrospective

> The rest of ENH-042, both halves lane P confirmed cost them. v0.39.0.

## What was delivered

- **`apply_patch(files[])`** (D158, D159): regions changed across many files as **one** act. Read
  all, validate all, write all — so a refused patch leaves every file byte-for-byte as it was. Its
  vocabulary is `edit_file`'s `{old, new}` and literally its validation function, extracted as
  `edited_by`: a diff format would be a parser, and a parser is a phase. The same path named twice
  is refused rather than applied twice.
- **A background shell in three operations, not four** (D160): `run_background`, `job_output` —
  status and new-since-last-read output together — and `kill_job`, which ends the whole tree.
- **The environment owns a job** (D157): `close()` ends every one. D35 says a step owns the tree it
  starts, and a job outlives its step by definition; what carries over is that nothing outlives its
  owner, one level up — the move BUG-019 forced for provider sessions.

## What went well

- **The patch reuses the edit's refusals rather than restating them.** Extracting `edited_by` means
  a caller who has learnt what an absent `old` means for one file does not learn it again for many,
  and the two cannot drift.
- **Atomicity is measured from the filesystem**, not trusted from the refusal: a patch refused on
  its last file is checked by reading the earlier files back.
- **No test sleeps for a fixed number of seconds.** TD-015 closed four flakes of that shape, and a
  background-job test is the easiest place in the codebase to reintroduce them; every wait goes
  through one `until()` helper that polls a condition to a deadline.
- The `_alive` helper has its own test — a SIGKILLed process must read as dead — because if it could
  never say no, every ownership assertion in the file would pass for the wrong reason.

## What did not

- **A safety claim was a docstring and nothing more, and a mutation found it.** `_start_job` said a
  background job goes through the same sandbox as a foreground command "because a job that escaped
  confinement by being long-lived would be a hole a mode never admitted" — and **removing the wrap
  entirely broke no test.** The same was true of the narrow environment: handing a job the whole
  ambient environment also broke nothing. Two tests added; both fail when their line is removed.
  The lesson is that prose beside code is not evidence.
- One mutation pass needed retrying because the `-k` filter selected tests for which the mutated
  branch was dead code.

## Verification Evidence

Captured 2026-10-01 on `staging` with phase 60 merged (the release tree for **v0.39.0**), macOS 26
(Darwin 27.0.0), Python 3.14.6. `pytest`'s exit code read directly rather than through a pipe.

### `uv sync --all-packages --all-extras` (the build command)

```
 - shadow-hdk-linux-sandbox==0.38.0 (from file:///…/native/sandbox)
 + shadow-hdk-linux-sandbox==0.39.0 (from file:///…/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
545 files already formatted
Success: no issues found in 485 source files
```

### `uv run pytest`

```
1957 passed, 20 skipped, 21 deselected, 85 warnings in 180.35s (0:03:00)
pytest exit=0
```

Phase 59 left it at 1936; this phase adds 21.

### Mutation checks — eleven, all biting

Four in G1 (write-as-you-go, the duplicate path, the empty patch, read-only), five in G2 (close
ending nothing, close ending only the last, killing the child not the group, re-reporting read
output, reporting `exit_code` 0 while running) and **two in G3 that found the untested confinement
claims** described above.

### What is not covered here

The Linux confinement leg runs on CI, not on this machine — `bubblewrap` and Landlock are exercised
by the `ci` workflow on `ubuntu-24.04`, and the background job's sandbox wrap is asserted through a
recording box rather than against a real sandbox locally. The claim proven locally is that the wrap
is *applied*; that it *confines* is Phase 41's proof, unchanged by this phase.
