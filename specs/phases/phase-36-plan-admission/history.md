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

### [EVALUATOR] 2026-09-18 — G0: the admission corpus v1 frozen, RED at collection
Topics: planning, admission, corpus, limits
Affects-phases: phase-36-plan-admission
Affects-specs: none
Detail: `tests/benchmarks/plan-admission-v1.json` (nine cases over depth, fan-out, steps, an
unregistered component, several reasons at once in the stable order, exactly-at-the-limits,
an `Await` as a leaf; three `meet` rows) with its sha-256 pinned in the kernel test; hypothesis
properties for `meet`; eleven runtime scenarios on the kit's own loop. Collection fails on
`shadow_hdk.kernel.PlanLimits` — the RED. Not edited again in this phase; a v2 is a new file.

---

### [DECISION] 2026-09-18 — PlanLimits carries only what admission can measure statically
Topics: planning, limits, leases
Affects-phases: phase-36-plan-admission
Affects-specs: epics/0009-the-harness-as-data.md#decisions
Detail: `PlanLimits(depth, fan_out, steps)`, each `int | None` with `None` unbounded. Seconds and
cents are not properties of a composition — no static reading of a plan can bound them — and the
lease already governs both at run time; the plan's *steps* is the one budget share admission can
state. The research note's "shares of seconds/cents" is narrowed accordingly; D109's shape
(order-bearing, `meet`) is unchanged. Measures: depth = nesting with a top-level leaf at 1;
fan_out = the widest `FanOut`; steps = leaf steps with an `Until` body counted `max_iterations`
times; an `Await` is a leaf.

---

### [NOTE] 2026-09-18 — G1: the kernel's admission is pure, published and mutation-checked
Topics: planning, admission, kernel, contracts, events
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/runtime.md#events, architecture/wire.md
Detail: `kernel/planning.py` — `PlanLimits` (depth, fan_out, steps; `meet`, `narrower_than`),
`measure()` (deepest leaf and widest fan-out named for the mismatch), `leaves_of()`, `admit()`
(structural then existence, the list complete and stable), `composition_digest()` (canonical
JSON, sha-256, as `StagedEffect.digest`). `PlanAdmitted`/`PlanRefused` join the `Event` union —
eighteen kinds now; `test_there_are_sixteen_kinds`, the wire's declared list and the
industry-words set updated, the last with its field precedent (plan mode, workflow agents).
Four contracts published with examples; TypeScript regenerated. The `effect` axis is the
runtime's (G2): the kernel measures, it cannot judge. [ARCH_CHANGE] pending for `/sync-docs`:
the events list in `architecture/runtime.md` and the wire's kinds.

---
