---
type: Tasks
phase: 24
---

# Tasks — Phase 24

## Group 1 — a skill says what it is
- [x] `Skill.description`, `Skill.source`; `skill_from` refuses a skill with no line
- [x] `SkillSource`, `DirectorySkills`, `MintedSkills`, `SkillRegistry` with shadowing on the record

## Group 2 — disclosure and choice
- [x] the catalogue lists skills as names and lines — on the `use_skill` tool itself (D55; `describe` of the tool shows them)
- [x] `use_skill` checks `missing_for` against `visible()`; unmet is refused by name; met loads the body — a step on the record

## Group 3 — minted and proposed
- [x] `mint_skill` mints for the run and proposes `kind="skill"` through the sink
- [x] a kept proposal comes back as a source next run (`source="kept"`)

## Group 4 — shipped and shown
- [x] a generic shipped library; `shipped()`; not one skill about code
- [x] the host example lists, uses, mints and keeps

## Close
- [x] D54–D56; index; documents; 0.18.0; status, roadmap, changelog, README; board (after landing)
