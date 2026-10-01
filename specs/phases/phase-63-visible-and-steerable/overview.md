---
type: Phase
status: in-progress
epic: inner-loop-primitives
tags: [plan, progress, steer, key-backed, components, lane-p]
deps: [phase-62-what-a-run-carries]
---

# Phase 63 — the loop is visible and steerable

## Goal

Lane P's asks 8 and 9, both P2 and both small. A host can show *"step 2 of 5"* from the agent's own
narration, and a key-backed model's turn can be steered midway as a resident CLI's already can.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D171 | **The plan is a registered component with no effects at all, not a runtime concept** | the mechanism is the kit's and the plan's *content* is the product's — lane P's words and ours. A component with an empty `EffectProfile` is admitted by every mode including `read-only`, which is what a narration needs: an agent that had to ask permission to say what it intends would stop saying it. And the record carries the revisions in order for free, because `Invoked.inputs` already does |
| D172 | **An item's `status` is an open string, not an enumeration** | the same cut `Provider.transport` and `injects_tools` make. A `Literal` would mean the kit's contract changes every time a product wants a status it did not think of, and a plan's vocabulary is exactly the kind of thing a product owns |
| D173 | **A steer is delivered between steps, as a message, and `steer` still answers `bool`** | the loop between steps is the kit's own, which is why this is the one place `ModelAgent.steer` could be true. Delivered as a user message before the next model call rather than injected into the running request, because a request already in flight cannot be changed and pretending otherwise would make the `bool` a lie. A turn that has already ended still answers `False`, exactly as a one-shot CLI does |

## Boundary and acceptance

**In:** a plan component and its registration; `steer` working for a key-backed model.

**Out:** the *content* of a plan — what the steps are, what a status means, how it renders (D171/D172).
Steering a one-shot CLI, which has no open stdin and honestly answers `False`. Changing a model
request already in flight.

**Unchanged:** `Composed`, `PlanAdmitted`/`PlanRefused` and `items()` — the runtime's own half of a
plan, which already exists and which lane P said they would read first. A resident CLI's `steer`
behaves exactly as it does. Contract additions, so a minor and a *Pins* row.

## Groups

| | What | Asks |
|---|---|---|
| G1 | the agent's own plan, on the record, admitted by every mode | 8 |
| G2 | a key-backed model's turn is steerable | 9 |
| G3 | the migration note, the version, the gate | — |

## Verification

TDD strict, every assertion mutation-checked. The property that matters for G2 is that a steer
**reaches the model** — asserted against what the model was actually asked, not against `steer`'s
return value, because returning `True` is the easy half.
