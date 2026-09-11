---
type: Phase
phase: 8
name: patterns-skills-replay
epic: 0003-composition-at-scale
status: complete
topics: [patterns, skills, replay, compaction, describe, d13, d17, toml]
deps: [phase-7-sub-agents]
---

# Phase 8 — Patterns, skills, replay

## Goal

`09` §5 is the claim this phase has to make true:

> The framework ships a small set — `single`, `plan-and-execute`, `orchestrator-workers`,
> `critic-pair`, `reflect-until` — and a team adds its own **the same way it adds a skill**. Nothing
> in the runtime knows the names.

Today `single` is a Python dataclass in a module. That satisfies *nothing in the runtime knows the
names* and fails *a team adds its own*: adding one means editing the package. A pattern the
framework ships and a pattern a team writes have to be the same kind of thing, and that thing is a
**file**.

Five deliverables, and each is a claim that can go wrong on its own:

| | claim |
|---|---|
| patterns as files | the four shipped patterns are data, loaded, and a team's own loads the same way |
| skills | a team's procedure is a file that **declares what it needs**, so skill and mode can be checked against each other before a run rather than halfway through |
| `describe` | D13's fourth mechanism: above a threshold the model sees names and one-liners and pulls a schema on demand |
| the recorded model port | a run's model calls can be replayed at no cost, which is what makes a $0 regression suite possible |
| compaction | a component, not a runtime power (`09` §5): the model proposes a summary of its own transcript and the **sink** decides whether it is kept |

## D17 — patterns and skills are TOML, and the loader refuses what it cannot check

**TOML**, for two reasons rather than taste. A role file is multi-line prose, which JSON cannot hold
without escaping it into unreadability; and `tomllib` has been in the standard library since 3.11,
so a file format costs no dependency. YAML would cost one, and would buy ambiguity — a version
string that parses as a float is not a hypothetical.

The second half matters more. A skill declares the components it needs. `10` §306 says this is so
*skill and mode can be checked against each other* — and the check is the whole point, so it
happens **before the first turn**, against `RunContext.visible()`. A skill that needs a component
the deployment's mode forbids is refused with the names of what is missing, rather than discovered
three steps in when a tool call fails.

That is the same move as `visible()` itself: a thing the policy would refuse is **absent**, not
greyed out (`09` §4). A skill is just the first thing that can say what it wants in advance.

*Rejected:* checking a skill lazily, at the moment it calls a tool. It costs a model turn to learn
what a file could have said, and the failure arrives as a refused tool call in the middle of work
rather than as a refusal to start.

*Rejected:* a Python entry point per pattern. It makes the framework's patterns a different kind of
thing from a team's, which is exactly what `09` §5 says they must not be.

*Overturned by:* a pattern needing to compute something — a role that varies with the deployment,
say. That would mean patterns want a template language, and the honest answer then is a template in
the file rather than a callable behind it.

## What is NOT in this phase

- **Record-a-skill** — offering a run that went well as a reusable procedure. `10` puts it at R8,
  and it needs the record, which is the product's side.
- **The agent editing its own patterns or skills at runtime.** `10` §457 is explicit: not until
  effect-rules governance (R5) and a human approval step (R10). *Learning may propose a measured,
  versioned change; it may never silently install one.*

## Exit criteria

- The four patterns ship as files and load; a team's own file loads by the same call
- A skill declares what it needs, and a run whose mode hides one of them refuses to start and says
  which
- Above the threshold the catalogue is names and one-liners, and `describe` returns a full schema
- A recorded run replays with no model call, and a changed prompt is a replay miss rather than a
  silent re-record
- Compaction is a component whose output reaches the **sink** as a proposal
