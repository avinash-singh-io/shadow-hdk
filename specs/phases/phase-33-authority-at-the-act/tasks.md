---
type: Tasks
status: in-progress
epic: production-boundary
---
# Phase 33 — Authority at the act — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12).
> **TDD strict:** no task may be marked `[x]` without a recorded red→green.
## Group 0 — Lock the transaction evaluator *(blocks)*
- [ ] RED: freeze canonical digest, legal-state, stale-authority, single-use and crash/recovery outcomes
- [ ] Include duplicate/concurrent delivery, parent/child replay and idempotent/non-idempotent matrices
- [ ] Version and commit the evaluator before implementation; record mutation evidence

## Group 1 — Authority and effect records are data
- [ ] Implement/export authority snapshot, staged effect, authorization, journal entry and outcome contracts
- [ ] Define host authority/authorizer/journal ports with canonical JSON and no credentials/callbacks
- [ ] Publish JSON Schemas and product contract suites; verify round trips and illegal-state refusal

## Group 2 — The journal survives its process
- [ ] Implement in-memory and shipped durable append-only journals with atomic legal-next-state checks
- [ ] Fold histories to current status; never overwrite a fact or consume a grant twice
- [ ] Verify contract suites, concurrent writers, restart and terminal-outcome uniqueness

## Group 3 — Every controlled irreversible invocation crosses one boundary
- [ ] Stage after governance/approval, authorize separately, re-read authority, append executing, invoke once, reconcile
- [ ] Refuse stale authority, expired/mismatched/replayed grants and controlled paths without transaction support
- [ ] Verify exact transition order and no component invocation on every refusal branch

## Group 4 — Recovery, children and adapter truth
- [ ] Recover staged/executing histories to safe abandonment, receipt or explicit unknown
- [ ] Reconcile/reuse only proven idempotent results; never blindly retry an uncertain non-idempotent act
- [ ] Narrow child authority, isolate grants and update shipped adapter posture/integration truth
- [ ] Verify crash injection, duplicate delivery, child attacks and provider-session restart without repeated receipts

## Group 5 — Public record and the v0.30 candidate
- [ ] Carry transaction/refusal/receipt/unknown through events, telemetry, wire, schemas and TypeScript
- [ ] Sync architecture, package, migration and release-candidate docs with limitations
- [ ] Run frozen evaluator, store contracts, crash matrix and full combined Epic 0008 gate
- [ ] Build v0.30.0 artifacts, mark Phase 33/epic complete and stop at protected merge/release approval
