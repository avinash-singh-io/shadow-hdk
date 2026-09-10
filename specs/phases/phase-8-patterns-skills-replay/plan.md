---
type: Plan
phase: 8-patterns-skills-replay
---

# Phase 8 — plan

```
# Sequential:  Group 0 → 1 → 2 → 3 → 4
# Each group is a claim that can fail on its own, so each has its own gate and commit.
```

## Group 0 — patterns are files

- `patterns/*.toml`: `single`, `plan-and-execute`, `orchestrator-workers`, `critic-pair`,
  `reflect-until`
- `load_pattern(path) -> Pattern`, `shipped() -> dict[str, Pattern]`
- The loader validates: unknown meta-tools refused by name, unknown keys refused, a missing
  required key refused — a pattern file is data a team edits, so its errors are for a person
- RED: each shipped pattern loads; a team's file loads by the same call; each kind of bad file is
  refused with the name of what is wrong

**Commit:** `feat(adapters): a pattern is a file, and a team writes one the same way we do`

## Group 1 — skills, checked before the first turn

- `Skill(name, prompt, needs)` and `load_skill(path)`
- `check(skill, visible) -> Missing | None` — what the deployment does not offer
- RED: a skill whose components are all visible starts; one that needs a hidden component is
  refused **before any turn**, naming what is missing; a narrowing mode is what hides it

**Commit:** `feat(adapters): a skill says what it needs, and is told no before it starts`

## Group 2 — the catalogue: `describe` (D13)

- Above a threshold (default 30, a setting) the catalogue the model is offered is names and
  one-line descriptions
- `describe(name)` returns the full interface for one component
- Below the threshold nothing changes — the whole schema, as today
- RED: at 29 the schemas are there; at 31 they are not and `describe` brings one back; `describe`
  on a component the policy hides is refused, not answered

**Commit:** `feat(adapters): a big catalogue is names until the model asks for more`

## Group 3 — the recorded model port

- `RecordedModel(inner, tape)` — records `(prompt fingerprint) -> response` on the way through
- Replaying from a tape makes no model call; a fingerprint that is not on the tape is a **miss**
  that says so rather than silently calling the model
- RED: a recorded run replays with the inner port removed; a changed prompt is a miss

**Commit:** `feat(runtime): a run that can be replayed for nothing`

## Group 4 — compaction, and the model's verbs

- `compaction` as a **component** (`09` §5): it proposes a summary of the transcript, and the
  **sink** decides whether it is kept
- `spawn` / `send` / `release` meta-tools, with the `held-helper` pattern that shapes the child:
  a brief, then a wait on `Mailbox.NAME` — Phase 7's deferral, landing where the shape belongs
- RED: a compaction reaches the sink as a proposal and is never written by the runtime; the verbs
  are offered by the pattern and unknown to the runtime
- records, board, status

**Commit:** `feat(adapters): a model that can summarise itself, and keep a helper`
