---
type: Plan
status: in-progress
epic: production-boundary
---

# Phase 33 — Authority at the act — Plan

```
# Execution:  G0 → G1 → (G2 ∥ G3) → G4 → G5
```

> **Derived, not brainstormed.**
> The group breakdown is the one thing the epic CANNOT know — it depends on
> code that exists now and did not when the epic was written. Everything
> above the groups is derived; the groups themselves are authored here.

Depends on: phase-31-a-host-knows-what-it-can-trust. Those must be complete before this starts.

Run policy: release: per-feature · push: per-phase · tdd: strict

## Reference specs

- `specs/architecture/runtime.md` — governed-step ordering, acting, children and recovery
- `specs/architecture/wire.md` — record, errors, schemas and crossed transaction status
- `specs/architecture/adapters.md` — which effect paths can truthfully claim controlled posture
- `specs/architecture/testing.md` — frozen evaluator, contract, crash and benchmark gates

---

## Group 0 — Lock the transaction evaluator *(sequential, blocks all)*

RED first with a deterministic state-machine evaluator and a crash injector at every transition.
Lock canonical authority/effect digests, legal append order, single-use grant binding, stale-revision
refusal, parent/child isolation and idempotent versus non-idempotent recovery. The evaluator is
versioned and frozen before implementation; do not change its expected outcomes while optimizing
the implementation.

**Commit:** `test(effects): lock act-time authority and recovery`

---

## Group 1 — Authority and effect records are data *(after G0)*

Add immutable kernel contracts for authority snapshots, staged effects, authorizations and journal
entries/outcomes, each canonical and JSON round-trippable. Define host-owned authority,
authorization and append-only journal ports. An authorization carries no executable callback or
credential; it binds the stage digest, identity, expected authority, expiry, key, run and step.
Export schemas and product-facing contract suites before any adapter uses them.

**Commit:** `feat(kernel): define authority and effect transactions`

---

## Group 2 — The journal survives its process *(parallel after G1)*

Implement the in-memory reference and durable implementations through the shipped store seams with
atomic append/compare semantics. Fold entries rather than mutating an outcome row. Prove two
processes cannot append incompatible next states or consume one authorization twice; a product's
implementation is held to the same contract suite.

**Commit:** `feat(store): keep an append-only effect journal`

---

## Group 3 — Every controlled irreversible invocation crosses one boundary *(parallel after G1)*

Integrate the transaction into the governed step for `posture="controlled"` and irreversible
effects. Stage after ordinary governance/approval, ask the host authorizer, re-read authority at
the last responsible moment, append `executing`, invoke once, then reconcile the returned
observation. A controlled path with no transaction ports is refused rather than silently retaining
its label; observed paths remain records of what Shadow saw but did not control.

**Commit:** `feat(runtime)!: authorize irreversible effects at the act`

---

## Group 4 — Recovery, children and adapter truth *(after G2 and G3)*

Resume/recovery folds unfinished journal histories. A staged-only attempt may be safely abandoned;
an executing attempt without terminal evidence becomes `unknown`. Invoke a reconciler or reuse an
idempotency result only where the adapter contract proves it; never blindly replay a non-idempotent
act. Narrow authority into children and bind authorizations so a parent, child, duplicate delivery
or restarted session cannot cross-consume them. Update devices, environment, callable, MCP and wire
posture reporting to controlled only where this boundary is actually honored.

**Commit:** `feat(effects): reconcile without blind retry`

---

## Group 5 — Public record and the v0.30 candidate *(sequential)*

Carry generic transaction status, receipt/unknown and typed refusals through events, telemetry,
wire, JSON Schema and generated TypeScript. Sync architecture, package and 0.30 migration/release
notes, naming limitations rather than promising exactly-once. Run the frozen evaluator, store
contracts, crash matrix, full ruff/format/mypy/pytest/document/schema/client/benchmark gate, then the
combined Epic 0008 acceptance suite. Mark Phase 33 and the epic complete, build v0.30.0 artifacts
and stop at the owner's protected-branch merge/release approval gate.

**Commit:** `docs: prepare the v0.30 production-boundary candidate`
