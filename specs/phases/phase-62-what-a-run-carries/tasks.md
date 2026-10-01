---
type: Tasks
---

# Phase 62 — tasks

## G1 — one named fragment, one assembler
- [x] RED: `Fragment` does not exist
- [x] `Fragment(name, text, source)`; `Behaviour.fragments`; `carried_by` + `framed` (D166, D167)
- [x] Q1's bare `<instructions>` became a named fragment — the replacement Q1 recorded
- [x] mutation-checked

## G2 — BUG-229
- [x] RED: 8 tests red — the behaviour reached nothing
- [x] instructions layered onto the pattern's role (D168), `Behaviour.model` → `ModelRequest.model`
- [x] `_ModelSession.unmapped` names `effort`/`temperature` (D170), and nothing it *can* take
- [x] mutation-checked: 6 bite, including one restoring the empty `unmapped`

## G3 — a root's own instruction files
- [x] `root_instructions` as a reader a product composes (D169); the ENH-012 default untouched
- [x] empty → nothing; too large → truncated and said; unreadable → skipped, not fatal
- [x] mutation-checked

## G4 — `SKILL.md` as a skill source
- [x] `markdown_skills`; front matter for name/description/needs, body as prompt
- [x] a nameless file takes its directory's name; one malformed skill does not lose the rest
- [x] plugs into `SkillRegistry` beside the other sources
- [x] mutation-checked — 7 across G3+G4

## G5 — measurement and close out
- [x] **the sentinel re-measured on claude-code 2.1.284**: the default holds, and an offered
      fragment is followed. Both live, both printing the version
- [x] **a live measurement found a bug every unit test missed** — fragments were gated behind
      `instructions_in_prompt`, so Claude Code got none. Two gates now, plus a covering test
- [x] `docs/migrations/0.41.md`; 0.41.0, helper in lockstep
- [x] full gate: ruff clean, format 555 files, mypy 494 files, **2011 passed** / 20 skipped
- [x] no published schema moved
