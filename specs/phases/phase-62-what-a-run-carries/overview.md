---
type: Phase
status: in-progress
epic: inner-loop-primitives
tags: [context, fragments, instructions, behaviour, agents-md, skills, claude-code, measurement, lane-p]
deps: [phase-59-a-change-on-the-record]
---

# Phase 62 — what a run carries into any provider

## Goal

Lane P's ask 5 (named context fragments, and ENH-047 as a component a plugin switches on), ask 11
(`SKILL.md` parsing), and **the remainder of ask 4** — which turned out to contain a defect.

## What planning this found: BUG-229

Lane P wrote *"a key-backed model takes instructions and skills directly."* It does not.

`ModelSession` stores `behaviour` and **nothing reads it**. A key-backed model's system message is
built from `pattern.system` plus a skill's prompt, so a mode's `system`, `append_system`, `model`,
`effort` and `temperature` all vanish. And `conversation.py:483` reads `unmapped` off the session by
name, which a `ModelSession` has not got — so `thread.unmapped_behaviour` comes back **empty**, which
a host reads as *your mode was honoured in full*.

Codex at least named what it dropped. This drops silently **and reports the opposite**, which makes
it a defect rather than a gap: the field exists to tell a host what was not honoured, and it lies.

So ask 4 had two halves and both were broken. Q1 fixed the CLI one; this fixes the other.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D166 | **One vocabulary for everything a run carries: a named `Fragment` (`name`, `text`, `source`).** Q1's `<instructions>` block becomes one | lane P asked for context that is "named, attributable, refusable, not an unmarked prefix", and four separate mechanisms for a mode's instructions, a root's `AGENTS.md`, a product's fragment and a skill's prompt would give four ways to be wrong. One shape, one assembler, and a model that has learnt to read one block has learnt to read all of them |
| D167 | **One assembler, in the kernel, for a CLI and a key-backed model alike** | the two were already diverging — Q1 folded into a CLI's prompt while a key-backed model got nothing. A single pure derivation is what makes "identically for a CLI and a key-backed model", which is lane P's own words, a property rather than an intention |
| D168 | **A mode's `system` is layered on the pattern's, never replacing it** for a key-backed model | `pattern.system` carries the loop's own mechanics — how to call a tool, when to stop. A `Behaviour.system` that replaced it would remove the instructions that make the loop work, so a mode's words are a fragment above the pattern's role, not a substitute for it. A CLI is the other case and keeps `--system-prompt`'s replacing semantics, because there the CLI owns its own loop |
| D169 | **Reading a root's `AGENTS.md` is a reader a product composes, not a default and not an agent tool** | ENH-047, and the existing default stays: a governed CLI does not read a folder's instruction files, because a run's instructions should be the mode's behaviour. What was missing is that the kit never *offered* them either. A function returning fragments is the smallest thing that fixes that without deciding for anybody |
| D170 | **`effort` and `temperature` are named unmapped for a key-backed model, because `ModelRequest` has nowhere to put them** | the honest half of BUG-229's fix. `ModelRequest` has `model`, so that is delivered; it has no effort and no temperature, and inventing one would be a kernel change this phase has no mandate for |

## Boundary and acceptance

**In:** `Fragment`; `Behaviour.fragments`; one assembler; BUG-229's fix (instructions and `model`
delivered to a key-backed model, `effort`/`temperature` named); a root-instruction reader; a
`SKILL.md` skill source; **the ENH-012 sentinel re-measured against claude 2.1.284**.

**Out:** deciding *which* fragments a run gets — that is the product's. Changing the default that a
governed CLI does not read a folder's instruction files. Any new `ModelRequest` field.

**Unchanged:** `pattern.system` still leads a key-backed model's system message (D168). A CLI with a
`--system-prompt` flag still uses it. Contract additions, so a minor and a *Pins* row.

## Groups

| | What | Asks |
|---|---|---|
| G1 | one named fragment, one assembler, for both provider kinds | 5, 4 |
| G2 | BUG-229 — a key-backed model is instructed, and says what it cannot take | 4 |
| G3 | a root's own instruction files, as a reader a plugin switches on | 5 |
| G4 | `SKILL.md` and `AGENTS.md` as a skill source | 11 |
| G5 | the sentinel re-measured on claude 2.1.284; migration note; version; gate | 5 |

## Verification

TDD strict, every assertion mutation-checked. Two measurements this phase owes rather than asserts:

- **The sentinel, on the version lane P ships.** BUG-031 is the precedent for not inferring across a
  CLI version gap — a later Claude Code shipped a built-in that a deny list written for an earlier
  one did not name. Measured on **2.1.284**, not 2.1.235.
- **A fragment actually reaches a live model**, for both provider kinds, because Q1 established that
  a green unit suite proves bytes reached a pipe and nothing more.
