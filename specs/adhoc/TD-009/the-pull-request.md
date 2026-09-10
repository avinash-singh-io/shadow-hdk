---
type: Adhoc
---

# TD-009 — the pull request, prepared and not opened

CI triggers on `push` to `main` and `staging` and on `pull_request`. Nothing has ever landed on
either branch, and no pull request has ever been opened — so **CI has never run on a single commit
of this stack**. Every "four zeros" in every commit message of every phase is this machine's word
and nothing else's.

Two halves. The first is committed: the workflow now triggers on **every** push, plus
`workflow_dispatch`, so the next push to any phase branch is the first time this repository has
been checked by anything but the laptop it was written on.

The second is the owner's, and this file is what it needs.

## Why this is not mine to run

`specs/project-rules.md` and this lane's standing instruction both say the same thing: **never open
a pull request without the owner**. A pull request is an outward-facing act on a repository the
owner owns — it names them as the author, it can notify a team, and on a repository with rules
attached it can start a merge. Preparing one costs nothing and is reversible; opening one is
neither.

So the command is written out below, ready, and deliberately not run.

## What it would open

| | |
|---|---|
| Head | `phase-19-the-p2s` — the top of the linear stack |
| Base | `main` |
| Commits | 162 |
| Files | 528 changed |
| Phases | 0–19 |
| Packages | kernel, runtime, wire, and 14 adapters, all `0.13.0`, all MIT |
| Tests | 946 passed, 1 skipped, 10 deselected |
| Types | mypy strict over 133 files |

**Two corrections to this record, made 2026-09-10 and worth stating rather than quietly editing.**

It named `phase-18-the-p1s` as the head. Phase 19 came after it, so the command would have opened a
pull request that left the last twenty-one commits out.

And it named **`staging` as the base, which does not exist.** This lane worked under a rule never to
push to `staging` or `main`, and never checked that the first of those was a branch. `git ls-remote
--heads origin staging` returns nothing. The command would have failed outright.

**The base is `main`, and no merge commit is needed.** Verified: `git merge-base --is-ancestor
origin/main origin/phase-19-the-p2s` succeeds, so `main` is a strict ancestor — 162 commits behind
and none of its own. It fast-forwards.

**One pull request, not twenty.** Every phase branched from the one before, and all twenty-one
branches were checked to be ancestors of this one, so there is nothing to land separately.

## The command

Run from the repository root, on a machine authenticated as the owner. **Or skip the pull request
entirely** — `main` fast-forwards, so `git push origin phase-19-the-p2s:main` lands the stack with
no merge commit and no review ceremony. The pull request is worth opening only if you want the
diff in one readable place or a second pair of eyes; the merge itself needs neither.

```bash
gh pr create --base main --head phase-19-the-p2s \
  --title "Phases 0-19: the harness, and everything the audit found" \
  --body-file specs/adhoc/TD-009/pull-request-body.md
```

## What to expect from the first run

It has never run, so treat a red as information rather than a regression. Three things are more
likely to differ on `ubuntu-latest` than anything in the code:

* **The coverage floor.** `--cov-fail-under=90` on `shadow_hdk.runtime` has never been measured
  anywhere but here, where the same command passes.
* **The platform skips.** One test skips on macOS with its reason recorded (`memory_mb`, which
  `prlimit` enforces on Linux and not here). On Linux it will **run** for the first time — that is
  the point of it, and it is the one test most likely to find something.
* **The live marks.** Ten tests are deselected by `-m 'not live'` and stay that way; they need a
  broker, a server or a paid turn, and none of those belong in CI.

Phase 11's gVisor and Firecracker proofs are still `[~]`: they need a Linux host with those
runtimes installed, which `ubuntu-latest` is not.
