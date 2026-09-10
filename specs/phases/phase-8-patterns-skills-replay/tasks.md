---
type: Tasks
phase: 8-patterns-skills-replay
---

# Phase 8 — tasks

## Group 0 — patterns are files

- [x] the TOML format, and `load_pattern(path)`
- [x] `shipped()` over the packaged `library/` directory, read through `importlib.resources`
      so a wheel and a checkout behave the same — **measured**: all five .toml files are in the
      built wheel
- [x] the five pattern files
- [x] the loader refuses an unknown meta-tool, an unknown key, a missing key — each by name **and
      with the path**, which is what it adds over `Pattern.__post_init__`
- [x] RED: each of the above
- [x] Gate

## Group 1 — skills, checked before the first turn

- [x] `Skill(name, prompt, needs)` and `load_skill(path)`
- [x] `missing_for(skill, visible)` → what is missing, matched on **registration id** — the
      identifier `Invoke.component` takes, so a skill cannot declare a need it could not invoke
- [x] RED: a skill whose needs are visible is allowed
- [x] RED: a skill needing a hidden component is refused before any turn, naming what is missing
- [x] Gate

## Group 2 — the catalogue: `describe` (D13)

- [x] `Pattern.catalogue_threshold`, default 30, settable in a pattern file
- [x] above it: names and one-line descriptions only — schemas dropped, **components never**
- [x] `describe(name)` → the full interface, as a meta-tool (D3)
- [x] `describe` on a component the policy hides is refused — it answers only from `visible()`
- [x] RED: each of the above, and the **wiring** as well as the function — a mutation showed the
      catalogue could have gone out whole with nothing to notice
- [x] Gate

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
