---
type: History
status: in-progress
epic: production-boundary
---

# Phase 33 — Authority at the act — History

### [SCOPE_CHANGE] 2026-09-15 — Derived from Epic 0008 after the capability boundary
Topics: authority, revisions, effect-authorization, act-time, effect-journal, reconciliation, unknown-outcome, receipts
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/wire.md; specs/architecture/testing.md; docs/migrations/0.30.md
Detail: The epic's Phase 33 row is decomposed into a frozen transaction evaluator, canonical authority/effect records and host ports, append-only reference journals, one governed act boundary, and crash-safe recovery. Approval remains consent evidence; provider/environment capabilities remain facts; only current host authority may issue the single-use act authorization.

---

### [NOTE] 2026-09-15 — Phase 33 started from the verified Phase 32 checkpoint
Topics: authority, revisions, effect-authorization, act-time, effect-journal, reconciliation, tdd
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/status.md; specs/phases/README.md
Detail: The stacked branch starts at Phase 32 commit `2ab153a` after the full green gate. Pre-flight found no P0 bug; TD-010 and TD-011 are the planned P1 work. Group 0 freezes the deterministic transaction evaluator before implementation, and the phase remains unreleased until the single Epic 0008 gate.

---

### [EVALUATOR] 2026-09-15 — Effect transaction v1 is frozen and RED
Topics: authority, effect-authorization, effect-journal, reconciliation, idempotency, tdd
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/testing.md
Detail: `tests/benchmarks/effect-transaction-v1.json` locks legal/illegal histories and crash recovery outcomes behind a SHA-256 immutability test. The runtime evaluator covers every authority/stage binding, stale act-time reads, grant replay, concurrent duplicate delivery, parent/child isolation and idempotent reconciliation; it fails at collection only because the new kernel/runtime contracts do not exist. A one-nibble hash mutation failed the freeze test and was reverted before commit.

---

### [FEATURE] 2026-09-15 — Authority and effect transaction records are public data
Topics: authority, revisions, effect-authorization, effect-journal, schemas, contracts
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/wire.md; specs/architecture/testing.md
Detail: Secret-free AuthoritySnapshot, exact StagedEffect, bound EffectAuthorization and append-only EffectEntry contracts now live in the kernel with canonical SHA-256 digests. Host-owned authority, authorizer and journal protocols plus importable product contract suites are published; 24 JSON Schemas and generated TypeScript contracts build cleanly. Five focused contract/freeze checks and strict mypy/Ruff are green while the frozen evaluator remains RED only on the intentionally absent runtime transaction.

---

### [FEATURE] 2026-09-15 — Effect histories survive and serialize concurrent writers
Topics: effect-journal, sqlite, postgres, recovery, idempotency, contracts
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/adapters.md; specs/architecture/runtime.md; specs/architecture/testing.md
Detail: One fold validates the frozen legal transition graph and derives state without rewriting facts. In-memory, SQLite and Postgres journals expose compare-and-append; SQLite uses an immediate transaction, Postgres an attempt-scoped advisory transaction lock, and both enforce globally unique authorization consumption. Eight SQLite/memory contract, restart and concurrency checks pass; eleven Postgres checks are collected and environment-skipped. Inverting the memory CAS predicate produced four focused failures and was reverted.

---

### [FEATURE] 2026-09-15 — Every controlled irreversible act crosses one current-authority boundary
Topics: authority, effect-authorization, act-time, effect-journal, refusal, idempotency, tdd
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/testing.md
Detail: After ordinary governance and any approval, StepExecutor stages the exact act, obtains a one-attempt grant, rereads current host authority, appends executing, invokes once and records its receipt or failure. Missing transaction ports fail closed; stale, expired, mismatched and cross-run grants never invoke; observed paths remain observation-only. The frozen evaluator has 29 green cases, the focused integration has four, and all 448 runtime tests pass with one environment skip. Removing the authority reread let a stale act execute, and disabling the missing-port guard changed its refusal to failure; both destructive mutations were reverted.

---

### [FEATURE] 2026-09-15 — Recovery reuses evidence and the ready-made host owns the boundary
Topics: authority, effect-journal, reconciliation, unknown-outcome, idempotency, children, adapter-posture
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/adapters.md; specs/architecture/testing.md
Detail: The store URL now chooses the effect journal beside records, threads and checkpoints; ServeHost and workshop bind a reference authority over live identity, workspace, policy, registry, provider and mode revisions plus a short-lived exact-stage authorizer. SQLite and Postgres survive process loss, terminal receipts are reused only for the same stage digest, unfinished histories fold to abandonment or unknown, and reconciliation requires explicit idempotency proof plus external evidence. Child runs retain the parent's policy boundary but receive distinct run/step-bound grants. The combined runtime, serve, adapter and child gate passed 829 tests with three environment skips and one deliberate deselection; two destructive mutations proved durable replay and store selection.

---

### [DISCOVERY] 2026-09-15 — Durable authorization identity belongs on one fact
Topics: effect-journal, effect-authorization, sqlite, postgres, recovery
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/adapters.md
Detail: BUG-052 exposed a mismatch between the in-memory and SQL journals: SQL correctly made authorization IDs unique, while the runtime repeated the same ID on executing and terminal entries. The transaction now records it only on `authorized`, and the fold carries it into later state; a real SQLite act and process-style reopen is the regression proof.

---

### [FEATURE] 2026-09-15 — Public transaction record and v0.30.0 candidate complete
Topics: effect-recorded, protocol-3, telemetry, release-candidate, migration
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/wire.md; specs/architecture/adapters.md; specs/architecture/testing.md; docs/migrations/0.30.md
Detail: `EffectRecorded` and `Item.effect` make generic transaction state public across Python, wire schemas and generated TypeScript; OpenTelemetry carries only status/digest metadata. The protocol advances to v3 so old peers refuse rather than omit the lifecycle. The complete v0.30.0 candidate gate passed: build, Ruff, strict mypy over 441 files, 1,688 non-live tests (14 skipped, 12 live deselected), TypeScript generation/check/build, Twine and OKF. The candidate is pushed but intentionally not merged, tagged or published pending owner approval.

---
