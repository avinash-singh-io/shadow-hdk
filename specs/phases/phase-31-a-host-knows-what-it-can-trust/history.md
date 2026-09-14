---
type: History
status: complete
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

### [DISCOVERY] 2026-09-15 — The run manifest ignored the epic's release policy
Topics: momentum, release-policy, epic
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface, phase-33-authority-at-the-act
Affects-specs: specs/epics/0008-production-boundary.md
Detail: `momentum run start epic production-boundary` materialized `release: per-phase` although Epic 0008 records `policy_release: per-feature`. The epic record and owner's approval remain authoritative: no phase-boundary release; one v0.30.0 after Phase 33. The mismatch belongs to momentum tooling and is not allowed to change Shadow's release plan.

---

### [FEATURE] 2026-09-15 — Capability and requirement algebra locked before adapters
Topics: capabilities, requirements, provider-evidence, compatibility, tdd
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface, phase-33-authority-at-the-act
Affects-specs: specs/architecture/adapters.md; specs/architecture/wire.md
Detail: RED first failed because `CapabilityEvidence` did not exist. GREEN adds typed provider and environment facts, caller requirements, evidence per axis and a total compatibility result in stable provider-then-environment order; unknown never satisfies a production requirement. Fresh gates: 32 focused tests, ruff and mypy all pass.

---

### [FEATURE] 2026-09-15 — Provider records expose measured capability truth
Topics: capabilities, provider-evidence, providers, api-model, tdd
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md
Detail: RED named seven missing behaviors: absent facts, nested validation paths, shipped matrices and detection exposure. GREEN adds a conservative capability record to every provider, validated nested TOML with per-axis evidence, measured/derived records for Claude Code, Codex and OpenCode, and the same record for model-provider adapters. Fresh gates: 90 provider/kernel contract tests, ruff and mypy pass.

---

### [FEATURE] 2026-09-15 — Environment truth is the effective isolation and mode
Topics: capabilities, environment, sandbox, proof, secrets, tdd
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-33-authority-at-the-act
Affects-specs: specs/architecture/runtime.md; specs/architecture/adapters.md
Detail: RED failed at the absent typed incompatibility. GREEN projects isolation through mode, distinguishes denied, ambient and unknown secrets, exposes the report on every environment, and refuses stricter requirements with the complete compatibility result. The live macOS proof confirms workspace-confined writes and denied network while reporting machine-wide reads and ambient secrets. Fresh gates: 83 broader tests pass (one expected inverse-platform skip), the focused live file has 12 passes, and ruff/mypy pass.

---

### [FEATURE] 2026-09-15 — One capability selection guards every construction door
Topics: capabilities, requirements, compatibility, serve, facade, wire, thread, typescript, tdd
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface
Affects-specs: specs/architecture/adapters.md; specs/architecture/wire.md; specs/architecture/runtime.md
Detail: Seven RED failures named the missing host/facade arguments, retained selection, typed wire refusal and provider discovery. GREEN resolves/proves the pair before opening an agent, persists requirements on record version 3 for resume, returns the accepted selection from direct Python and protocol v2, and adds `providers/list` plus `capabilities/check`; JSON Schemas and generated TypeScript types move together. Fresh broader gate: 229 tests pass with one expected inverse-platform skip; ruff, mypy and TypeScript compilation pass.

---

### [DISCOVERY] 2026-09-15 — Schema publisher escaped the repository after D78
Topics: wire, schemas, spec-drift
Affects-phases: phase-31-a-host-knows-what-it-can-trust
Affects-specs: specs/architecture/wire.md; specs/architecture/testing.md
Detail: The documented module command resolved its default two directories above the repository and created an external generated schema directory. BUG-045 records the defect; the output was inspected and removed, a failing exact-target test was added, and the default now resolves to this repository.

---

### [ARCH_CHANGE] 2026-09-15 — Capability truth is published at every consumer door
Topics: capabilities, requirements, provider-evidence, environment, wire, testing
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface, phase-33-authority-at-the-act
Affects-specs: specs/architecture/adapters.md; specs/architecture/runtime.md; specs/architecture/wire.md; specs/architecture/testing.md; README.md; docs/consuming.md; docs/packages/kernel.md; docs/packages/providers.md; docs/packages/runtime.md; docs/packages/serve.md; docs/packages/wire.md; docs/migrations/0.30.md
Detail: The additive Phase 31 contracts are now recorded in the constitutional specs, package guides and consumer migration note. The matrix preserves provider differences and the environment note explicitly distinguishes confined writes and denied network from machine-wide reads and ambient secrets; 53 focused document, parity and schema checks pass.

---

### [DISCOVERY] 2026-09-15 — The configured build gate removed the dependencies its next gates need
Topics: testing, mypy, ci, landing
Affects-phases: phase-31-a-host-knows-what-it-can-trust
Affects-specs: specs/config.md; specs/backlog/backlog.md
Detail: The configured `uv sync --all-packages` succeeded by uninstalling 29 optional packages, after which full pytest and mypy could not import the Postgres, MQTT, LangChain and OpenSandbox adapters. BUG-046 is closed by making the build command match CI's all-extras install; the completion gate also caught and formatted five Phase 31 files before any checkpoint claim.

---

### [DISCOVERY] 2026-09-15 — Historical metadata failed the current spec-conformance audit
Topics: spec-drift, testing, landing
Affects-phases: phase-31-a-host-knows-what-it-can-trust
Affects-specs: specs/adhoc/TD-009/pull-request-body.md; specs/decisions/index.md; specs/backlog/backlog.md
Detail: The optional OKF closeout check found one historical artifact without frontmatter and a reserved index with frontmatter it must not carry. BUG-047 records the exact red audit; only metadata is changed and the historical content remains intact.

---

### [NOTE] 2026-09-15 — Phase 31 verified as the first unreleased epic checkpoint
Topics: capabilities, requirements, compatibility, testing, landing
Affects-phases: phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface, phase-33-authority-at-the-act
Affects-specs: specs/status.md; specs/planning/roadmap.md; specs/epics/0008-production-boundary.md
Detail: The final tree passes build sync with every extra, Ruff lint and formatting, strict mypy over 422 source files, 1,600 non-live tests with 12 platform/service skips and 12 live deselections, 55 explicit document/decision/schema/benchmark checks, config validation and OKF over 185 specs. Phase 31 is complete but deliberately untagged and unmerged; Phases 32 and 33 are fully derived and the one v0.30.0 release remains behind the final epic gate.

---

### [DISCOVERY] 2026-09-15 — The decision index could not see epic decision tables
Topics: spec-drift, testing, epic
Affects-phases: phase-31-a-host-knows-what-it-can-trust
Affects-specs: specs/decisions/index.md; tests/invariants/test_the_decisions_index_is_true.py; specs/backlog/backlog.md
Detail: Adding D95–D106 to the decision index produced a red invariant because its declaration parser recognized headings and history entries but not momentum's canonical epic table. BUG-048 closes the format gap in the invariant rather than duplicating the decisions; both index directions are re-run before checkpoint completion.

---
