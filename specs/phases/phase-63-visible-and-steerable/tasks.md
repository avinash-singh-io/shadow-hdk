---
type: Tasks
---

# Phase 63 — tasks

## G1 — the agent's own plan
- [x] `PlanComponents` registering `update_plan`, with an empty `EffectProfile` (D171)
- [x] `status` an open string (D172); a wordless step and a 200+ plan refused
- [x] revisions counted; the latest kept for a host attaching mid-run
- [x] the record carries it through `Invoked.inputs` — nothing extra built
- [x] mutation-checked: 4 bite

## G2 — a key-backed model's turn is steerable
- [x] `_Turnwise.steer` queues; `_fold_in_steers` delivers before the next model call (D173)
- [x] `_ModelSession.steer` routes to the live loop; `False` where there is none
- [x] asserted against **what the model was actually asked**, not `steer`'s return value
- [x] mutation-checked: 2 bite — one of which found the session-level refusal untested

## G3 — close out
- [x] `docs/migrations/0.42.md`
- [x] 0.42.0, the Linux helper in lockstep
- [x] full gate: ruff clean, format 558 files, mypy 496 files, **2021 passed** / 20 skipped
- [x] `specs/status.md`; ENH-045 and ENH-046 closed
