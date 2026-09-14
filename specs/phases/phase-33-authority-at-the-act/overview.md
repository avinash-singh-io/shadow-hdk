---
type: Phase
status: in-progress
epic: production-boundary
tags: [authority, authorization, effects, journal, recovery, receipts, idempotency]
deps: [phase-31-a-host-knows-what-it-can-trust]
---

# Phase 33 — Authority at the act

> **Derived, not brainstormed.**
> Generated from `specs/epics/0008-production-boundary.md` on 2026-09-15 with no
> operator interview (Epic D10). Every decision below was settled when the
> epic was written and is NOT re-litigated here. Decisions are durable;
> plans are perishable — this file is the perishable half.

## Goal

A controlled irreversible effect is no longer trusted because an earlier judgement or approval
once allowed it. Shadow stages the exact effect, asks the host for a single-use authorization bound
to current revisioned authority, persists `executing` immediately before the component boundary,
and reconciles the attempt to a receipt, refusal, failure or explicit unknown. The append-only
journal is the source of truth; mutable thread records, events and UI items are projections. A
crash may leave uncertainty, but it cannot silently turn stale consent into authority or cause a
blind non-idempotent retry.

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

- Canonical, secret-free `AuthoritySnapshot` data covering principal, workspace, policy, registry,
  provider configuration, mode and their revisions/digests
- Canonical staged-effect digest and a single-use authorization bound to run, step, principal,
  authority revision/digest, expiry and idempotency key
- Host ports for reading current authority, authorizing one staged effect and appending/reading its
  journal; no host policy moves into the runtime
- The enforced state order `stage -> authorize -> execute -> reconcile` for controlled irreversible
  component invocations, including a fresh authority read immediately before execution
- Append-only journal entries and folds to receipt, refusal, failure or `unknown`; compare-and-append
  semantics sufficient for duplicate delivery and concurrent recovery
- In-memory and shipped durable reference implementations plus contract suites a product runs
  against its own backend
- Recovery/reconciliation that reuses a receipt or adapter result where idempotency exists and never
  blindly retries an uncertain non-idempotent act
- Child-authority narrowing and non-transferable authorizations
- Python, schema, wire, TypeScript, telemetry and migration surfaces for the generic transaction

**Out:**

- Product permission models, credential values, job leases, tenancy, domain receipts or UI labels
- Exactly-once claims about an arbitrary external system
- A global transaction spanning the host database and an unrelated external service
- Scheduler retry policy, dynamic planning and remote-agent delegation
- Treating approval as authorization, or treating a provider/environment capability as permission

## Deliverables

| Deliverable | Verification |
|---|---|
| Authority snapshot, staged effect, authorization and journal entry contracts | canonical digest/property tests; JSON round trips; mutation checks |
| Authority/authorizer/journal ports and product contract suites | fake host plus in-memory, SQLite/Postgres/reference adapter contract runs |
| Controlled irreversible transaction in the governed step | transition-order tests; stale revision and replay refusal; no-invoke assertions |
| Crash-safe outcomes and reconciliation | injected crash at every boundary; duplicate/concurrent recovery tests |
| Child narrowing and grant isolation | parent/child authority property tests and cross-run replay attacks |
| Public record and migration | wire/schema/TypeScript parity; telemetry; document and benchmark gates |

## Acceptance criteria

> Checkable. "It works" is not a criterion.

1. The authority snapshot is canonical and digestible without containing a credential or policy
   payload; changing any governed revision changes its digest.
2. The staged-effect digest binds component identity, exact canonical inputs, declared effects,
   run and step. A grant for any different value is unusable.
3. Approval remains consent evidence on the record. A separate host authorization is requested
   only for the staged controlled irreversible effect and is consumed at most once.
4. Immediately before the component boundary, Shadow reads current authority. Any principal,
   workspace, policy, registry, provider-configuration or mode revision/digest mismatch refuses the
   act while preserving the earlier approval.
5. Journal order is append-only and mechanically valid: staged precedes authorized, authorized
   precedes executing, and executing ends in exactly one receipt, refusal, failure or unknown fold.
6. `executing` is durable before component invocation. A crash before it proves no act was sent; a
   crash after it without an outcome becomes `unknown`, never assumed failed or successful.
7. Duplicate delivery/concurrent recovery cannot consume one grant twice. An idempotent adapter
   reuses its key/result; an uncertain non-idempotent adapter is not invoked again automatically.
8. A child receives the same or narrower authority and cannot consume or replay its parent's grant;
   run and step binding is enforced, not conventional.
9. `controlled` on an irreversible effect means the journal can show current authorization and its
   receipt/unknown outcome. A path that cannot participate is reported `observed` or refused.
10. A provider/thread resume after process restart folds the same journal and does not repeat an
    effect already carrying a terminal receipt.
11. Journal contract suites pass against every shipped reference store and can be imported by a
    product testing its own durable implementation.
12. Public Python, JSON Schema, protocol and TypeScript representations round-trip, and the full
    combined Epic 0008 non-live gate is green before v0.30.0 is proposed for landing.

## Run policy (inherited)

release: per-feature · push: per-phase · tdd: strict
