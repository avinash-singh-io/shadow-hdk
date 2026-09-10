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

- [x] `RecordedModel(inner, tape)`, and the fingerprint — messages, **the tools offered**, and the
      model name
- [x] a replay makes no model call — a replay-only port has no inner model to call
- [x] a fingerprint not on the tape is a miss that says so, naming enough of the question to
      recognise it
- [x] answers consumed **in order**; asking more times than were recorded is a miss too
- [x] a tape saves and loads
- [x] RED: each of the above, plus a whole agent run replayed with **no model port at all**
- [x] Gate

## Group 4 — compaction, and the model's verbs

- [x] compaction as a **meta-tool** whose proposal reaches the sink and which the runtime writes
      nowhere; the transcript afterwards is shorter, and the role and brief survive it
- [x] `spawn` / `send` / `release` meta-tools, with `@1`-style handles
- [x] `keeps-helpers.toml` — a sixth shipped pattern offering the verbs. The child's *shape* is
      the composition the verb builds: the named agent given a brief, then a wait on the mailbox
- [x] RED: each of the above, plus a deployment with **no mailbox** where a helper cannot park
- [x] a Phase 7 bug found and fixed: a held child was woken on the ceiling it started with, which
      a parent that had spent since could no longer afford
- [x] records, board, status
- [x] Gate
