---
type: Planning
---

# What moves to Shadow, and what is throwaway

> **This is H10, and D153's standing requirement.** D153 permits capability work to be carried here
> while `shadow` is pre-usable, on one condition: *each phase stating what migrates and what is
> throwaway*. **Phases 59 through 65 did not state it, including the phase that found this gap.**
> This document is that statement for every contract added between 0.38.0 and 0.44.0, and it is the
> thing to update at the end of any later bridge phase.

**Written 2026-10-03, from `shadow` at `origin/main` plus `phase-64-models-and-tools`.** Every row
below is a claim about what `shadow`'s *specifications* say today, not about what its authors intend.
A row saying *not planned* means **no phase of Shadow's names it** — not that Shadow has refused it.
Re-read before relying on it; the sibling repository moves.

## Decision

| # | Decision | Rationale |
|---|---|---|
| D184 | **What moves to Shadow is stated per contract, in this one file, and every later bridge phase updates it before closing** | D153 permitted this bridge on the condition that each phase say what migrates and what is throwaway. Phases 59 through 65 did not say — so the condition was met in letter and not in substance, and eight shipped capabilities turned out to have no planned home. A per-phase paragraph in a retrospective nobody re-reads is what failed; one file that is the answer, kept current, is the correction. It also gives a product integrating today a single list to put behind its own adapter |

## The method, so the next reader can repeat it

Each contract name was searched across the whole of `shadow/specs/`, then the hits were read for
**sense** rather than counted. Counting alone is misleading here and nearly misled this document:
`checkpoint` matches 42 files, `restore` 21, `proposal` 34 and `change` 147 — and almost all of those
are other senses of ordinary words. Two distinctions did the work:

- **Scope versus record.** A term in a phase's `overview.md` is in that phase's *scope*. A term only
  in its `history.md` or `evidence/` is a record of something already discussed, which is not a plan.
- **Which sense.** `checkpoint` in Shadow means the durable engine's state and "an internal
  checkpoint, not a supported release". It does not mean a workspace a person can put back.
  `worktree` in Shadow means a development worktree in `repository-layout.md` and `release-plan.md`,
  not a worktree per agent.

## The one fact that frames all of it

Shadow's **Phase 59 — open integrations and standards** is the only phase chartered to bring this
kit's work across. Its goal line reads *"After the alpha, bring the capabilities already built in
`shadow-hdk` into the new architecture"*. Its named scope is: Shadow as an ACP agent; Agent Skills
(`SKILL.md`); `AGENTS.md` and OKF bundles; OpenTelemetry with the GenAI conventions; later
policy-as-code and hook-name mapping.

**It names none of the eight capabilities this kit shipped in 0.38–0.42.**

And the timing is further out than "after the alpha" alone suggests: Phase 59 is `planned` and
depends on Phase 51 and Phase 64. **Phase 51 _is_ the alpha** and is itself `planned`; Phase 61
(hardening, "before the alpha") is `planned`; Phase 64 is `in-progress`. So between today and Phase
59, anything a product needs either exists in this kit or exists nowhere.

## Migrates — named in Shadow's own scope

| contract | where Shadow carries it |
|---|---|
| Skills, and a skill's declared needs | Phase 59: *"Agent Skills (SKILL.md): register, create, list and package skills. Keep `shadow-hdk`'s checking of a skill's needs and its recorded origin."* Named explicitly, ours cited |
| `SKILL.md` / `markdown_skills` as a source | Phase 59, same line. The parser itself is throwaway; the capability is not |
| `root_instructions`, `AGENTS.md` | Phase 59: *"AGENTS.md and OKF bundles as instruction and knowledge sources. They resolve once, at run start, into the instructions Phase 64's agent pins with the run."* |
| Context fragments (D166–D168) | Phase 64 design evidence (`group-5c`), and Phase 59's instruction-pinning line above. The assembler is throwaway; framed context survives |
| Usage, cost and OTel | Phase 59: OpenTelemetry with GenAI conventions, *"Port `shadow-hdk`'s rule that payloads never go on spans"* |
| ACP as a front door | Phase 59: *"Shadow as an ACP agent"*, reusing the `agent-client-protocol` crate Phase 64 adopts |
| `steer` mid-turn | Phase 65's `overview.md` (complete as an internal checkpoint). Present in scope; whether the shape matches ours is unverified |
| Threads, turns, approvals, parking, durable runs | Shadow's core and its Phase 63 durable engine port, which is **complete** |

## Not planned — throwaway unless Shadow adds it

Each of these was searched across the whole spec tree and appears in **no** Shadow phase, in any
file. This is the parity list.

| contract | shipped | hits in `shadow/specs/` |
|---|---|---|
| `change` on the record — a diff for every write, edit, delete and patch (D154–D156) | 0.38.0 | none in any scope; `change` matches 147 files as an ordinary word |
| `apply_patch` — a multi-file edit as one act (D157) | 0.39.0 | **0 files** |
| `run_background`, `job_output`, `kill_job` (D158–D160) | 0.39.0 | **0 files each** |
| `checkpoint`, `restore`, `list_checkpoints` — a workspace put back (D161–D165) | 0.40.0 | the word appears only as the durable engine's state and as "an internal checkpoint, not a supported release". *"restore the workspace"* / *"workspace undo"*: **0 files** |
| `open_worktree`, `close_worktree` — a worktree per agent | 0.40.0 | **0 files**; `worktree` elsewhere means a development worktree |
| `update_plan` — the agent's own visible plan (D171, D172) | 0.42.0 | **0 files** |
| `tools_offered` — narrowing what a step is shown (D178, D179) | 0.44.0 | **0 files** |
| `Behaviour.silence_seconds` — the provider's patience (D182) | 0.44.0 | **0 files** |
| Agents as store rows: `store_patterns`, `ModeSpec.agent`, `thread/start {agent}`, `agents/list` (D174–D177, D183) | 0.43.0, 0.44.0 | **0 files each** |
| `ThreadRecord.agent` / `.agent_override` | 0.44.0 | **0 files** |

## Unknown — needs a reading, not a guess

| contract | why it is unresolved |
|---|---|
| `SinkPort` and proposals (D169, 0.38.0) | `SinkPort` matches **0 files**, but `proposal` matches 31 phase files. The concept may well exist in Shadow under another name, and saying either *migrates* or *throwaway* would be a guess. Someone who knows Shadow's vocabulary should settle it |
| `Dialect.instructions_in_prompt` — the Codex fold (ENH-051, 0.38.0) | A quirk of driving a particular CLI. Whether Shadow drives CLIs the same way is Phase 64's business and not readable from here |

## What this means, stated plainly

1. **Eight shipped capabilities have no planned home.** They are the parity list above, and they are
   exactly what lane P's product uses for its developer workbench. On today's specifications they are
   throwaway: valuable now, gone at the switch.
2. **D153 was satisfied in letter and not in substance.** It permitted this bridge *because* each
   phase would say what moves. Seven phases did not say, which is how eight capabilities came to be
   built without anyone deciding whether they survive.
3. **The decision is Shadow's scope, not this kit's.** Nothing here can make a capability migrate.
   The useful output of this document is the list, handed to whoever sets Shadow's phase 59 and 60
   scope, plus the warning that the list is what a product would lose on the day it switches.
4. **For a product integrating today:** put the parity list behind an adapter of your own. The
   *migrates* table needs no wrapping — those either match Shadow's model or are named in its scope.

## Keeping this true

Any later bridge phase in this repository adds its contracts to one of the three tables before it
closes. That is D153's requirement and the reason this file exists rather than a paragraph in a
retrospective nobody re-reads.
