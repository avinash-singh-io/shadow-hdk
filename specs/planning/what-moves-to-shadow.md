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

## Second reading: Shadow answered this from its source (2026-10-03)

**Everything below the method section was first written from `shadow/specs/` alone**, and said so.
Shadow's own session then answered D184 row by row **from its source rather than its specs** — the
`2026-10-03-answers-for-lane-p` handoff on its `claude/optimistic-einstein-qejjar` branch (a document
in the *sibling* repository, not this one), §2 and §3, read first-hand for this revision.

That moved five rows, and the reason is worth keeping: **three capabilities exist there under other
words**, so a search for our names found nothing and concluded nothing was planned. A spec grep
answers *is this name present*. It cannot answer *is this capability present under another name*, and
only the people who know the other vocabulary can. The two readings are different kinds of evidence
and this file now says which is which per row.

## Migrates — named in Shadow's scope, or already built there

| contract | where Shadow carries it | evidence |
|---|---|---|
| **`tools_offered`** — narrowing what a step is shown | **Already shipped, three ways.** A plan grants only the tools a step binds; the tool face lends a delegated CLI only the granted tools and never control tools; the context projector narrows what is *presented* per turn, preferring `allowed_tools` so a cached prefix stays stable — **and the narrowing is journaled per turn**. Run templates also carry a tool list. Shadow notes BUG-230 could not take this shape there, because a journaled narrowing cannot be reported as honoured while nothing narrows | Shadow §2.1, phase 64 G5b accepted, G10 |
| **`Behaviour.silence_seconds`** — the provider's patience | **Yes in substance.** A **stall deadline that stream progress resets**, beside a call deadline, with the wall hold bounding the act. And D182's real point holds there structurally: an approval is a **durable parked decision**, not time inside a model act, so a person thinking for twenty minutes cannot fail a turn. Missing only the *place to set it per mode* — Shadow has no mode; it is per model component and per act | Shadow §2.1, phase 64 G2c/G3 |
| **`update_plan`** — the durable half | **Mostly there under another name.** A strategy proposes a plan revision, Core admits or refuses it, and `PlanRevisionAdmission` is journaled per revision with head, proposer and digest — so *step 2 of 5* is readable off the journal with no tool. Absent: a **model-authored** plan list as a product-visible artifact | Shadow §2.1, phases 47/48/63 done; 53 then 56 for the surface |
| **Agents as data** — `store_patterns`, `agents/list`, a named agent per run | **Partly before the alpha, fully later.** Phase 64 G5.1's **run templates** are *"a named, product-registered agent definition with a model allowlist, tools, instructions, limits and a budget ceiling"*, listed by `builtins.list` and aligned with phase 53's registry. That is our 0.43 agent row minus store-row CRUD inside Shadow and minus the mode indirection | Shadow §2.1/§4, 64 G5.1 pre-alpha; 53 later |
| **`ThreadRecord.agent`** | **Follows run templates.** The template a run names is part of its binding and configuration digest, so *which agent ran* is on the record and survives a resume and a takeover **by construction** — the record is the journal, not a mutable row, which is precisely what broke in our BUG-234 | Shadow §2.1 |
| Skills, and a skill's declared needs | Phase 59: *"Agent Skills (SKILL.md) … Keep `shadow-hdk`'s checking of a skill's needs and its recorded origin."* Named explicitly, ours cited | `shadow/specs/` |
| `root_instructions`, `AGENTS.md` | Phase 59: instruction and knowledge sources resolving once at run start into what phase 64's agent pins | `shadow/specs/` |
| Context fragments (D166–D168) | Phase 64 design evidence (`group-5c`), and phase 59's instruction-pinning. The assembler is throwaway; framed context survives. HDK H6/BUG-238 now decodes stored mode fragments before assembly (0.47.1 candidate); the existing store-put wire path carries them | `shadow/specs/` |
| Usage, cost and OTel | Phase 59: OpenTelemetry with GenAI conventions, *"Port `shadow-hdk`'s rule that payloads never go on spans"* | `shadow/specs/` |
| ACP as a front door | Phase 59: *"Shadow as an ACP agent"* | `shadow/specs/` |
| `steer` mid-turn | Phase 65's `overview.md`; shape unverified against ours | `shadow/specs/` |
| Threads, turns, approvals, parking, durable runs | Shadow's core and its phase 63 durable engine port, **complete** | `shadow/specs/` |
| **A governed run carrying only the tools it was given** — our Codex `--ignore-user-config` (0.45.0, H23) | **Yes.** Shadow's **tool face** lends a delegated CLI only the tools the plan grants and never control tools; its own answer names this as H23's answer too. Ours is a launch flag on one CLI; Shadow's is structural, so the flag is throwaway and the property survives | Shadow §2.1, phase 64 G10 |

## The primitives exist; who writes the component is an owner decision

Shadow's §2.0 settles why five of our rows looked alike: they are **file and shell tools**, and
Shadow has none *by design rather than omission* — it governs effects rather than names, so a file
edit or a shell command is a component behind the component contract with an effect profile the
Authorizer judges. Its `integrations/tools/` holds an MCP client and a JSON-pointer tool.

So for all five the question is not whether Shadow's core can carry it but **who writes the
component** — Shadow in its phase 64 G11 / 59, or the product behind its own adapter. **Shadow
recommends its phase 59; the owner decides** (Shadow §9.1, lane P's roadmap §5 as *D-M*).

| contract | the primitive Shadow already has |
|---|---|
| `change` on the record — a diff per write, **plus 0.45.0's host-set cap (`change_diff_bytes`), bounded hold (`change_diffs_held`) and `change_diff` door, with `whole` and `handle` on the change** | the **payload store** (64 G2b, done): content-addressed, SHA-256, scoped by principal and lineage, with erase. Shadow notes this answers **H20's harder half** directly — a host-set cap plus a governed door to fetch the whole diff later is `put` a payload, journal its digest, `get` it under the principal's authority. **Theirs is the better design**: ours holds cut diffs in memory, bounded and evicted oldest-first, where theirs is content-addressed and erasable. So 0.45.0's hold is **throwaway** and the capability is not. Absent either way: a file tool to emit the diff |
| `apply_patch` | one governed component act with a bounded input schema; the schema validator (G5b) and the payload store carry it |
| `run_background`, `job_output`, `kill_job` | **every primitive, and they are the hard part**: owned async acts (G2c) as futures the run owns to their terminal within a wall deadline and grace; owned resources by scope released on stop, cancel and takeover — which is what *jobs die with the environment* was; an act handle carrying a `background_job` kind given to recovery's reconcilers; **live output** through `LiveSink`, replacing our polling; and the process owner extracted in G1 with no leaked grandchildren as a G10 test. The three operations are a thin component over that |
| `checkpoint`, `restore`, `list_checkpoints` | owned resources by scope (a checkpoint is run-scoped state released on cancel). Shadow confirms our reading that its own *"checkpoint"* is a different word |
| `open_worktree`, `close_worktree` | the same: a worktree is an owned resource by scope, and the child-run machinery already narrows a child's ceiling |

## Added by phase 66, and where each one lands

D184 requires every bridge phase to add its contracts here before closing. Phase 66's:

| contract | shipped | what happens to it |
|---|---|---|
| `change_diff_bytes`, `change_diffs_held`, `change_diff`, `change.whole`, `change.handle` | 0.45.0 (H20) | in the file-and-shell table above: the capability is answered by Shadow's payload store, our in-memory hold is throwaway |
| `Dialect.mcp_strict_args` carrying `--ignore-user-config` for Codex | 0.45.0 (H23) | **migrates in substance** — Shadow's tool face is structural where ours is a flag on one CLI, so the flag is throwaway |
| `Thread.agent_unhonoured`, `ThreadRecord.agent_unhonoured`, and the field in `thread/start`'s reply | 0.45.0 (H11-A) | **follows run templates, and Shadow's shape is better.** A template a run names is part of its binding and configuration digest, and Shadow's own rule is that *any* fallback is journaled rather than silent — so *the agent you asked for and could not have* is on the journal by construction rather than in a field we had to add |
| `Carried` and `carried_into` — an agent's role and tool list composed into a provider's behaviour | 0.45.0 (H11-B) | **throwaway, capability met.** Instructions reach a delegated agent through Shadow's **agent profile**, which is data; the narrowing is the tool face and the context projector. Ours is a composition for a kit that has modes, and Shadow has none |
| `Pattern.skill`, `SkillRegistry.named`, `Carried.unhonoured` | 0.45.0 candidate (H11-E), not published | skill selection belongs with Shadow phase 59's Agent Skills; this stored-row binding is a bridge contract, not a requirement to copy HDK's loop. A CLI reports the pre-binding as unhonoured and can still choose a skill through the governed component. Procedure dependencies never grant authority |
| `Pattern.plan` parsed from a stored row | 0.46.0 candidate (H11-C), not published | whole-plan shape limits belong to Shadow's run templates and admission; preserve the generic narrowing property, not HDK's stored-row loop implementation |
| `Pattern.description` and stored description on agents/list | 0.47.0 candidate (H11-D), not published | descriptions belong with run templates; retain human-readable presentation metadata, not HDK's prompt-derived fallback as a required successor contract |
| PostgreSQL `prepared=True` default | 0.45.0 candidate, not published | trusted provisioning separated from DDL-free runtime is a generic storage-adapter boundary; no runtime file-and-shell operation is inherited |

| Native interruption preserving session and turn boundaries (existing contract repaired) | 0.47.2 candidate (H7/BUG-239), not published | **Unknown implementation parity.** The turn boundary is generic; the provider JSONL control line is adapter data and throwaway. No successor implementation is inferred from HDK's source and live verification |

## Not planned, and a real gap — `SinkPort` and proposals

This was D184's *Unknown* row and it is now settled, in the direction that matters most.

**Shadow has no equivalent, and no phase names one.** The 31 files matching `proposal` are three
unrelated senses, **all internal and all inbound**: a strategy proposing the next plan revision
(which *is* journaled); `ModelProposal`, a wire format for one model turn; and `LiveSink`, closest in
*shape* and wrong in *kind* — it carries stream deltas, with no `kind`, no `provenance`, no `grounds`,
and retention `none`.

So the property a product relies on — **the harness proposes and never commits** — is true there only
**vacuously**: Shadow has no skill, rule, compaction, claim or derivation concept, so it commits none
of them. That is not the same as having the boundary, and it means **a product cannot receive them
either**. On current plans phase 55 would **journal** a compaction rather than propose it, and phase
59's skills would have nowhere to go.

**Shadow recommends a Proposal port** — one method, `propose(Proposal{kind, payload, provenance,
grounds})`, outbound, retention `none`, never journaled, conformance-tested like every other port,
beside `LiveSink`; `provenance` is free from the binding and `grounds` maps onto payload-store
handles. The owner decides (Shadow §9.2, lane P's roadmap §5 as *D-N*).

**My view, since this is the row I left unknown rather than guess at:** build the port. The gap is a
governance boundary, not a feature, and Shadow's own note is the decisive one — *without it, those two
phases will each journal what you expect to be proposed, and the boundary will be harder to put back
than to build now.* Six kinds of product artifact become the harness's record by default, and no
product can opt out of a boundary that was never there.

## Resolved differently by design — the Codex fold

D184's other *Unknown*. **Shadow does not fold, and its design forbids folding silently**:
instructions reach a delegated agent through its **agent profile**, which is data, and the ACP /
app-server field; any fallback would be journaled rather than silent. So
`Dialect.instructions_in_prompt` is **throwaway** — it is a quirk of driving one CLI one way — while
the capability it exists for is met by a different and better-governed mechanism.

## The reframing, 2026-10-04 — this is not a list of what Shadow lacks

**Measured in this repository**: `src/shadow_hdk/runtime/environment.py` defines **fifteen operations
by name** in the runtime layer — `read_file`, `write_file`, `edit_file`, `apply_patch`, `move_file`,
`glob`, `grep`, `run_shell`, `run_python`, `run_background`, `job_output`, `kill_job`, `checkpoint`,
`restore`, `list_checkpoints`.

Every one is a file-or-shell operation whose *meaning* the runtime knows — in the layer whose own
boundary rule says that a tool name's meaning belongs behind a port. And none passes the test the
product's own audit stated: *"a coding tool, a support desk or a research assistant could use it
equally."* A support desk does not need worktrees.

**So the *Not planned* and *primitives exist* tables above should be read as what the successor should
**not** inherit, rather than as a gap in it.** Shadow's own answer said this and it was under-read at
the time: *"Shadow has none, by design and not by omission: it governs effects rather than names, and
a file edit or a shell command is a **component** behind the component contract."*

That is a diagnosis and not a reproach. This kit was a bridge built at speed for a shipping product,
those operations are load-bearing for it today, and nothing about them changes — the repository is
maintenance-only. What changes is that the list stops being read as a demand on Shadow.

**Where such tools do belong**, by Shadow's own boundary table: Components, published as a **Pack**,
loaded only when a run asks. Not Core, which owns pure contracts and not product policy; not Runtime,
which explicitly does not own a product-specific agent. Shadow's phase 64 G11 tool preset is already
that shape.

Recorded as **D190** in [`project-rules.md`](/project-rules.md), and cross-repo in
`shadow-ecosystem`'s initiative **0002, generic before product**, which settles D-M and D-N.

## What this means, stated plainly

1. **The parity list is five, not eight, and none of the five is a from-scratch build.** Shadow has
   the primitive for every one; what is missing is the component that emits it, and that is an owner
   decision between Shadow's phase 59 and the product's own adapter. Three of my original eight were
   already there under other words, and two more arrive with run templates before the alpha.
2. **The one true gap is a governance boundary, not a feature.** `SinkPort`'s propose-never-commit
   has no equivalent and no plan, and it gets harder to add the longer two phases journal what a
   product expected to be proposed.
2. **D153 was satisfied in letter and not in substance.** It permitted this bridge *because* each
   phase would say what moves. Seven phases did not say, which is how eight capabilities came to be
   built without anyone deciding whether they survive.
3. **The decision is Shadow's scope, not this kit's.** Nothing here can make a capability migrate.
   The useful output of this document is the list, handed to whoever sets Shadow's phase 59 and 60
   scope, plus the warning that the list is what a product would lose on the day it switches.
4. **For a product integrating today:** put the five file-and-shell rows behind an adapter of your
   own — that is worth doing whichever way the owner decides, because the adapter is the thing that
   makes either answer cheap. The *migrates* table needs no wrapping.
5. **A spec grep cannot find a capability under another name.** Three rows moved for exactly that
   reason. Any future revision of this file should ask the sibling repository rather than only read
   it — which is what this revision did.

## Retirement, and what runs where until then

**D189 — the owner's decision, 2026-10-03** (relayed through lane P, which is the coordination
channel the owner designated; recorded here as theirs rather than as a relayed condition, which is
what an earlier draft of the Codex handoff called it):

| # | Decision | Rationale |
|---|---|---|
| D189 | **`shadow-hdk` retires once Shadow runs on Mac *and* Windows, and at the earliest one release after Intent Studio's switch.** Until then it is the rollback | *The decision is the owner's; the rationale in this cell is this repository's reading of it and is open to correction.* A rollback that cannot run where the product runs is not a rollback, so both platforms are the condition rather than the alpha. One release after the switch is a floor rather than a date — the switch is the risky moment, and the thing being rolled back to has to outlive it |

**What runs where until then**, as lane P describes the plan:

- **Intent Studio's chats and workbench stay on HDK** until Shadow's phase 52 moves them — estimated
  late November to December 2026.
- **New feature types run on Shadow** from its alpha and beta: connections, background runs,
  routines, helpers, images. **Nothing new is built here**, which is the same rule as the *Out* list
  in phase 66's overview and the reason this file's parity tables matter — they are what a product
  would lose on the day it switches.
- **HDK takes maintenance and corrections only.** A correction that makes an existing claim true is
  in scope; a capability is not.

## Keeping this true

Any later bridge phase in this repository adds its contracts to one of the three tables before it
closes. That is D153's requirement and the reason this file exists rather than a paragraph in a
retrospective nobody re-reads.
