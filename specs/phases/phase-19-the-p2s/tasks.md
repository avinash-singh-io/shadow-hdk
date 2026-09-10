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

## Groups 2–4
- [ ] BUG-013, BUG-014
- [ ] TD-004, TD-005
- [ ] TD-006, TD-007, TD-008
- [ ] records, board, status, roadmap
