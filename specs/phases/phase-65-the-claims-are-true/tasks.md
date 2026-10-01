---
type: Tasks
phase: phase-65-the-claims-are-true
---

# Phase 65 tasks

## G1 — `tools_offered` narrows, and an unknown name refuses (D178, D179) · BUG-230

- [x] G1.1 the narrowing is a pure function over names, so it is mutation-checkable without a host
- [x] G1.2 `catalogue()` narrows by it, after the pattern and the ceiling — **and so does the list the registry serves a CLI**, which is where a CLI's catalogue actually comes from
- [x] G1.3 a name no registration answers to is refused, naming it and saying what there is
- [x] G1.4 both honesty fields are true now — and the `| {"tools_offered"}` union in `unmapped_behaviour` turned out to be **dead code**, found by a surviving mutation
- [x] G1.5 a mode naming nothing is offered everything — asserted, not assumed

## G2 — a key-backed model honours the mode's `model` (D180) · BUG-231

- [ ] G2.1 `LangChainModel` re-binds where the request names a model that differs
- [ ] G2.2 where it cannot, `unmapped_for_a_model` names `model`
- [ ] G2.3 a request naming nothing is byte-for-byte the request it always was

## G3 — a key-backed conversation remembers its turns (D181) · BUG-232

- [ ] G3.1 the transcript seeding is one derivation, used by the ordinary path and by fork alike
- [ ] G3.2 a second turn contains the first, asserted against what the model was asked
- [ ] G3.3 a first turn is unchanged

## G4 — a person's thinking time is not the provider's ceiling (D182) · BUG-233

- [ ] G4.1 the ceiling is a mode's to set, with a default that is not ten minutes
- [ ] G4.2 a turn parked on a person does not count that time
- [ ] G4.3 a provider that genuinely goes silent still fails, saying so

## G5 — a resolved agent survives a mode switch and a resume (D183) · BUG-234

- [ ] G5.1 the resolved agent is on `ThreadRecord`
- [ ] G5.2 `set_mode` re-resolves it; an unknown name on the new mode refuses
- [ ] G5.3 a resumed thread runs the agent it was running
- [ ] G5.4 a host-handed agent still wins, and a thread override survives a switch

## G6 — the skips, the note, the version, the gate · TD-020

- [ ] G6.1 each skipped live test says what account it needs and what it would prove
- [ ] G6.2 the release's migration note, under `docs/migrations/`
- [ ] G6.3 version, changelog, status, history, retrospective with verification evidence
- [ ] G6.4 the full gate green, with the output read
