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
| Head | `phase-18-the-p1s` — the top of the linear stack |
| Base | `staging` |
| Commits | 141 |
| Files | 508 changed |
| Phases | 0–18 (Phase 18 is groups 1–5 of 5) |
| Packages | kernel, runtime, wire, and 14 adapters, all `0.12.0`, all MIT |
| Tests | 837 passed, 1 skipped, 10 deselected |
| Types | mypy strict over 132 files |

**One pull request, not eighteen.** Each phase branched from the one before it, so the stack is
linear and every branch is an ancestor of this one. Opening it against `staging` rather than `main`
is the staging-first rule, and it means the first CI run in this repository's history happens
somewhere a failure costs nothing.

## The command

Run from the repository root, on a machine authenticated as the owner:

```bash
gh pr create --base staging --head phase-18-the-p1s \
  --title "Phases 0-18: the harness, and the audit's P0s and P1s" \
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
