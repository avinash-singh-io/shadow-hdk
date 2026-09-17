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

### [DECISION] 2026-09-18 — D108/D121 amended: admission names a step's ask or refusal, it does not pre-empt it
Topics: planning, admission, questions, governance
Affects-phases: phase-36-plan-admission
Affects-specs: epics/0009-the-harness-as-data.md#amendments, architecture/runtime.md#the-governed-step
Detail: Implementing G2 against the whole suite showed the collision: with "a single call is a
plan of one step", raising the plan's question at admission either failed where no `Questions`
handle exists (breaking D57's park) or asked twice (plan, then step); and refusing a plan because
one step would be refused broke BUG-012's promise that the plan runs and the planner sees every
result — a step's own refusal is precisely a judgement the step *can* make. Admission therefore
refuses only what no step can see — structure and existence — and dry-judges effects to **name**
`PlanAdmitted.asks` and `.refusals`; each step is still refused, parked or asked live at its own
invocation through the existing path (D57, D58, D88). A host that wants one card for a whole plan
has the list and the rules to keep. D121's single question becomes a host presentation, not a
runtime park. Proposed as Epic 0009's amendment; the epic record carries it pending the owner.

---

### [DISCOVERY] 2026-09-18 — BUG-054: two README snippet tests fail on main since the v0.30 README refresh
Topics: docs, readme, tests
Affects-phases: phase-36-plan-admission
Affects-specs: none
Detail: `test_the_readme_three_lines_run_for_real` and `test_the_readme_snippet_is_what_the_smoke_run_runs`
read the README's snippets and run them; `ca432d0` changed both snippets without re-running the
tests. Reproduced on `ecb15f1` before any change here. Fixed in G7 with the README and docs.

---

### [NOTE] 2026-09-18 — G2: admission inside spawn, true for every caller
Topics: planning, admission, runtime, wire, fold
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/runtime.md, architecture/wire.md
Detail: `Children.admit()` before `run()`: structure and existence in the kernel, effects dry-judged
in the child's context (a handed `context=` wins, BUG-030), the events on the record, `PlanNotAdmitted`
to the caller. Three callers adapted honestly: the loop's `compose` answers the model with every
mismatch; the `spawn` helper verb composes only what is offered (it used to lean on the mailbox
step *failing*); the offer returns a refused one-call plan to a CLI as the error it always read.
The plan crosses the wire with its limits and its proposing step, and a refusal crosses as
`plan_refused`. A plan event never opens an item. [ARCH_CHANGE] pending for `/sync-docs`:
the governed step's story gains admission; the wire's kinds and `ERROR_KINDS`.

---

### [NOTE] 2026-09-18 — G3: compose is a component; a CLI planned through the socket, measured on Codex
Topics: planning, component, offer, live, codex
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/runtime.md#planning, providers/library/codex.toml
Detail: `runtime/planning.py` on the `PersonComponents` precedent, offered in the served composition
beside `ask_person`, held to the component contract. Two findings on the way: BUG-001's guard
refused the registered `compose` as a tool shadowed by the meta-tool — for the loop the plan-labelled
registration *is* the meta-tool (D110), so it is never shown as a second tool and `single` stays
unable to plan; and the offer carved a two-step ceiling for every call, which starved a plan of its
second step — a `plan`-labelled proposal now gets the parent's remaining steps (admission bounds
it). Live on **Codex CLI 0.154.0** (Claude Code signed out here): the CLI proposed
`fan_out(read_a, read_b)` through the socket; two `plan_admitted` on the record (the one-call plan
for the `compose` call, then the proposed plan); both `read_file` steps ran through the registry;
the reply named both contents. 2 turns, 4 steps, 17.4 s, 57,471 in / 324 out tokens, unpriced.
This is also the first live proof of the registry relay end to end on Codex, which
`codex.toml`'s comment still calls unproven — the comment is updated with the docs in G7. The
Claude Code half of the measurement is owed to the owner's sign-in.

---

### [DECISION] 2026-09-18 — G4: the shipped modes' plan limits, and a document narrows only
Topics: modes, limits, planning
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/adapters.md#modes
Detail: `PLAN_OF` — read-only and ask (depth 3, fan-out 8, steps 64), workspace-write (4, 16, 128),
full (4, 32, 256): generous on purpose, the lease the floor, but a ceiling so a runaway plan is
refused before its first step. A mode document's `[plan]` inherits the named policy's value on any
axis it leaves out (never unbounded by omission) and is refused by name if it widens the policy
on any axis — the rule a rule file already lives under (D24). A host that wants more than the
shipped ceiling composes a `ModeSpec` in code; data narrows, code decides. `Conversation.plan_limits`
is the host's met with the mode's, read at every turn, so `set_mode` changes the next plan's
limits live — measured in the test with a scripted CLI proposing a three-wide fan-out under a
two-wide mode, then again under an eight-wide one.

---

### [ARCH_CHANGE] 2026-09-18 — G5: the checkpoint carries the plan; amend is a resume; a plan may run after its planner
Topics: planning, amend, resume, checkpoint, state, defer
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/runtime.md#state, architecture/runtime.md#resume, architecture/adapters.md#patterns
Detail: `RunState.plan` — the composition as JSON, seeded in the initial state and written by every
node — so a parked run's shape survives where its state does. Two things follow. A settle now
resumes on the composition it parked with (`runtime.parked_composition`) instead of a rebuilt
one-step plan, which would have dropped every step after the parked one in a nested plan. And
`resume` handed a *different* composition admits it as an amendment (D116) before taking it:
`Composed` and `plan_admitted(amendment=True)`, or `plan_refused` with the run untouched. The
person's amendment travels as an answer — `Amend(composition, answer)` beside `Approve`, `Deny`,
`ApproveAndAddRule`, `Parked` — so whoever holds the plan performs it: `compose` and the loop's
component both wake the held child through `Children.amend`; refused, `compose` re-parks on the
same question. `Pattern.absorb=False` defers an admitted plan to run after its planner's step
closes (D112), as the same run's child. Also found and fixed: `compose` returned `Completed` when
a step inside its plan parked — it now parks the call on that question (D57) as the loop's
component does; and a settle reserved a one-call ceiling that starved a nested plan at its first
step — it reserves what the thread has left, the meter settling the rest back. Phase 33's
boundary showed up in the tests as designed: an irreversible write with no authority ports is
refused, fail-closed.

---

### [NOTE] 2026-09-18 — G6: unmapped behaviour is named, not dropped (ENH-020)
Topics: providers, behaviour, session, wire
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/adapters.md#jsonl, architecture/wire.md
Detail: `unmapped_behaviour` was already written and never called; it moved to `kernel.providers`
because the ACP opener needs it too and an adapter may not import another (the stands-alone
invariant). `AgentSession.unmapped` joins the port with a default of none (D14); the JSONL opener
computes it from the record's `behaviour_args`, ACP from a record that maps none. The conversation
reads it off the session at every open the way it reads `session_id`, so a `set_mode` that reopens
the provider re-reads it; `Changed.unmapped`, `Thread.unmapped_behaviour`, and `unmapped_behaviour`
on the `thread/start`, `thread/resume` and `thread/set_mode` results. Nothing shipped changes —
the shipped modes set no behaviour field — a product mode on Codex learns what it was losing.

---

### [DISCOVERY] 2026-09-18 — BUG-055: a second park in one leg replayed the first answer
Topics: runtime, resume, langgraph, amend, questions
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/runtime.md#resume
Detail: The wire test for `thread/amend` (refused, then admitted, on one thread) failed with the
first amendment's mismatch on the second call and the turn `failed` on *"interrupt() returned on
the parking path"*. LangGraph 1.2 replays a task's earlier resume values by index on every
re-run of the node, so a component that parks twice in one step gets answer one at the first
`interrupt()` and the new answer at the second — which was the *parking* call. G5's tests never
parked twice on one thread. Fixed in the executor (the park payload carries `replays`; the
component path drains that many before the newest), in `Thread.settle` (a question the run parks
on again is kept under the same handle; the agent is told its call is still waiting) and in
`compose` (the whole kept record on a refused amendment). P1, closed in this group.

---

### [NOTE] 2026-09-18 — G7: the plan crosses the wire; 0.31.0 at the gate
Topics: wire, typescript, docs, release, readme
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/wire.md, architecture/runtime.md#resume
Detail: `thread/amend` (D116) with `admitted`, `mismatches` and the events; `plan_limits` in and
out of `thread/start` and `thread/resume`, out of `thread/set_mode`; `plan` on every `modes/list`
row; the serve host reads `plan_limits` in the wire's words and refuses a non-integer axis by
name. The events already crossed (the `Event` union is the contract). Protocol stays `3`: every
addition is a method or a field, and the version is for a meaning change. `ModeRow`, `Amended`,
`thread.amend` and `plan_limits` typed in the TypeScript client; `tsc` and the build green.
`docs/migrations/0.31.md`; the kernel, runtime, modes and wire guides; `consuming.md` gains *a
plan, end to end*; `codex.toml` says the relay is proven. BUG-054 closed with the README's
runnable snippets. 0.31.0, `EXPECTED`, `uv lock`. The demo's re-pin to 0.31.0 from PyPI and its
chapter from the live run follow the publish, as 0.29.1's did — they cannot be true before it.
[ARCH_CHANGE] entries pending for `/sync-docs`: the wire's methods and kinds; the governed
step's admission; `RunState.plan` and the amend-as-resume; a second park in one leg.

---

### [NOTE] 2026-09-18 — /sync-docs: the architecture specs carry Phase 36
Topics: planning, admission, amend, wire, modes, runtime
Affects-phases: phase-36-plan-admission
Affects-specs: architecture/runtime.md, architecture/wire.md, architecture/adapters.md, decisions/impact-map.md
Detail: Additive, so specs directly (Rule 10): `runtime.md` — the governed step gains admission
before the transaction boundary; `children.py`, `step.py`, `state.py`, `loop.py`, `bindings.py`,
`approvals.py`, `conversation.py` and `threads.py` rows say what Phase 36 put there, BUG-055
included. `wire.md` — `plan_limits` and `unmapped_behaviour` on the thread methods,
`thread/amend`, `plan_refused` among the typed kinds, and the note that the plan crosses whole
with protocol 3 unchanged. `adapters.md` — `Pattern.plan`/`absorb`, `ModeSpec.plan` and the
shipped ceilings, a `[plan]` table narrows only. The impact map gains the phase's topics.
`momentum okf index` rewrote the decisions index again (BUG-050); restored from a copy.

---
