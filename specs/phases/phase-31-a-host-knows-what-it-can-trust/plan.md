---
type: Plan
status: complete
epic: production-boundary
---

# Phase 31 — A host knows what it can trust — Plan

```
# Execution:  G0 → (G1 ∥ G2) → G3 → G4
```

> **Derived, not brainstormed.**
> The group breakdown is the one thing the epic CANNOT know — it depends on
> code that exists now and did not when the epic was written. Everything
> above the groups is derived; the groups themselves are authored here.

No dependencies — this phase can start immediately.

Run policy: release: per-feature · push: per-phase · tdd: strict

---

## Group 0 — The capability algebra *(sequential, blocks all)*

RED first in the kernel: a requirement is not a capability; evidence is not the value it supports;
unknown fails strict; mismatches are complete and deterministically ordered. Add immutable,
JSON-round-trippable types for provider capabilities, environment capabilities, requirements,
evidence and `Compatibility`. Keep open protocol names as strings; use closed enums only for the
semantic axes Shadow itself compares. Export them through the public API and schemas.

**Commit:** `feat(kernel): define execution capabilities and requirements`

---

## Group 1 — Providers tell the measured truth *(parallel after G0)*

RED first around `provider_from_data`, shipped files and `Available`: add a nested capability record
whose absent fields remain unknown; reject unknown keys and invalid evidence exactly as the provider
loader already rejects a typo. Record Claude Code, Codex and OpenCode from the measurements already
documented beside their TOML fields. Derive only facts logically forced by an existing field; never
infer a security promise from a marketing/provider name. Expose the record from detection.

**Commit:** `feat(providers): expose measured execution capabilities`

---

## Group 2 — Environments tell the proven truth *(parallel after G0)*

RED first around `Isolation`, `requires` and the live local proof: project the proof into environment
capabilities and add the missing ambient-secret axis as unknown/available rather than pretending it
is denied. Preserve the three existing modes. A host can additionally state requirements stricter
than a mode; construction refuses with a typed compatibility result. Fake environments exercise
every capability without depending on one OS; the macOS proof asserts broad reads explicitly.

**Commit:** `feat(environment): match execution requirements to proof`

---

## Group 3 — One selection decision on every door *(after G1 and G2)*

RED first through `Harness`, `ServeHost`, thread start and the wire. Add requirement-aware provider
and environment selection at the one construction boundary, before either is opened. Add provider
discovery/capability and compatibility results to the wire, bump its protocol version, regenerate
schemas and TypeScript types, and keep Python/TypeScript refusal details identical. No requirements
means the additive 0.29.1 behavior, documented as an explicit compatibility choice.

**Commit:** `feat(serve)!: require provable execution capabilities`

---

## Group 4 — Evidence, docs and the epic checkpoint *(sequential)*

Run focused suites after every group, then the full non-live gate: ruff, format, mypy strict, pytest,
document invariants, schema/client drift and benchmark. Write the capability matrix and 0.29.1
migration note without naming an adopter as part of the API. Record Phase 31 evidence and prepare
Phase 32/33 derivation; do not tag because Epic 0008 releases per feature.

**Commit:** `docs: record the execution capability contract`
