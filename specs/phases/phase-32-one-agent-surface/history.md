---
type: History
status: in-progress
epic: production-boundary
---

# Phase 32 — One agent surface — History

### [SCOPE_CHANGE] 2026-09-15 — Derived from the verified Phase 31 capability boundary
Topics: model-agent, agent-surface, item-inputs, stream-session, heartbeat, authentication
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md; specs/architecture/wire.md; specs/architecture/testing.md; docs/migrations/0.30.md
Detail: The epic's Phase 32 row is decomposed into one parity evaluator, a ModelPort-to-AgentPort adapter, Item.inputs, a reusable stream session, heartbeat/silence recovery and safer bearer sources. Phase 31 is the dependency: both provider kinds must retain the same evidence-backed selection before either agent session opens.

---

### [NOTE] 2026-09-15 — Phase 32 started on the stacked epic branch
Topics: model-agent, agent-surface, item-inputs, stream-session, heartbeat, authentication, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/status.md; specs/phases/README.md
Detail: The branch starts at Phase 31's verified commit `7b9f298`. Group 0 is the only active work: write and observe the cross-provider lifecycle, item, stream-session and bearer-source failures before implementing any Phase 32 behavior; no version, release or Intent Studio surface changes here.

---
