---
type: Tasks
phase: 18-the-p1s
---

# Phase 18 — tasks

## Group 1 — the workspace and the leash
- [x] reproduce: hard-link read **and overwrite**; a NUL byte raising out of `invoke`; a marker written after the step returned; `HOME` in the child
- [x] `_resolve` refuses a regular file more than one name reaches (directories exempt: their link count is their subdirectories plus two); `ValueError` from a NUL byte caught where every other filesystem refusal already was; `adapters.md` corrected on `write_file`'s `contained`
- [x] `run_leashed`: own session, the **group** killed when the leash returns (D35), no `HOME`, `TMPDIR` in the workspace, `memory_mb` by `prlimit` from the parent with `MEMORY_LIMIT_ENFORCED` saying where it bites, output capped as it arrives
- [x] RED: the four, the other way round — 24 tests (9 workspace, 15 leash, one skipped on macOS with its reason)
- [x] Gate — ruff 0 / format 0 / mypy 0 (121 files) / pytest 752 passed, 1 skipped, 10 deselected; 15 mutations, all bite

## Group 2 — a proof is a capability test (D36)
- [x] reproduce: a five-line fake `runsc` on `PATH` produced a `Proof`
- [ ] `Proof.declared` / `Proof.checks`; a capability test; refusal without one unless trust is named
- [ ] RED: a backend that does not contain cannot prove; a banner is not a proof
- [ ] Gate

## Groups 3–5
- [ ] BUG-015 — a held child across its parent's park
- [ ] BUG-010 — the double invoke, and a re-run judgement overriding a human
- [ ] BUG-011, BUG-012, TD-003
- [ ] TD-009 — the workflow change, and the pull request prepared for the owner
- [ ] records, board, status, roadmap
