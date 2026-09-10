---
type: Tasks
phase: 18-the-p1s
---

# Phase 18 — tasks

## Group 1 — the workspace and the leash
- [x] reproduce: hard-link read **and overwrite**; a NUL byte raising out of `invoke`; a marker written after the step returned; `HOME` in the child
- [ ] `_resolve` refuses a hard link; `ValueError` caught; `adapters.md` corrected
- [ ] `run_leashed`: own session, group killed on return (D35), no `HOME`, `TMPDIR` in the workspace, rlimits, output capped as it arrives
- [ ] RED: the four, the other way round
- [ ] Gate

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
