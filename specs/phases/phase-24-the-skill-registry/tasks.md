---
type: Tasks
phase: 24
---

# Tasks — Phase 24

## Group 1 — a skill says what it is
- [ ] `Skill.description`, `Skill.source`; `skill_from` refuses a skill with no line
- [ ] `SkillSource`, `DirectorySkills`, `MintedSkills`, `SkillRegistry` with shadowing on the record

## Group 2 — disclosure and choice
- [ ] the catalogue lists skills as names and lines; `describe` answers for a skill
- [ ] `use_skill` checks `missing_for` against `visible()`; unmet is refused by name; met loads the body

## Group 3 — minted and proposed
- [ ] `mint_skill` mints for the run and proposes `kind="skill"` through the sink
- [ ] a kept proposal comes back as a source next run (`source="kept"`)

## Group 4 — shipped and shown
- [ ] a generic shipped library; `shipped()`; not one skill about code
- [ ] the host example lists, uses, mints and keeps

## Close
- [ ] D54–D56; index; documents; 0.18.0; status, roadmap, changelog, README; board
