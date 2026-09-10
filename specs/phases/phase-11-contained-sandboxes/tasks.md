---
type: Tasks
phase: 11-contained-sandboxes
---

# Phase 11 — tasks

## Group 0 — the contract

- [ ] `IsolationBackend`, `Proof`, `NotContained`
- [ ] `ContainedSandbox` probes at construction and refuses if it cannot prove containment (D25)
- [ ] `FakeIsolation` double
- [ ] RED: a proof → `contained: true` and the proof on provenance
- [ ] RED: a failed proof → `NotContained`, naming the reason
- [ ] RED: an absent binary → `NotContained`, naming the binary
- [ ] RED: a run goes through `wrap`, not around it
- [ ] RED: Phase 3's `SubprocessSandbox` unchanged
- [ ] Gate

## Group 1 — the real backends, as code

- [ ] `GVisor` backend: `wrap` and `probe`
- [ ] `Firecracker` backend: `wrap` and `probe`
- [ ] RED (here): `probe()` is `None` when the binary is absent; `wrap()` shape without running
- [ ] live tests marked `live`, skipping when the binary is absent
- [ ] `[~]` the live runs, with the command per backend
- [ ] Gate

## Group 2 — the record

- [ ] records, board, status, roadmap
