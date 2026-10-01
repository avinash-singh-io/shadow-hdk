---
type: Tasks
---

# Phase 61 — tasks

## G1 — the port, and a git adapter that leaves git alone

- [x] RED: no `history` module (collection error)
- [x] `WorkspaceHistoryPort` + `Snapshot` in the kernel, refuse-not-crash (D161)
- [x] `GitHistory`: scratch index → write-tree → commit-tree → `refs/shadow-hdk/snapshots/*` (D165)
- [x] restore puts content back, removes files created since, brings back files deleted since
- [x] ignored files neither deleted nor resurrected (D164)
- [x] **found by a test**: snapshot ids must sort — commit dates are second-resolution and two
      checkpoints in one second tie
- [x] mutation-checked: 7 bite (2 needed the assertion tightened first)

## G2 — `checkpoint` and `restore` as acts the mode judges

- [x] RED: the three operations do not exist (8 red)
- [x] `checkpoint` (`write`), `restore` (`delete`, irreversible — D163), `list_checkpoints` (`list`)
- [x] the host reaches `environment.history` directly for its own checkpoints (D162)
- [x] a bad snapshot is `Refused`, not `Failed`
- [x] mutation-checked: 6 bite (1 needed the read-only test to use a real snapshot)

## G3 — a worktree per agent, host-side

- [x] `open_worktree` / `close_worktree` / `worktrees`, branches under `shadow-hdk/`
- [x] two agents, two independent checkouts, neither leaking into the other or into the developer's
- [x] the branch outlives the directory, because the work is the point
- [x] a developer's own worktree is not listed and cannot be swept up
- [x] a linked worktree's `.git` is a *file*, so the history attaches there too
- [x] mutation-checked: 5 bite

## G4 — close out

- [x] `docs/migrations/0.40.md`
- [x] 0.40.0, the Linux helper in lockstep
- [x] schemas and the TS client regenerated — **no drift**: the port is a Protocol, not a published
      contract
- [x] full gate: ruff clean, format 550 files, mypy 490 files, **1986 passed** / 20 skipped
- [x] `specs/status.md` own row; ENH-043 closed
