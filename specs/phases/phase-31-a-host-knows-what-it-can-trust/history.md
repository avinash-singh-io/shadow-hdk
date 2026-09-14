---
type: History
status: in-progress
epic: production-boundary
---

# phase-31-a-host-knows-what-it-can-trust — History

### [DECISION] 2026-09-15 — Derived from Epic 0008's production boundary
Topics: capabilities, requirements, provider-evidence, compatibility, shadow, hdk, harness
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface, phase-33-authority-at-the-act
Affects-specs: specs/epics/0008-production-boundary.md; specs/planning/roadmap.md
Detail: The owner approved one strict test-first, per-feature epic and one v0.30.0 release. Phase 31 establishes the typed capability and requirement vocabulary that both later phases consume; Intent Studio waits for the completed epic rather than building an execution patch.

---

### [DISCOVERY] 2026-09-15 — The current implementation is honest but not selectable by requirements
Topics: capabilities, requirements, provider-evidence, sandbox, environment, providers
Affects-phases: phase-31-a-host-knows-what-it-can-trust
Affects-specs: specs/architecture/adapters.md; specs/architecture/wire.md
Detail: Provider data distinguishes model from agent and records tool-injection/session facts, while `Isolation` reports broad reads on macOS; `Available` and the host surface do not expose a typed capability result or let a caller require one. ENH-019 records the generic gap.

---
