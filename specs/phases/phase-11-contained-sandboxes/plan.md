---
type: Plan
phase: 11-contained-sandboxes
---

# Phase 11 — plan

```
# Sequential: Group 0 → 1 → 2.
```

## Group 0 — the contract, and a backend that proves itself

- `IsolationBackend` protocol: `name`, `probe()` → `Proof | None`, `wrap(argv)` → argv
- `Proof`: what was observed, by which backend, when — carried on provenance
- `ContainedSandbox(root, backend, …)`: probes at construction; **raises** `NotContained` naming
  the backend and the reason if the proof fails or the binary is absent; registers `contained=True`
  only on a proof
- `FakeIsolation(proves=True|False, present=True|False)` for tests, under `runtime.testing`-style
  doubles in this package
- RED: proves → `contained: true` and the proof on provenance; fails → `NotContained` with the
  reason; absent → `NotContained` naming the binary; a run goes *through* `wrap`, not around it;
  Phase 3's `SubprocessSandbox` still works unchanged

**Commit:** `feat(adapters): a sandbox that proves it is contained, or refuses to exist`

## Group 1 — the two real backends, as code

- `GVisor` (`runsc`): wraps argv in `runsc run` against a minimal OCI bundle; probe reads the
  kernel's self-announcement
- `Firecracker`: wraps argv for a microVM launch; probe reads the guest's hardware identity
- Both **skip** their live tests when the binary is absent — never pass, never fail
- RED (here): each backend's `probe()` returns `None` when the binary is absent; each `wrap()`
  produces the expected argv shape without running anything
- `[~]`: the live tests, with the command per backend

**Commit:** `feat(adapters): gVisor and Firecracker as backends that must prove themselves`

## Group 2 — the record

- tasks, history, status, roadmap, board; the `[~]` rows say exactly what a Linux host would run
