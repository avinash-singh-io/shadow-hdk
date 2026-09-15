---
type: History
status: complete
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

### [FEATURE] 2026-09-15 — Item carries the invocation inputs once
Topics: item-inputs, agent-surface, wire, typescript, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/wire.md#The thread, crossed; docs/migrations/0.30.md
Detail: The shared Fold now projects each Invoked input into Item.inputs, preserves it through reopen/freeze and the wire, and emits an explicit byte-counted omission marker above the 64 KiB canonical JSON boundary. Python contracts, the published schema and generated TypeScript all carry the field; 67 focused checks and three destructive mutations verify retention, the exact bound and crossed projection.

---

### [FEATURE] 2026-09-15 — One transport-independent stream session
Topics: stream-session, heartbeat, wire, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/wire.md#The thread, crossed; specs/architecture/runtime.md
Detail: Runtime StreamSession now owns monotone bounded replay, typed stale cursors, exactly one attachment, injected-clock grace expiry and ephemeral idle heartbeats. HTTP/SSE consumes this primitive rather than owning another queue/outbox/timer implementation; 22 focused state/property and D94 integration tests plus four destructive mutations verify the boundary.

---

### [NOTE] 2026-09-15 — BUG-049 was an invalid reading, not a duplicate-frame defect
Topics: stream-session, wire, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: none
Detail: The two `_sse` yield sites are the replay loop and the later live loop, not consecutive live emissions; the last-replayed guard and D94 unique-id assertion already covered the seam. The backlog row is deprecated with the correction, while the shared extraction still makes replay-then-live-once a direct state-machine property.

---

### [EVALUATOR] 2026-09-15 — HTTP heartbeat and client silence recovery are RED
Topics: heartbeat, stream-session, typescript, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/wire.md#The thread, crossed
Detail: A live HTTP test requires an idle connection to receive an SSE heartbeat comment, while a deterministic TypeScript fake transport holds a link silently open and requires reattachment with its last event id. The server test fails on the absent heartbeat option and the client build fails on the absent silenceSeconds contract before either path is implemented.

---

### [FEATURE] 2026-09-15 — Silent links recover and production bearers stay out of argv
Topics: heartbeat, stream-session, typescript, authentication, tdd
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/wire.md#The thread, crossed; docs/migrations/0.30.md
Detail: Idle HTTP streams now emit 15-second SSE comments from StreamSession without allocating an id or record, and the TypeScript client treats 45 seconds without bytes as a dropped link before reattaching with its last event id. Serve resolves a permission-checked regular token file before SHADOW_HDK_TOKEN before the documented local-only flag; 20 focused checks and five destructive mutations verify framing, silence detection, cursor retention, precedence, permissions and redaction.

---

### [ARCH_CHANGE] 2026-09-15 — One-agent and stream contracts synchronized
Topics: model-agent, agent-surface, item-inputs, stream-session, heartbeat, authentication, typescript
Affects-phases: phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md; specs/architecture/runtime.md; specs/architecture/wire.md; specs/architecture/testing.md; docs/migrations/0.30.md; docs/packages/adapters-agent.md; docs/packages/runtime.md; docs/packages/serve.md; docs/packages/wire.md; clients/typescript/README.md; README.md
Detail: Completion sync documents the already-approved additive Phase 32 contracts: ModelAgent below the common Thread surface, bounded Item.inputs, runtime-owned reconnect state, ephemeral heartbeat/client silence recovery and permission-checked bearer sources. The phase index was regenerated; the decision index rewrite was rejected because the generator would erase the repository's canonical D1–D106 map, recorded as BUG-050.

---

### [DISCOVERY] 2026-09-15 — Passing gate retains two cleanup warnings
Topics: acp, mqtt, testing
Affects-phases: none
Affects-specs: specs/backlog/backlog.md
Detail: The full suite is green, but an ACP refusal test can leave a subprocess transport to finalize after loop closure (BUG-051), and the AMQTT broker fixture uses APIs marked for removal (TD-012). Both are isolated from the Phase 32 contract and recorded for bounded follow-up rather than folded into the epic.

The Phase 33 pre-flight also found ENH-019 still marked planned after its Phase 31 implementation;
the verified capability boundary is present, so the stale backlog row is closed without changing
scope. The learnings tool's TD-012 stale-closure suggestion was rejected after inspection.

---

### [NOTE] 2026-09-15 — Phase 32 complete as an unreleased epic checkpoint
Topics: model-agent, agent-surface, item-inputs, stream-session, heartbeat, authentication, testing
Affects-phases: phase-33-authority-at-the-act
Affects-specs: specs/status.md; specs/phases/README.md
Detail: Build and static gates pass; 1,625 tests pass with 12 expected skips and 12 live deselections; focused lifecycle, item, reconnect, bearer and benchmark checks add 30 passes; document/schema/parity checks add 61 passes; TypeScript check/build and deterministic silence recovery pass; OKF validates 185 specs. The checkpoint is pushed without a tag, protected-branch merge, release or Intent Studio edit, and Phase 33 starts from it.

---
