---
type: Phase
status: in-progress
tags: [behaviour, honesty, model-port, conversation, timeout, agents, lane-p, audit]
deps: [phase-64-an-agent-is-data]
---

# Phase 65 — the claims are true

> **Phase numbering collides with `shadow`.** This repository's 59–65 and `shadow`'s 59–65 are
> different work that happens to share numbers. Nothing here refers to a `shadow` phase by number
> without saying so.

## Goal

Lane P's audit of 2026-10-02 lists forty items. Eight of them (its A-group) are not requests for new
capability — they are **claims this kit already makes that are not true**. Five were confirmed
against the source before this phase opened, and **three of the five originate in my own phases 62
and 64**. That is the whole scope. Nothing else from the audit is in it.

A missing capability costs a product a workaround. A false claim costs it a wrong decision — lane P
planned against `unmapped_behaviour` believing it, and it was lying in two places.

## What was confirmed, and where

| | claim | what the source does | confirmed at |
|---|---|---|---|
| H1 | `tools_offered` narrows what a model is shown, "so it is honoured elsewhere" | parsed into `Behaviour`; skipped as a launch flag with the comment *offered-set narrowing is the registry's*; `catalogue()` narrows by the **pattern** and the ceiling and **never reads it**. Counted as delivered in `unmapped_behaviour` *and* in `unmapped_for_a_model` | `kernel/providers.py:377,438` · `adapters/jsonl/transport.py:95` · `adapters/agent/component.py:327` |
| H2 | a mode's `model` reaches a key-backed model (`ModelRequest.model`, phase 62) | the field is set on the request. `LangChainModel._bind` reads `request.tools` and nothing else; the chat model is fixed at construction, so `request.model` is **discarded by the only adapter that implements the port** | `adapters/langchain/model.py:101` |
| H3 | — (never claimed; the gap is that nothing says it) | `work()` opens with `self.messages = [system, user]` — a fresh conversation every turn. Seeding happens only after a fork or a rollback. A product's second turn on a key-backed thread has no first turn in it, and no document says so | `adapters/agent/component.py:182` |
| H4 | — | one `asyncio.timeout(600)` around the whole wait, person included | `adapters/jsonl/session.py:32,174` |
| H5 | an agent is selected per mode (D175) and readable on the thread (D177) | `set_mode` replaces policy, environment and behaviour and **never re-resolves the agent**; `ThreadRecord` has no `agent`, so a resumed thread falls back to the host default. Phase 64 shipped selection without persistence | `runtime/threads.py:684` · phase 64 |

H37 (Codex instructions measured end to end) stays blocked on an account where Codex accepts a
model; this phase makes the two skipped tests say exactly what is needed rather than merely skip.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D178 | **`tools_offered` narrows, in the one place a catalogue is built** — and it narrows by the name a model is shown, after the pattern and the ceiling have had their say | the alternative is to delete the field and say so. But a mode that may name *who the model is* and *what it may do* and not *which of the run's tools this step needs* is missing the cheapest context control there is. Narrowing last means it can only ever take away, so no mode can widen past its policy |
| D179 | **A name in `tools_offered` that no registration answers to is refused at open, naming it** | the D176 cut, again. A typo that silently offers everything is the failure this phase exists to stop |
| D180 | **`ModelPort` gains no field; `request.model` is honoured by the adapter that can** — `LangChainModel` re-binds per request where the asked-for model differs from the constructed one, and names it in `unmapped_for_a_model` where it cannot | the kernel already carries the field; nothing in the contract needs to change. An adapter over a chat model constructed for one spec cannot always become another, so the honest answer is *re-bind where possible, name it where not* |
| D181 | **A key-backed conversation remembers its turns**, and the transcript is the thread's, not the turn's | the current behaviour is not a documented limitation a product could work around — `unmapped_behaviour` says nothing, the docs say nothing, and a product has no way to tell a forgetful thread from a forgetful model. Seeding already exists for fork and rollback; this is the same seeding on the ordinary path |
| D182 | **Time spent waiting for a person is not the provider's time.** The ceiling applies to the provider's own silence; a parked turn's clock stops | 600s was chosen for a CLI that answers by itself. A turn parked on `ask_person` is waiting for a human being, and failing it at ten minutes with *the provider did not finish* is both a wrong diagnosis and a wrong cut |
| D183 | **A resolved agent is on the record**, so a mode switch re-resolves it and a resume restores it | phase 64 made an agent selectable and then let it evaporate at the first `set_mode`. A selection that does not survive the doors a product actually uses is not a selection |

## Boundary and acceptance

**In:** the five confirmed claims, made true; H37's skips made explicit about what they need; the
honesty fields (`unmapped_behaviour`, `unmapped_for_a_model`) corrected in the same change as the
behaviour they describe.

**Out:** everything else in the forty-item audit. Named so no later reader thinks it was missed:
H10, H11, H12, H13, H14, H16, H20, H21, H22, H24, H28, H29, H30, H39 and the rest are **not in this
phase and not deferred into it** — the user's decision of 2026-10-02 was Wave 1 only, on the ground
that the native line should carry new capability rather than this one.

**Unchanged:** a mode naming no `tools_offered` is offered everything, exactly as today. A thread
whose mode names no agent still runs `single`. No protocol change; contract additions only, so a
minor and a *Pins* row.

## Groups

| | What |
|---|---|
| G1 | `tools_offered` narrows, and an unknown name refuses (D178, D179) |
| G2 | a key-backed model honours the mode's `model`, or says it cannot (D180) |
| G3 | a key-backed conversation remembers its turns (D181) |
| G4 | a person's thinking time is not the provider's ceiling (D182) |
| G5 | a resolved agent survives a mode switch and a resume (D183) |
| G6 | H37's skips say what they need; the migration note, the version, the gate |

## Verification

TDD strict, every assertion mutation-checked, mindful of TD-019 — logic that would need a
`ServeHost` to fail is extracted into a pure function and checked there, with the host test kept as
behavioural coverage.

Four properties this phase owes beyond the gate:

- **A narrowed mode actually narrows.** Not that the field parses — that the catalogue a model is
  handed is shorter, asserted against what the model was asked.
- **The honesty fields and the behaviour move together.** A test that fails if either side is
  corrected alone, because the lie this phase closes was precisely the two disagreeing.
- **A second turn contains the first.** Asserted against what the model was asked, not against a
  field.
- **Nothing that works today changes.** A mode naming nothing is offered everything; a thread with
  no agent still runs `single`.
