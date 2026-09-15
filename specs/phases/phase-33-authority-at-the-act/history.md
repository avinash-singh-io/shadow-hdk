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
