---
type: Phase
status: in-progress
epic: production-boundary
tags: [agent-port, model-port, thread, items, streaming, heartbeat, authentication]
deps: [phase-31-a-host-knows-what-it-can-trust]
---

# Phase 32 — One agent surface

> **Derived, not brainstormed.**
> Generated from `specs/epics/0008-production-boundary.md` on 2026-09-15 with no
> operator interview (Epic D10). Every decision below was settled when the
> epic was written and is NOT re-litigated here. Decisions are durable;
> plans are perishable — this file is the perishable half.

## Goal

A product opens one durable `Thread` whether its reasoning comes from an API-backed `ModelPort` or
a subscription-backed CLI `AgentPort`. The adapter difference stays below the host lifecycle:
turns, tool offers, parking, spend, cancellation, resume and activity remain one contract. The
same phase closes the item-projection input gap and extracts the stream-session behavior already
proven by HTTP so in-process hosts and wire clients share replay, heartbeat and silence semantics.

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

- A first-party `ModelAgent` implementing `AgentPort` over any `ModelPort`, using the existing
  agent pattern/tool loop rather than adding a second thread runner
- Provider construction that chooses model-backed or CLI-backed agency below `Thread`, retaining
  Phase 31 capability selection and evidence on either path
- `Item.inputs` from the existing `Invoked` event through Python, JSON Schema, wire and generated
  TypeScript surfaces, under one bounded/redacted projection rule
- A reusable in-process stream-session abstraction: monotone frame ids, bounded outbox, one active
  attachment, grace period, replay after a cursor and explicit expiry
- `serve` rewritten to consume that abstraction, plus heartbeat frames and client silence/reattach
  behavior that never changes the durable run record
- Bearer input by environment variable or permission-checked token file; the command-line flag
  remains an explicitly local-development convenience with documented precedence
- Contract tests proving model and CLI agents share the product-facing lifecycle

**Out:**

- Authority revisions, effect grants, act-time rechecks, the effect journal and reconciliation —
  Phase 33
- Presets, blueprints and progressive `HarnessSpec` materialization — Phase 34
- Product authentication, tenancy, frontend state, message schema or domain activity vocabulary
- Replacing provider SDKs, provider loops, SSE/JSON-RPC or the host's durable store
- Dynamic planning, scheduling, generative UI and peer-agent protocols

## Deliverables

| Deliverable | Verification |
|---|---|
| `ModelAgent` over `ModelPort`, exposed through the same construction path as CLI agents | agent-port contract; scripted model/tool/activity/usage tests; `Thread` parity scenarios |
| `Item.inputs` on every public projection | fold unit tests; JSON round trip; wire and generated TypeScript drift tests |
| Reusable bounded stream session consumed by `serve` | in-process lifecycle/property tests; existing reconnect integration rewritten against it |
| Heartbeat, silence detection and reattachment | deterministic-clock session tests; live HTTP integration without sleeps where controllable |
| Safer bearer sources | precedence, permissions, redaction and subprocess argv tests |
| Migration and capability documentation | document invariant; examples and generated client compile |

## Acceptance criteria

> Checkable. "It works" is not a criterion.

1. A caller can hand a `ModelPort` and open a `Thread`; no product-owned runner or alternate
   conversation record is needed.
2. Model-backed and CLI-backed scripted providers pass the same tests for turn, park/settle, hold,
   spend, cancellation, resume and activity ordering.
3. `ModelAgent` exposes only the `ToolSource` it is handed, routes every tool call through it, and
   reports the model's usage/activity without manufacturing unknown values.
4. Phase 31 selection remains truthful for both provider kinds: an API-model record and its
   evidence are checked before its session opens, exactly as for a CLI agent.
5. Every folded item created from `Invoked` retains the canonical JSON inputs in Python and across
   protocol/schema/TypeScript boundaries; over-limit or sensitive payload handling is one explicit
   rule rather than client-specific truncation.
6. A stream session assigns strictly monotone ids, keeps a bounded replay window, permits one live
   attachment, replays only frames after a supplied cursor and expires after its grace period.
7. The HTTP/SSE server uses the reusable session rather than retaining a private implementation;
   existing D94 reconnect behavior remains green.
8. Heartbeats make a silent connection observable without adding events/items to the durable
   record, and a client that crosses its silence deadline reattaches using the last frame id.
9. A production bearer can be supplied without appearing in process arguments. Ambiguous or
   insecure token-file input is refused by name, and no error/log includes the bearer value.
10. Existing 0.29.1 CLI-backed callers preserve behavior when they do not opt into new model or
    stream APIs; the full non-live gate and generated-client compile are green.

## Run policy (inherited)

release: per-feature · push: per-phase · tdd: strict
