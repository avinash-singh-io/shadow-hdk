---
type: History
status: in-progress
epic: the-harness-as-data
---

# phase-36-plan-admission — History

### [NOTE] 2026-09-18 — Phase 36 derived from Epic 0009; the groups authored against the tree
Topics: planning, admission, limits, modes, component, amend, wire
Affects-phases: phase-36-plan-admission
Affects-specs: epics/0009-the-harness-as-data.md, research/2026-09-18-what-belongs-in-the-kit.md
Detail: D107–D121 inherited; deps re-derived to Phase 33 only (D117). The seven groups follow the
code as it is: `admit()` pure in the kernel mirroring `check_compatibility`; admission inside
`children.spawn` before `run()`; `compose` as a component on the `PersonComponents` precedent;
limits on `ModeSpec`; `Pattern.absorb`; amend through the held child's `resume`, which already
"takes the plan back in". G0 freezes the corpus RED first (Rule 11).

---

### [SCOPE_CHANGE] 2026-09-18 — ENH-020 folded in as Group 6 instead of a v0.30.1 quick-task
Topics: providers, behaviour, wire
Affects-phases: phase-36-plan-admission
Affects-specs: epics/0009-the-harness-as-data.md#amendments
Detail: The honest fix is additive — the opener reports the unmapped fields and `Thread` and the
wire surface them — which is a public contract addition; Rule 14 makes a contract change a
phase, not a quick-task. The shipped modes set no behaviour fields, so nothing shipped changes;
only a product mode that sets `system`/`model` on Codex or OpenCode learns what it was losing.
Proposed to the owner as Epic 0009's first amendment; recorded here pending their word.

---
