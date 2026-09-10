---
type: Tasks
phase: 11-contained-sandboxes
---

# Phase 11 — tasks

## Group 0 — the contract

- [x] `IsolationBackend`, `Proof`, `NotContained`
- [x] `ContainedSandbox` probes at construction and refuses if it cannot prove containment (D25)
- [x] `FakeIsolation` double
- [x] RED: a proof → `contained: true` and the proof on provenance
- [x] RED: a failed proof → `NotContained`, naming the reason
- [x] RED: an absent binary → `NotContained`, naming the binary
- [x] RED: a run goes through `wrap`, not around it
- [x] RED: Phase 3's `SubprocessSandbox` unchanged
- [x] the leash extracted to `runtime/leash.py` so neither sandbox imports the other — the
      stands-alone invariant refused the first version, which subclassed
- [x] a vacuous timeout test found by mutation and fixed: nothing checked a timed-out child was
      dead rather than abandoned — the same gap Phase 4 recorded
- [x] Gate

## Group 1 — the real backends, as code

- [x] `GVisor` backend: `wrap` and `probe`
- [x] `Firecracker` backend: `wrap` and `probe`
- [x] RED (here): `probe()` is `None` when the binary is absent; `wrap()` shape without running
- [x] live tests marked `live`, skipping when the binary is absent
- [~] the live runs need a Linux host. Settled by `uv run pytest -m live tests/adapters/contained/test_backends.py -k gvisor` with `runsc` on PATH, and `SHADOW_HDK_FC_LAUNCH="<launcher>" uv run pytest -m live tests/adapters/contained/test_backends.py -k firecracker` with a configured microVM. Verified here: both **skip**, naming what they need
- [x] Gate

## Group 2 — the record

- [x] records, board, status, roadmap
