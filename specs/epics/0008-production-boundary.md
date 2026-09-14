---
type: Epic
id: "0008"
slug: production-boundary
status: in-progress
owner: Avinash
started: "2026-09-14T18:44:36.704Z"
phases: [phase-31-a-host-knows-what-it-can-trust, phase-32-one-agent-surface, phase-33-authority-at-the-act]
policy_release: per-feature
policy_push: per-phase
policy_tdd: strict
---

# Epic 0008 — production-boundary

## Objective

A product can select only providers and environments that prove its requirements, consume CLI and model agents through one durable host surface, and execute controlled irreversible effects against current authority with crash-safe recovery.

## Decisions

> Settled once; never re-asked. Per-phase specs are derived from this table.

| # | Decision | Rationale |
|---|---|---|
| D95 | **One umbrella, two surfaces:** Shadow HDK is the construction kit; Shadow Harness is the ready-to-run reference assembly built only from the HDK's public contracts | A product can begin with defaults and progressively replace them without crossing into another runtime, repository or private API |
| D96 | **Capability, requirement and evidence are different types.** Providers and environments report what they can do and how it was established; a host states what it requires; an unknown never satisfies a production requirement | A boolean feature bag can contradict itself and silently turn missing evidence into permission. Compatibility must be computed and a mismatch must be data |
| D97 | **Provider truth, environment truth and execution authority stay separate.** A provider owns either inference or an agent loop; an environment proves containment; the host owns permission to act | A strict provider cannot compensate for an unconfined environment, and a sandbox cannot turn a provider's ungoverned native tools into controlled effects |
| D98 | **One durable agent surface for both provider kinds.** A `ModelPort` is adapted behind `AgentPort`; `Thread` remains the product-facing conversation lifecycle | A product must not build a second runner to get API-backed models, and changing provider kind must not discard holding, parking, spend, cancellation or recovery |
| D99 | **Approval is evidence of consent, not executable authority.** The host issues a separate, single-use effect authorization immediately before an irreversible act | Authority may narrow while a person is deciding. Keeping the approval on the record must never let stale policy, roots or credentials authorize the act |
| D100 | **Authority is explicit and revisioned.** Principal, workspace, policy, registry, provider configuration, mode and their revisions/digests form the act's authority snapshot; live narrowing is re-read at the act | A plan may be old and a conversation may be long-lived. The record must say both what the plan saw and what the host authorized when the effect happened |
| D101 | **A controlled irreversible effect is a transaction:** `stage -> authorize -> execute -> reconcile` | Judging once before invocation is insufficient across approval waits, crashes and network ambiguity. The transition order is the generic production boundary |
| D102 | **An effect authorization is bound** to the staged-effect digest, run and step, principal, expected authority revision/digest, expiry and idempotency key, and is consumed once | A grant must not be replayable for different inputs, a different user, a later policy or a duplicate delivery |
| D103 | **Uncertainty is a first-class outcome.** Persist `executing` before invocation; finish with a receipt, refusal, failure or `unknown`; reconcile an unknown and never blindly retry a non-idempotent effect | Exactly-once execution cannot be promised across a crash after the external system acted but before acknowledgement |
| D104 | **The append-only run/effect journal is authoritative; mutable records and UI items are folds.** The HDK defines ports, schemas, contract suites and reference stores; a product chooses and operates its durable backend | Recovery needs facts that cannot be overwritten. Product databases and vocabulary remain product-owned while the execution contract stays reusable |
| D105 | **The HDK's event vocabulary remains generic.** Product activity labels, cloud job leases, intent/policy schemas, subscriptions and domain projections do not enter the kernel | Intent Studio is evidence and the first consumer, not a reason to couple the kit to one product |
| D106 | **Open standards meet Shadow at adapters.** MCP, A2A, AG-UI/A2UI-style UI protocols, CloudEvents, OpenTelemetry, OpenAPI/JSON Schema, OAuth/OIDC and OCI may cross external boundaries; none dictates the kernel's canonical model | Standards evolve independently and describe different boundaries. Dependency inversion preserves interoperability without making the core a union of vendor schemas |

## Phases

| Phase | Builds | Depends on |
|---|---|---|
| 31 — a host knows what it can trust | Typed provider/environment capabilities and evidence; typed execution requirements; conservative compatibility/refusal; the same report in-process and over the wire | 30 |
| 32 — one agent surface | `ModelAgent` over `ModelPort`; model- and CLI-backed `Thread` parity; `Item.inputs`; the reusable stream session, heartbeat and safer bearer input | 31 |
| 33 — authority at the act | Revisioned authority snapshots; staged effects and single-use authorizations; act-time recheck; the durable journal, receipts, unknown outcomes and reconciliation | 31 |

Phases 32 and 33 are independent after Phase 31. The epic releases once, after both are complete.

## Completion criteria

> Checkable. "It works" is not a criterion.

- [x] A host submits typed execution requirements and receives either a compatible provider/environment selection or a typed mismatch naming every unmet or unknown requirement
- [x] Claude Code, Codex, OpenCode and API-model fixtures expose measured capability records; an omitted fact has the conservative value and cannot satisfy a strict requirement
- [x] `LocalEnvironment` reports write confinement and network denial without claiming read confinement; asking it for repository-only reads or secret denial refuses construction
- [ ] Model-backed and CLI-backed agents both run through `Thread` with the same turn, parking, holding, spend, cancellation, resume and activity contracts
- [ ] A folded `Item` carries the invoked inputs through the Python and TypeScript surfaces, subject to the existing payload/offloading policy
- [ ] The reusable stream session proves frame ids, bounded replay, heartbeat, silence detection and reattachment in-process and through `serve`
- [ ] An approval followed by a narrowed policy, workspace, registry, provider configuration or credential revision is refused before execution while the approval remains on the record
- [ ] A child run receives the same or narrower effective authority and cannot reuse its parent's effect authorization
- [ ] A crash before external execution leaves no act; a crash after possible execution but before acknowledgement leaves `unknown`; recovery reconciles it without blind retry
- [ ] Duplicate delivery of one staged effect produces at most one authorized execution for an idempotent adapter and an explicit refusal/unknown for a non-idempotent one
- [ ] A provider session resumes after a process restart as the same logical run and does not repeat an effect already carrying a receipt
- [ ] `controlled` on an irreversible effect means the runtime can show the act-time authorization and receipt/unknown record; otherwise its posture is `observed` or the act is refused
- [ ] The public Python contracts, JSON Schemas, wire methods and TypeScript types round-trip and pass their contract suites
- [ ] The full non-live gate is green: ruff check, format check, mypy strict, pytest, document invariants and the benchmark
- [ ] The release notes state the capability matrix and known provider/environment limitations; one `v0.30.0` release is published only after Phases 31–33 are complete

## Non-goals

- Intent Studio endpoints, cloud queues, job-ownership leases, subscriptions, domain schemas, product activity vocabulary, frontend state and cloud persistence
- A claim that macOS Seatbelt provides repository-only reads or secret isolation
- Reimplementing a subscription provider's private agent loop or pretending it is a `ModelPort`
- Exactly-once effects across an arbitrary external system; the promise is idempotency where available and explicit uncertainty everywhere else
- Dynamic planning, context engineering, scheduling, generative UI and agent-to-agent collaboration; they remain later roadmap capabilities
- Splitting Shadow HDK and Shadow Harness into separate kernels, packages or repositories in this epic

## Run policy

`per-feature`, `tdd: strict`: each phase has its own RED/green evidence, commits and review
checkpoint, but there is one merge and one `v0.30.0` release when the whole boundary is coherent.
The owner understands that the final landing approval covers the accumulated three-phase diff;
verification evidence is produced at every phase boundary rather than deferred to the end.

## Amendments

> Operator changes made during the run land here, newest last, and become
> inputs to the derivation of every not-yet-started phase.

_(none yet)_
