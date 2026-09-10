---
type: Tasks
phase: 19-the-p2s
---

# Phase 19 — tasks

## Group 1 — the latency budget (BUG-016)
- [x] reproduce: a 100-step run built **101** adapters; one costs **0.743 ms**; the 101 are **75 ms of a 132 ms run — 57%**
- [x] one dict keyed on the type, in `kernel/contracts.py`; unbounded on purpose and argued (a type set cannot grow with load)
- [x] RED on the mechanism — a run builds one adapter per contract type, however many steps it takes
- [x] re-measured: **59.4 / 60.0 / 59.7 ms — 0.594 ms/step**, inside D11's ≤ 1 ms; fan-out 24 ms against 50
- [x] **D11's slack deliberately not tightened** — the runner is 2.1× this machine and the drift was 2.4×; the ranges overlap, so no threshold separates them. Recorded as a decision
- [x] `.coverage` untracked and ignored — a binary rewritten by every coverage run, tracked since the first commit
- [x] Gate — ruff 0 / format 0 / mypy 0 (133 files) / pytest 845 passed, 1 skipped, 10 deselected; 7 mutations, all bite
- [x] **CI green for the first time in this repository's history** — 96.77% coverage, 842 passed on Linux, all three benchmarks inside their assertions

## Group 2 — derivation and the sink (BUG-013, BUG-014)
- [x] BUG-013 reproduced, and **the audit's row corrected in three places** (the `NaN` literal, the place normalisation bites, what a float actually costs)
- [x] `evaluate` is total — `out_of_range` names the value that would not fit; the component's `try` covers it too, and that guard is now tested by making the engine raise on purpose
- [x] magnitudes canonical through the arithmetic's own quantizer, in the tree and in the cells
- [x] NFC on both sides of a `count_where`, so the value and the identity agree
- [x] a cell is a string or a boolean, refused with the row, the column and what to send
- [x] **two existing tests encoded the weaker property** — that the canonical tree echoes the caller's spelling — and were rewritten from the corrected premise
- [x] **unit cancellation deliberately deferred** and recorded: a design question, not a defect
- [x] BUG-014: every byte written or a raise; the torn tail cut back before any append; the record written off the event loop; the directory synced once; a context manager with idempotent close
- [x] **Phase 14's *a torn line can only be the last* retired** — true within one process, false across a restart, which is the only time one exists
- [x] Gate — ruff 0 / format 0 / mypy 0 (133 files) / pytest 871 passed, 1 skipped, 10 deselected; 24 mutations, 23 bite, 1 equivalent and named

## Group 3 — the shared shape and what bounds growth (TD-004, TD-005)
- [x] the contract suites reached 7 of 14 adapters; **the fix is an invariant**, not the wiring — every port implementation must name the module that contracts it, and that module is checked to really contain a contract
- [x] the scan found **29** implementations, not fourteen: the runtime's testing doubles are ports hosts depend on
- [x] five adapters wired plus `Controlled`, `RuleGovernance`, `Mailbox`; **`mqtt` and `recording` implement no port at all** and are recorded as such
- [x] **the suites found no defects**, so the net was widened by one question while being cast: inputs of the wrong shape are an observation, not an exception — eleven component ports answer it
- [x] the plan cache: 2000 compositions → 2000 entries, ~6.3 MiB; now 512, least-recently-used, evictions counted
- [x] the observer queue: a slow observer handled 1 event while 49,999 queued; bounded at 4096, **dropping the oldest and counting**, because D11 keeps the observer off the critical path
- [x] the caller's stream stays **unbounded and argued** — same task fills and drains it, so a bound deadlocks the run against itself
- [x] **two of TD-005's three claims were stale** — the witness queue was bounded in Phase 16, and the wire has no queues
- [x] Gate — ruff 0 / format 0 / mypy 0 (133 files) / pytest 924 passed, 1 skipped, 10 deselected; 11 mutations, all bite

## Group 4 — the leaks and the record (TD-006, TD-007, TD-008)
- [x] TD-006 reproduced, and **six claims turned out to be one root cause**: `RuntimeStop` was an `Exception`, so every component adapter's `except Exception` swallowed a lease, a cancellation and a port failure alike
- [x] `RuntimeStop` is a `BaseException` — the argument that moved `asyncio.CancelledError` in 3.8; it fixes adapters nobody has written yet
- [x] `visible()` wraps its judgement; `propose()` announces only what the sink took; `unreachable` is readable; the lease is charged for work, not for being refused
- [x] the step's docstring said seven moves, `runtime.md` a different seven — it does **nine**, and the two that arrived unrecorded were D15's cancellation check and D38's resume branch
- [x] **an existing test asserted the inversion while citing D7** and was rewritten, name included
- [x] **contract 0.12.0 → 0.13.0** — see *Pins*
- [x] TD-007's plumbing: `posture` and `component` refused at the door rather than silently overwritten
- [x] **TD-007's policy recorded as the owner's under ADR-1**, not invented: whether an irreversible step must produce an `Acted` whichever port it came through
- [x] TD-008: `specs/decisions/` carries a **map of all thirty-eight**, with an invariant that keeps it true; the decisions stay beside the work that forced them
- [x] Gate — ruff 0 / format 0 / mypy 0 (133 files) / pytest 940 passed, 1 skipped, 10 deselected; 9 mutations, all bite
- [ ] **TD-008's remaining half**: `runtime.md`, `file-structure.md`, `adapters.md`, `wire.md`, `CLAUDE.md`'s dead link, the `.githooks`, and `recursion_limit`
- [ ] TD-006, TD-007, TD-008
- [ ] records, board, status, roadmap
