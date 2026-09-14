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

### [EVALUATOR] 2026-09-15 — The unified lifecycle boundary is RED before implementation
Topics: model-agent, agent-surface, item-inputs, stream-session, heartbeat, authentication, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md; specs/architecture/wire.md; specs/architecture/testing.md
Detail: Product-facing tests now lock the shared Thread/tool/usage/activity shape, canonical bounded Item.inputs, monotone bounded single-attachment stream sessions with typed stale cursors and injected-time expiry/heartbeat, and bearer file/environment/flag precedence with permission and disclosure refusals. The focused run fails only on the absent ModelAgent, item projection field/bound, runtime stream module and bearer resolver; the existing CLI scenario independently reaches the shared Item.inputs failure.

---

### [DISCOVERY] 2026-09-15 — A live SSE frame is emitted twice
Topics: stream-session, heartbeat, wire, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/wire.md#The thread, crossed
Detail: While mapping the private HTTP session into the locked evaluator, `stream_of` was found to yield the same numbered live frame twice. BUG-049 records the defect; the shared session's replay-then-live-once test is the Phase 32 fix boundary, rather than a separate patch beside the extraction.

---

### [EVALUATOR] 2026-09-15 — Model interruption is RED at the provider call
Topics: model-agent, agent-surface, cancellation, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md#The agent adapter
Detail: A blocked ModelPort call now exercises Thread.interrupt through the new adapter. Before the cancellation path exists, interrupt marks the run but only closes a flag on the model session; the provider call remains blocked and the focused evaluator times out instead of recording a cancelled turn.

---

### [FEATURE] 2026-09-15 — ModelPort is an AgentPort below the durable Thread
Topics: model-agent, agent-surface, capability-selection, cancellation, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md#The agent adapter; docs/migrations/0.30.md
Detail: ModelAgent reuses the existing governed model loop under the same Thread, host selection and product-facing lifecycle as a CLI-owned agent. The adapter keeps model usage honest when unreported, maps a parked child step back to its durable run for later settlement, and cancels an active provider call on Thread.interrupt; 187 focused lifecycle tests and three destructive mutations verify routing, cancellation and parked-child identity.

---
