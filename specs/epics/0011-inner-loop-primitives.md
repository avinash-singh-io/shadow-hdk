---
type: Epic
id: "0011"
slug: inner-loop-primitives
status: complete
owner: avinash-singh-io
phases: [phase-59-a-change-on-the-record, phase-60-the-write-class-completes, phase-61-undo-and-an-agents-own-workspace, phase-62-what-a-run-carries, phase-63-visible-and-steerable]
policy_release: per-phase
policy_tdd: strict
---

# Epic 0011 — the inner loop as primitives

> **Status: complete through phase 63, unmerged.** Q1 and phases 59–63 are built, gated and
> pushed as branches. **Landing on `main`/`staging` and tagging a release remain gated on the
> owner's approval** (Rule 6) and the hooks enforce it, so nothing here has been released.
>
> What shipped, and what it cost: the suite went **1897 → 2021**, 63 mutations were verified to
> bite, and six of those mutations found assertions weaker than they looked. Two defects nobody
> had reported were opened and closed — ENH-051 (a product's instructions never reached Codex)
> and **BUG-229** (a key-backed model never received them *and* the thread reported them
> honoured). Asks 10 and 12 remain unscheduled, for the reasons below.
>
> **Scope is one repository.** Everything below is built in `shadow-hdk` (this repo). Nothing in
> [`shadow`](../../../shadow/specs/status.md), `shadow-ecosystem`, or any product repository is
> edited by this epic. Lane H's row on `intent-ecosystem/lanes/board.md` is in another repo and is
> therefore **not** updated from here — see *Known gaps* below.

## Why this epic exists, against a repository declared maintenance-only

`specs/status.md` says this repository is the maintenance-supported Python/LangGraph implementation,
that the current phase is none, and that future work starts at Phase 46 in `shadow`. Phases 46–58
here are transferred stubs that say *do not plan or execute the phase here*.

This epic deliberately reverses that for a bounded set of work, because:

1. The product (lane P, Intent Studio) ships on `shadow-hdk==0.36.0` **today**, and its first
   product gate is to match Claude Code and Codex for one developer.
2. The native harness in `shadow` is two to three weeks from being usable. Waiting costs the
   product its gate; building twice costs one epic here.
3. Every ask in lane P's 2026-10-01 handoff is a **primitive or a component**, not a product
   concept. The boundary rule is unchanged and untested by any of them.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D153 | **Capability work for a shipping product lands here while `shadow` is pre-usable.** A named epic, phases numbered from 59 so no transferred ID (46–58) is reused, each phase stating what migrates and what is throwaway. A bridge, not a change of direction: `shadow` remains the destination, D142–D152 stand, and nothing here is an argument for keeping the Python implementation | the product ships on 0.36.0 today and its first gate is blocked; the native harness is two to three weeks from usable; every ask is a primitive or a component, so none of it is work the boundary would refuse |

**Non-goals.** No native work. No architectural direction changes. No new door, transport or
protocol version. No product concept enters the kit — no plugin format, no plugin loader, no folder
of agents or skills the kit loads for a product. Protocol 3 stays unchanged throughout.

## The twelve asks, and what is actually already built

Verified against the code at 0.36.0 before this plan was written. Two asks are **mostly answers**;
one may avoid a kernel change entirely.

| # | Ask (lane P's priority) | Verified state |
|---|---|---|
| 1 | ENH-044 — the diff of every change on the record (P1) | **Missing.** `write_file` records `{"path", "bytes"}`; `delete_file` the path. `EffectRecorded.detail` is already free `JsonValue` (`kernel/events.py:77`), so before/after can ride it **without a kernel field** — to be proven, not assumed. |
| 2 | ENH-042 rest — background shell, cross-file atomic patch (P1) | **Missing.** `runtime/environment.py::OPERATIONS` has nine operations; neither is among them. |
| 3 | ENH-043 — checkpoints and undo as governed acts (P1) | **Missing.** `grep worktree src/` returns zero. Backlog records the dependency: needs ask 1 first, to know what a snapshot must hold. |
| 4 | Everything a run needs, passable as data, to every provider (P1) | **Mostly built, one real gap.** `Behaviour` carries `system`, `append_system`, `model`, `effort`, `temperature`, `tools_offered`. `SkillSource` is a protocol; `StoreSkills` already reads a `Store`'s `skills` collection — a product's database **is** a supported skill source today. `SkillComponents` registers the registry as tools, so product skills already reach a governed CLI through the relay. Sub-agents exist (`runtime/children.py`). **Gap: Codex takes no `system`/`append_system`/`temperature` flag** — `providers/library/codex.toml:121`. The kit is honest about it (the fields are named on `thread.unmapped_behaviour`, reported over the wire at `wire/threads.py:424`), but the instructions do not reach the model. |
| 5 | Phase 55 context fragments; ENH-047 as a component (P1) | **Missing.** Plus a cheap measurement lane P asked for by name: re-run the ENH-012 sentinel against claude **2.1.284** rather than inferring from 2.1.235. |
| 6 | What a run creates comes back as a proposal (to agree) | **Mostly built, one subtraction.** `mint_skill` already emits a `Proposal` on `SinkPort`. But `KeepingSink` (`serve/keeping.py`) then writes it into **the kit's own store** — exactly what lane P says it does not want. The change is to make that keeping optional and to stop narrowing on `kind == "skill"`. |
| 7 | An isolated environment per agent (P2) | **Missing.** Shares the git mechanism with ask 3. |
| 8 | ENH-045 — the live plan (P2) | **Half built, not the half needed.** `Composed`, `PlanAdmitted`/`PlanRefused` and `items()` exist. The agent's own narration does not. |
| 9 | ENH-046 — steer for key-backed models (P2) | **Missing, small, localized.** `ModelAgent.steer` returns `False`; the loop between steps is the kit's own. |
| 10 | Credential injection at the boundary (to agree) | **Design only.** D137 already names an egress proxy with an allowlist as a later seam. Not scheduled here. |
| 11 | A parser for `SKILL.md` / `AGENTS.md` (optional) | **Partly.** `DirectorySkills` parses `*.toml` only; no frontmatter reader exists. |
| 12 | Phase 54 — triggers (later) | **Not scheduled.** Parked on lane P's side pending their initiative 0055. |

### Answers lane P can act on without waiting for code

Ask 4 and ask 6 are largely already-built. Their answers ship as documentation **before** Phase 59,
so lane P can act this week:

- Their database is already a skill source — implement the `Store` port and pass `store_skills(...)`
  as a `SkillSource`. No kit change needed.
- Product skills already reach a governed CLI as **tools through the relay**, which is the mechanism
  they guessed at in §4.1.
- `mint_skill` already proposes on the sink. What they must do is **not install `KeepingSink`**, or
  wait for Phase 59 to make its store-write optional.
- They can verify the instruction gap themselves today: read `thread.unmapped_behaviour` on a Codex
  thread and they will see `system` and `append_system` named.

## Phases

Numbered from 59: 46–58 are transferred stubs and D152 preserves completed IDs.

### Quick-task Q1 (before the epic) — instructions reach a dialect with no flag

Lane P's ask 4, the only part that is a capability gap rather than an answer. A dialect that maps no
flag for `system`/`append_system` folds them into the turn's prompt instead, named rather than
prefixed unmarked, and stops reporting them as unmapped once they are delivered. Bounded to the
dialect layer and its tests, so a quick-task under Rule 14, not a phase.

**Why first:** it is days of work, it is P1, and it is the one thing lane P's Build agent needs to
behave the same on Codex as on Claude Code.

### Phase 59 — a change is legible on the record

**Asks 1 and 6.** Lane P's top priority, and Phase 61 depends on it.

- The write path captures prior content (or its absence) and puts a bounded before/after on the
  observation and the effect record. Lane P answered the open question: **keep content up to a cap,
  mark `truncated` beyond it, and do not keep every file version** — git keeps history for
  repositories.
- A binary or undecodable file is marked, not carried.
- The cap's location and default are decided in this phase and stated in the migration note.
- `edit_file` and `move_file` gain the same treatment, so all write-class operations are uniform.
- `KeepingSink`'s store write becomes opt-in; `Proposal` handling stops narrowing on
  `kind == "skill"`, so a memory or an instruction a run mints reaches the product's sink too.

**Decision to settle first:** whether `EffectRecorded.detail` carries this (no kernel change, no
ADR) or a new field is honest (ADR + minor bump, per project-rules). Prove it; do not assume it.

### Phase 60 — the write-class toolset completes

**Ask 2.** Both halves cost lane P today, confirmed in their reply.

- A **cross-file atomic patch** admitted as one act: all files land or none, with the record honest
  about what happened. Depends on Phase 59, because a patch whose record lies is worse than no patch.
- A **background shell** with start, status, output and kill — a dev server, a watcher, a long test
  suite. Each an operation with an honest effect profile, so every mode judges it like the nine.
- The process-lifetime rule already established applies: D35 says a step owns the process tree it
  starts, and BUG-019 is the precedent for what happens when it does not.

### Phase 61 — undo and an agent's own workspace

**Asks 3 and 7.** One git mechanism serves both.

- A snapshot before a turn's first write; a restore that **is itself an act** — effects, the mode's
  judgement, on the record. An undo that bypasses governance is a hole.
- A port with a git-backed adapter, which is what lane P narrowed the design question to: cheap
  where a root is a work tree, and that covers their first use case. A port means a refuse-not-crash
  default, per project-rules.
- Per-agent isolated environments via git worktrees locally, so several agents run in parallel each
  producing its own pull request. Where a cloud sandbox lives stays unagreed and out of scope.
- **ADR required** (a new port).

### Phase 62 — what a run carries into any provider

**Asks 5, 11, and the remainder of 4.**

- Named context fragments the product passes as data: named, attributable, refusable, framed by the
  mode's behaviour — not an unmarked prefix — and identically for a CLI and a key-backed model.
- ENH-047 as a **component a plugin switches on**, not a default: the workspace reads a root's own
  `AGENTS.md`/`CLAUDE.md` and folds it in as named data. The existing default (a governed CLI does
  not read them) stays.
- **Re-measure the ENH-012 sentinel against claude 2.1.284**, the version lane P ships. BUG-031 is
  the precedent for not inferring across a CLI version gap.
- `SKILL.md`/`AGENTS.md` frontmatter parsing as an optional `SkillSource`, if it is still wanted by
  the time this phase starts.

### Phase 63 — the loop is visible and steerable

**Asks 8 and 9.** Both P2; smallest phase.

- `ENH-045`: the agent's plan as a **registered component** whose calls are plan items and whose
  effects are nothing, so every mode admits it and the record carries revisions in order. The
  mechanism is the kit's; the plan's content is the product's.
- `ENH-046`: a steer queued on the running key-backed loop and delivered before the next model call,
  same `bool` contract. A one-shot dialect stays `False`.

### Not scheduled

- **Ask 10 — credential injection.** Needs agreement on where the vault and egress proxy live
  before any code. D137 names the seam.
- **Ask 12 — Phase 54 triggers.** Parked pending lane P's initiative 0055.

## Sequencing and dependencies

```
D1 (reply to lane P, docs only) ─┐
Q1 (Codex instructions)  ────────┼──▶ 59 ──▶ 60
                                 │      └───▶ 61
                                 └──▶ 62        (61 needs 59's snapshot content)
                                      63        (independent; last)
```

- **59 before 61** — the backlog records it: a snapshot needs to know what it must hold.
- **59 before 60** — a cross-file patch's record depends on 59's diff machinery.
- **62 and 63 are independent** of the 59→60→61 spine and can move if priorities change.

## Release and version policy

Per-phase, matching how lane P has been consuming releases (0.34.2, 0.35.0, 0.36.0). Every phase
here is **contract additions** — a minor bump under D9 and a *Pins* row — with protocol 3 unchanged:

| Phase | Version | Contract |
|---|---|---|
| Q1 | **0.37.0** ✅ | a `Dialect` field, so a minor; `Provider.json` and the TS client regenerated |
| 59 | **0.38.0** ✅ | additions; no ADR needed — the change rides the observation's own output |
| 60 | **0.39.0** ✅ | additions: `apply_patch`, `run_background`, `job_output`, `kill_job` |
| 61 | **0.40.0** ✅ | additions + a new port (`WorkspaceHistoryPort`), D161–D165 recorded |
| 62 | **0.41.0** ✅ | additions + BUG-229 fixed; no published schema moved |
| 63 | **0.42.0** ✅ | additions: `update_plan`, and `steer` for a key-backed model |

## Gate, per phase, before anything claims done

Rule 12 and project-rules, unchanged and non-negotiable:

`uv run ruff check` · `uv run ruff format --check` · `uv run mypy` (strict) · `uv run pytest`

TDD is **enabled and strict** (Rule 13): every group starts red, every assertion is mutation-checked,
ports get contract suites that every adapter subclasses. Plus, because Q1 and Phase 62 are about
what actually reaches a model, at least one **live** measurement per phase that touches a provider —
a green unit suite does not prove instructions arrived.

## Pre-phase bug check (Rule 4), run 2026-10-01

- **No open P0 or P1 bugs.** Every P0/P1 in `backlog.md` is closed; the open P1 rows are ENH-042 and
  ENH-044, which are this epic's own asks.
- `momentum learnings` reports one class: **2 stale closures** (ENH-033, TD-012), both pointing at
  `scripts/`, not `src/`. Advisory inferences, not measurements — to be **hand-verified before any
  status is flipped**. This project's own history includes a learnings run that claimed seven stale
  entries with two P0/P1s when the truth was four and none.

## Known gaps in this plan

- **The lane board is not updated.** `intent-ecosystem/lanes/board.md` is in another repository and
  this epic touches one. Lane H's row will go stale for this epic's duration unless lane P or the
  owner updates it.
- **Asks 10 and 12 are unscheduled** and this plan does not resolve them.
- **The cap in Phase 59 is undecided** — its value and location are that phase's first decision.
- **Ask 11 may be dropped.** It is optional and lane P said it will use `DirectorySkills` if it
  already parses `SKILL.md`, which it does not.
- **What migrates to `shadow` is stated per phase and not yet written**, because no phase has run.

## Outcome, 2026-10-01

| ask | where it landed |
|---|---|
| 1 — the diff on the record (ENH-044) | phase 59, 0.38.0 |
| 2 — patch and background shell (ENH-042) | phase 60, 0.39.0 |
| 3 — checkpoints and undo (ENH-043) | phase 61, 0.40.0 |
| 4 — everything a run needs, as data | **answered** (mostly already built) + Q1 (0.37.0) + BUG-229 in phase 62 |
| 5 — context fragments, ENH-047, the sentinel | phase 62, 0.41.0 — measured on claude-code 2.1.284 |
| 6 — a run's creations come back | phase 59, 0.38.0 (a subtraction: `KeepingSink` made opt-in) |
| 7 — an isolated environment per agent | phase 61, 0.40.0 (host-side worktrees) |
| 8 — the live plan (ENH-045) | phase 63, 0.42.0 |
| 9 — steer for key-backed models (ENH-046) | phase 63, 0.42.0 |
| 10 — credential injection | **not scheduled** — needs the owner's decision on where the vault and egress proxy live |
| 11 — `SKILL.md` parsing | phase 62, 0.41.0 |
| 12 — Phase 54 triggers | **not scheduled** — parked on lane P's initiative 0055 |

### What this epic taught, worth carrying to `shadow`

- **A green unit suite proves bytes reached a pipe.** Twice a live measurement found what no unit
  test could: Q1's whole point (does a model obey framed in-turn instructions) and phase 62's
  one-gate bug, where fragments never reached Claude Code because every unit test used a dialect
  that folds.
- **The mutation pass is not a formality.** Six of 63 mutations found assertions that could not
  fail — a safety claim that was only a docstring (phase 60's confinement), a guard whose deletion
  still passed (61), a test refused for the wrong reason (61), an ordering that passed by luck (61),
  and a refusal tested at the wrong layer (63).
- **Two of lane P's twelve were answers, not builds**, and finding that out before writing code was
  the highest-value hour of the epic.
