---
type: Tasks
---

# Phase 60 — tasks

## G1 — a patch applies across files, or not at all

- [x] RED: `apply_patch` does not exist (8 tests, all red)
- [x] the validation extracted as `edited_by`, shared by `edit_file` and `apply_patch` (D158)
- [x] read all, validate all, write all (D159)
- [x] a `change` per file, the same block 0.38.0 put on a write
- [x] the same path twice, an empty batch, a missing file — each refused by name
- [x] withheld in `read-only` before governance is asked
- [x] mutation-checked: 4 mutations bite

## G2 — a background job starts, reports and is killed

- [x] RED: `run_background` does not exist (10 red, 1 pass — the `_alive` helper's own check)
- [x] `run_background`, `job_output`, `kill_job` (D160: status and output together)
- [x] output is new-since-last-read; `exit_code` null while running
- [x] a job nobody started is refused by name
- [x] mutation-checked: 5 mutations bite

## G3 — no job outlives the environment that owns it (D157)

- [x] `Environment.close()` ends every job; `_Job.end()` ends the whole group
- [x] measured against the OS, not the kit's bookkeeping — `os.kill(pid, 0)`
- [x] the grandchild of a shell goes too (`npm run dev` is a shell *and* a node)
- [x] **a gap a mutation found**: the sandbox wrap and the narrow environment were untested.
      Two tests added; both fail when either is removed
- [x] mutation-checked: 2 more mutations bite

## G4 — close out

- [x] `docs/migrations/0.39.md`
- [x] 0.39.0, the Linux helper in lockstep
- [x] full gate: ruff clean, format 544 files, mypy 485 files, **1957 passed** / 20 skipped
- [x] `specs/status.md` own row; ENH-042 closed in the backlog
