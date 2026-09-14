---
type: Phase
status: in-progress
epic: production-boundary
tags: []
deps: []
---

# Phase 31 — A host knows what it can trust

> **Derived, not brainstormed.**
> Generated from `specs/epics/0008-production-boundary.md` on 2026-09-15 with no
> operator interview (Epic D10). Every decision below was settled when the
> epic was written and is NOT re-litigated here. Decisions are durable;
> plans are perishable — this file is the perishable half.

## Goal

A host states the execution properties it requires and receives either a provider/environment pair
whose capabilities are known to satisfy them or a typed mismatch naming what is absent, weaker or
unknown. The same facts and decision are available through the Python surface, `Harness`, `serve`
and the generated TypeScript client. No product has to reverse-engineer a provider TOML, infer
security from a mode's name, or turn missing evidence into permission.

## Inherited decisions

> From the epic record. Never re-asked.

- D95 — **One umbrella, two surfaces:** Shadow HDK is the construction kit; Shadow Harness is the ready-to-run reference assembly built only from the HDK's public contracts _(A product can begin with defaults and progressively replace them without crossing into another runtime, repository or private API)_
- D96 — **Capability, requirement and evidence are different types.** Providers and environments report what they can do and how it was established; a host states what it requires; an unknown never satisfies a production requirement _(A boolean feature bag can contradict itself and silently turn missing evidence into permission. Compatibility must be computed and a mismatch must be data)_
- D97 — **Provider truth, environment truth and execution authority stay separate.** A provider owns either inference or an agent loop; an environment proves containment; the host owns permission to act _(A strict provider cannot compensate for an unconfined environment, and a sandbox cannot turn a provider's ungoverned native tools into controlled effects)_
- D98 — **One durable agent surface for both provider kinds.** A `ModelPort` is adapted behind `AgentPort`; `Thread` remains the product-facing conversation lifecycle _(A product must not build a second runner to get API-backed models, and changing provider kind must not discard holding, parking, spend, cancellation or recovery)_
- D99 — **Approval is evidence of consent, not executable authority.** The host issues a separate, single-use effect authorization immediately before an irreversible act _(Authority may narrow while a person is deciding. Keeping the approval on the record must never let stale policy, roots or credentials authorize the act)_
- D100 — **Authority is explicit and revisioned.** Principal, workspace, policy, registry, provider configuration, mode and their revisions/digests form the act's authority snapshot; live narrowing is re-read at the act _(A plan may be old and a conversation may be long-lived. The record must say both what the plan saw and what the host authorized when the effect happened)_
- D101 — **A controlled irreversible effect is a transaction:** `stage -> authorize -> execute -> reconcile` _(Judging once before invocation is insufficient across approval waits, crashes and network ambiguity. The transition order is the generic production boundary)_
- D102 — **An effect authorization is bound** to the staged-effect digest, run and step, principal, expected authority revision/digest, expiry and idempotency key, and is consumed once _(A grant must not be replayable for different inputs, a different user, a later policy or a duplicate delivery)_
- D103 — **Uncertainty is a first-class outcome.** Persist `executing` before invocation; finish with a receipt, refusal, failure or `unknown`; reconcile an unknown and never blindly retry a non-idempotent effect _(Exactly-once execution cannot be promised across a crash after the external system acted but before acknowledgement)_
- D104 — **The append-only run/effect journal is authoritative; mutable records and UI items are folds.** The HDK defines ports, schemas, contract suites and reference stores; a product chooses and operates its durable backend _(Recovery needs facts that cannot be overwritten. Product databases and vocabulary remain product-owned while the execution contract stays reusable)_
- D105 — **The HDK's event vocabulary remains generic.** Product activity labels, cloud job leases, intent/policy schemas, subscriptions and domain projections do not enter the kernel _(Intent Studio is evidence and the first consumer, not a reason to couple the kit to one product)_
- D106 — **Open standards meet Shadow at adapters.** MCP, A2A, AG-UI/A2UI-style UI protocols, CloudEvents, OpenTelemetry, OpenAPI/JSON Schema, OAuth/OIDC and OCI may cross external boundaries; none dictates the kernel's canonical model _(Standards evolve independently and describe different boundaries. Dependency inversion preserves interoperability without making the core a union of vendor schemas)_

## Scope

**In:**

- Kernel value types for capability evidence, provider capabilities, environment capabilities,
  execution requirements, mismatches and the total compatibility result
- Conservative defaults and one compatibility function; unknown is not false and never satisfies
  a strict requirement
- Measured capability records for the shipped Claude Code, Codex and OpenCode providers, plus the
  API-model seam; loader validation rejects contradictory or malformed records
- The existing `Isolation` proof exposed as environment capabilities, including the explicit fact
  that this macOS local environment does not confine reads or deny ambient secrets
- Requirement-aware selection at thread/harness construction; typed refusal before a provider or
  effectful environment is opened when the pair cannot meet the request
- Provider/capability discovery and requirement results over the wire and in the TypeScript client
- Contract suites, generated schemas, documentation and a migration note for consumers of 0.29.1

**Out:**

- `ModelAgent`, `Item.inputs`, reusable stream sessions, heartbeat and bearer input — Phase 32
- Authority revisions, effect authorizations, the effect journal and recovery — Phase 33
- Product-specific provider labels, workspace policy, cloud job leases or Intent Studio schemas
- New provider transports, stricter capabilities a provider cannot actually prove, or reading a
  person's configuration/credentials to manufacture evidence

## Deliverables

| Deliverable | Verification |
|---|---|
| Pure typed capability/requirement algebra with conservative defaults | kernel unit/property tests; JSON round-trip contracts |
| Provider capability records and loader validation | provider library tests plus one mutation per load-bearing field |
| Environment capability report derived from the existing proof | local/fake environment tests, including strict-read and secret-denial refusal |
| Requirement-aware in-process selection | provider/environment compatibility and harness/thread construction tests |
| Wire and TypeScript parity | schema drift invariant, wire integration tests and `tsc --noEmit` |
| Consumer documentation and capability matrix | document invariant and examples exercised by tests |

## Acceptance criteria

> Checkable. "It works" is not a criterion.

1. An omitted provider or environment capability is represented as unknown and fails a requirement
   that asks for it; it is never silently promoted to supported.
2. Capability values cannot express contradictory states such as both controlled and ungoverned
   tool execution; evidence says measured, derived, declared or unknown and carries a human-readable
   source without credentials.
3. Claude Code reports a closed governed tool path and resumable session; Codex reports its own MCP
   and native-tool limitations; OpenCode reports only what its ACP bridge and measured file prove.
4. `LocalEnvironment` reports confined writes, denied network and broad reads. A requirement for
   repository-only reads or denied ambient secrets refuses construction on this machine.
5. A host requiring a controlled tool path cannot accidentally select a provider with ungoverned
   native paths; the mismatch names the provider, axis, required value, available value and evidence.
6. A requirement accepted in-process is accepted over the wire, and a refusal has the same typed
   details in Python and TypeScript.
7. Existing callers that state no requirements retain 0.29.1 behavior; the migration note explains
   that this is compatibility, not a production safety claim.
8. The non-live quality gate is green and every new public type appears in generated schemas and the
   API export invariants.

## Run policy (inherited)

release: per-feature · push: per-phase · tdd: strict
