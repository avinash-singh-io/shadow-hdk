---
type: Plan
phase: 18-the-p1s
---

# Phase 18 — plan

```
# Sequential, the security-shaped ones first. Each group reproduces before it fixes.
```

## Group 1 — the workspace and the leash (BUG-008, BUG-009 except the proof)

- `_resolve` asks the filesystem, not the name: refuse `st_nlink > 1` on a regular file; catch
  `ValueError` (a NUL byte) where `OSError` is already caught; `adapters.md` corrected on
  `write_file`'s `contained`
- `run_leashed`: `start_new_session=True`; kill the **group** when the leash returns, timeout or
  not (D35); `HOME` out of `KEPT_ENV`; `TMPDIR` pointed at the workspace; rlimits where the
  platform has them; output capped as it arrives
- RED: the four reproductions, each the other way round

**Commit:** `fix(workspace,runtime)!: a hard link is not confined, and a step owns its process tree`

## Group 2 — a proof is a capability test (D36)

- `Proof` splits: `declared` (the backend's own word) and `checks` (what was attempted and denied)
- a capability test the backend runs inside itself; `ContainedSandbox` refuses a backend that
  cannot be tested unless the deployment names its trust in an argument
- RED: a fake backend that runs commands locally cannot produce a proof; the banner alone is not
  a proof; the named-trust path says what it is

**Commit:** `fix(contained)!: containment is proven by what is denied, never by what is announced`

## Groups 3–5

BUG-015; then BUG-010; then BUG-011, BUG-012, TD-003. TD-009 prepared and handed to the owner.
