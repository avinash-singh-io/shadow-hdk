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

- [x] G2.1 `LangChainModel` re-binds where the request names a model that differs, caching one chat model per spec
- [x] G2.2 where it cannot — the `over()` seam — `unmapped_for_a_model` names `model`, asked of the port rather than assumed
- [x] G2.3 a request naming nothing, or naming what was constructed, builds nothing new

## G3 — a key-backed conversation remembers its turns (D181) · BUG-232

- [x] G3.1 the transcript lives on the session that outlives the per-turn loop, and is carried over a provider reopen the way a session id is
- [x] G3.2 a second turn contains the first, and a third both — asserted against what the model was asked, in order
- [x] G3.3 a first turn is exactly the role and the prompt; one system message however many turns; a mode switch replaces the role and keeps the words

## G4 — a person's thinking time is not the provider's ceiling (D182) · BUG-233

- [x] G4.1 the ceiling measures the provider's **silence**, not the turn; a mode sets it through `Behaviour.silence_seconds`; the default is 1800s of silence, not 600s of work
- [x] G4.2 time the kit spends answering the provider's own call — a person's approval included — is given back to its patience
- [x] G4.3 a hung provider still fails, and the words say *said nothing for Ns* rather than *did not finish*

## G5 — a resolved agent survives a mode switch and a resume (D183) · BUG-234

- [x] G5.1 the resolved agent is on `ThreadRecord`, and `Thread.agent` reads off the record so there is one answer
- [x] G5.2 `set_mode` re-resolves it through a chooser the host hands in; an unknown name on the new mode refuses, naming it
- [x] G5.3 a resumed thread runs the agent its record says it was running
- [x] G5.4 a host-handed agent still wins; a thread's override survives a switch **and** a resume — `agent_override` is on the record too, found by a surviving mutation

## G6 — the skips, the note, the version, the gate · TD-020

- [x] G6.1 the two Codex skips name the account needed, what the measurement would prove, and TD-020 — and the two Claude Code legs were run live and passed
- [x] G6.2 `docs/migrations/0.44.md`
- [x] G6.3 version 0.44.0 in all four places, changelog, status headline (which still said 0.42.0 — lane P was right), the five backlog rows closed, history, retrospective
- [x] G6.4 ruff, format, mypy strict and pytest all green, each exit code read directly from a file rather than through a pipe


All six groups complete. `/sync-docs` then `/complete-phase` next (Rule 9).
