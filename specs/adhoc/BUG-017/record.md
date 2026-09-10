---
type: Ad-hoc Record
---

# Ad-hoc Work Record: BUG-017

> **Type**: quick-task
> **Created**: 2026-09-11
> **Branch**: `fix/BUG-017-and-the-front-door`
> **Backlog**: BUG-017, and ENH-004 filed along the way
> **Status**: shipped

Two things, found the same way: by using the library from outside its own test suite.

## Current Behavior

**The listener printed a traceback on a clean exit.** `served_over_http` cancelled uvicorn
mid-`serve`, which left uvicorn's own tasks to be torn down by force; one of them surfaced the
cancellation as an unretrieved exception, and the loop printed the whole `CancelledError` at
teardown. Harmless, and the first thing anybody driving the wire sees — which is the problem: a
traceback on a clean exit teaches a reader to ignore tracebacks.

Every wire test missed it. Pytest's anyio runner owns the loop and absorbs an unretrieved
exception, so the leak is visible only to a program that calls `asyncio.run` itself — which is to
say, to every program that is not a test.

**The README described a different project.** It announced Phase 0, 150 tests, version 0.1.0, "Phase
1 next", and "private and unlicensed" — one day after seventeen distributions were released at
0.13.0 under MIT. It also mentioned an adopter by name, which the owner ruled out of this
repository's documents on 2026-09-10.

**Three tables in `specs/status.md` were stale in the same way**: every phase row said *Complete,
unmerged* with an empty release column after all twenty had merged and thirteen releases existed;
the Active Phase table listed seventeen finished lanes as if they were in flight; and the Upcoming
Phases table said *Not Started* for phases 4 through 9, which shipped.

## Expected Behavior

The listener asks uvicorn to stop, waits for `serve` to return, and only then cancels as a
backstop. The README describes this tree. `status.md` says what is true, and what is left says what
it is waiting for rather than sitting as an undated intention.

## Unchanged Behavior

The wire's own behaviour: 66 wire tests pass unchanged. The five-second cap on the wait stays, and
the cancel scope stays as the backstop for a shutdown that never finishes — a fix that waited
forever would trade a cosmetic problem for a hang.

The historical records are not rewritten. Each group gate in
`specs/phases/phase-19-the-p2s/tasks.md` recorded what it actually ran, and the changelog is
append-only; the correction is a new line, not an edit to an old one.

## Verification Evidence

Fresh, 2026-09-11, this session.

**The bug reproduced first (RED), with the fix removed:**

```
FAILED tests/wire/test_the_listener_leaves_quietly.py::test_the_listener_shuts_down_without_printing_a_traceback
FAILED tests/wire/test_the_listener_leaves_quietly.py::test_the_port_is_let_go
2 failed, 1 passed
```

The failure text is a real `Traceback` out of starlette's lifespan receive being cancelled — the
stated reason, not a coincidental red.

**The first fix passed for the wrong reason and was replaced.** It waited on `server.started`,
which uvicorn sets once at line 196 of `server.py` and never clears, so the loop was a five-second
sleep that happened to outlast the shutdown: 26.3 s for three tests. Waiting on `serve` returning
instead: **5.8 s**, same three tests green.

**Mutations, both bite:**

| Mutation | Result |
|---|---|
| never wait for it to finish (`should_exit` alone) | 2 failed |
| never ask it to stop (wait alone) | 2 failed |

`test_the_process_exits_zero` passes under both mutations *and* under the original bug, and is kept
deliberately: an unretrieved exception does not fail a process, so the exit code is a separate
claim, and a fix that quietened the loop by swallowing a real shutdown failure would still have to
answer it.

**The README's example was run as written and was wrong three times** — `CallableComponents` takes
no mapping, `Invoke` takes bindings rather than an `inputs=` mapping, and `Ceiling`'s fields are
`max_steps`/`max_wall_seconds`/`max_cost_cents`. The published version is the one that produced:

```
started
composed
invoked say-hello
observed say-hello
ended
```

Running it also surfaced **ENH-004**: `Ports.model` is typed as required, so the simplest possible
composition — no model at all — runs but does not type-check. Filed rather than fixed, because
making it optional is a contract change and D9 moves every package together.

**The invariant now covers the README**, which is the part that stops this recurring. It checks
seven paths there today, and a deliberately dead path fails it:

```
E           README.md: specs/architecture/does-not-exist.md
1 failed, 5 passed
```

**Gate, all four zero:**

```
ruff check      0
ruff format     0
mypy            0    Success: no issues found in 147 source files
pytest          0    949 passed, 1 skipped, 10 deselected in 61.08s
```

**A carried-forward number corrected.** *mypy strict over 133 files* was Group 1's gate; the phase's
closing records, the release notes and the prepared pull request all repeated it rather than
re-measuring after four more groups landed. Measured at the phase-19 tree with this change's one new
test removed: **146**. With it: **147**.

## Release

**v0.13.1**, 2026-09-11, on the owner's word. Seventeen distributions 0.13.0 → 0.13.1 with the
sixteen intra-workspace pins, because equality is what *every package moves together* means.

**A patch, not a minor.** No contract changed, so there is no *Pins* row on the ecosystem board.
`tests/test_versions.py` records the reason beside every previous bump — until now every entry was
a minor and said what a host would have to change; this is the first that says nobody has to change
anything. Its module docstring also said *the four are one thing released four ways*, true at
Phase 0 and wrong since Phase 1 added adapters; it says seventeen now.

**The gate caught the bump.** `test_every_package_is_at_the_same_version` failed on the first pass
because `EXPECTED` still read `0.13.0` — the single place that has to be edited deliberately, which
is the point of it.

Wheels built and read back:

```
shadow-hdk-kernel | 0.13.1 | License-Expression: MIT | LICENSE file: True
shadow-hdk-wire   | 0.13.1 | License-Expression: MIT | LICENSE file: True
   Requires-Dist: shadow-hdk-kernel==0.13.1
   Requires-Dist: shadow-hdk==0.13.1
```
