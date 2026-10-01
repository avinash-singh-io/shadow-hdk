---
type: Phase
status: in-progress
epic: inner-loop-primitives
tags: [agents, patterns, store, modes, wire, plugin-boundary, docs, lane-p]
deps: [phase-63-visible-and-steerable]
---

# Phase 64 — an agent is data, like everything else

## Goal

Close the last asymmetry in lane P's §3 boundary. Everything a plugin is made of can live in the
product's database and be read by the kit — **except its agents.**

| | store source | `*/list` | selectable per run |
|---|---|---|---|
| skills · modes · rules · batteries · providers · component switches | ✅ | ✅ | ✅ (via the mode) |
| **agents (`Pattern`)** | ❌ | ❌ | ❌ |

A plugin whose Build agent, Reviewer, Test fixer and Release writer cannot be stored or selected is
not a plugin; it is one hardcoded role. That is the gap.

## What this phase found while planning, and must say out loud

**Full CRUD on every other plugin concept already works and is documented nowhere.** The wire
carries `store/put`, `store/get`, `store/delete`, `store/list` and `store/version` with no
collection allow-list, so a product already creates, updates, lists and deletes its own skills,
modes, rules, batteries and providers through the kit's own door. Lane P asked for exactly this
capability without knowing it was there — which is a documentation failure of ours, and the reason
ENH-026 is in this phase rather than deferred again.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D174 | **An agent is a store row like a skill is**: `StorePatterns` over an `agents` collection, reloaded when the collection's version moves | every other concept works this way and `pattern_from(data, where=)` already exists, so the data constructor is done. A seventh concept with a seventh mechanism would be the asymmetry this phase exists to remove |
| D175 | **A mode names its agent.** `ModeSpec.pattern` is the primary selector, with `thread/start {agent}` as the per-thread override | a mode already carries *who the model should be* (`behaviour`, D64) and *what it may do* (policy, plan limits). Which loop runs it is the same kind of fact, and putting it on the mode means a product switches agent with `set_mode` — a door that already exists and is already governed — rather than a new one |
| D176 | **An unknown agent name is refused at open, naming it** — never silently `single` | falling back to a default would give a product a run that looks right and is not, which is the failure `Dialect` refuses for an unknown transport and `ModeRegistry` refuses for an unknown mode id. Same cut |
| D177 | **The resolved agent is readable on the thread**, beside `unmapped_behaviour` | lane P carries a resolved snapshot (agent, instructions, skills, version, hash) so a person's machine can cache by hash. They cannot build it if the kit will not say which agent a run resolved to |

## Boundary and acceptance

**In:** `StorePatterns`; `ModeSpec.pattern`; `thread/start {agent}`; `agents/list`; the resolved
agent on the thread's own description; TD-017 decided and applied; `docs/for-a-product.md` current.

**Out:** authoring UI, plugin format, or any notion of a "plugin" in the kit (the boundary rule
stands — this is a `Pattern` row, not a plugin). Changing what a `Pattern` *is*. Agent inheritance
or composition — a product that wants a Reviewer built from a Base writes both rows.

**Unchanged:** `single` stays the default where nothing names an agent, so every existing
composition behaves exactly as it does. `load_pattern` and the packaged `library/` keep working —
a store source is an addition, not a replacement. Protocol 3 unchanged; contract additions, so a
minor and a *Pins* row.

## Groups

| | What |
|---|---|
| G1 | an agent is a store row (D174) |
| G2 | a mode names its agent, and a thread may override it (D175, D176) |
| G3 | `agents/list`, and the resolved agent on the thread (D177) |
| G4 | TD-017 decided; `docs/for-a-product.md` current, with the store-CRUD surface it has never described |
| G5 | the migration note, the version, the gate |

## Verification

TDD strict, every assertion mutation-checked. Three properties this phase owes beyond the gate:

- **A product's own agent actually runs.** Not that the row parses — that a thread opened on a
  store-backed agent uses *that* pattern's system prompt, asserted against what the model was asked.
- **An unknown name refuses rather than falling back** (D176), because a silent default is the
  failure mode worth a test.
- **Nothing that works today changes.** A composition naming no agent still gets `single`, asserted
  rather than assumed.
