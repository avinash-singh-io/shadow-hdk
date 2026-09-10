---
type: Tasks
phase: 8-patterns-skills-replay
---

# Phase 8 — tasks

## Group 0 — patterns are files

- [ ] the TOML format, and `load_pattern(path)`
- [ ] `shipped()` over the packaged `patterns/` directory
- [ ] the five pattern files
- [ ] the loader refuses an unknown meta-tool, an unknown key, a missing key — each by name
- [ ] RED: each of the above
- [ ] Gate

## Group 1 — skills, checked before the first turn

- [ ] `Skill(name, prompt, needs)` and `load_skill(path)`
- [ ] `check(skill, visible)` → what is missing
- [ ] RED: a skill whose needs are visible is allowed
- [ ] RED: a skill needing a hidden component is refused before any turn, naming what is missing
- [ ] Gate

## Group 2 — the catalogue: `describe` (D13)

- [ ] the threshold, as a setting with a default of 30
- [ ] above it: names and one-line descriptions only
- [ ] `describe(name)` → the full interface
- [ ] `describe` on a component the policy hides is refused
- [ ] RED: each of the above
- [ ] Gate

## Group 3 — the recorded model port

- [ ] `RecordedModel(inner, tape)`, and the fingerprint
- [ ] a replay makes no model call
- [ ] a fingerprint not on the tape is a miss that says so
- [ ] RED: each of the above
- [ ] Gate

## Group 4 — compaction, and the model's verbs

- [ ] compaction as a component whose proposal reaches the sink
- [ ] `spawn` / `send` / `release` meta-tools
- [ ] the `held-helper` pattern that shapes the child
- [ ] RED: each of the above
- [ ] records, board, status
- [ ] Gate
