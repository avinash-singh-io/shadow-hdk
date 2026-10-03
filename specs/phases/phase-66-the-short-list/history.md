---
type: History
phase: phase-66-the-short-list
---

# Phase 66 history

### [SCOPE_CHANGE] 2026-10-03 — the last bridge phase: a short list, then maintenance
Topics: scope, maintenance, shadow, lane-p
Affects-phases: none
Affects-specs: specs/phases/phase-66-the-short-list/overview.md
Detail: The owner's decision after lane P's cross-repo plan of 2026-10-03: HDK takes six items —
H10, H11 (confirm then build), H20, H23, H6–H8 — released as 0.45.x, and is then maintenance only:
bugs and the product's pins. H12–H17, H21, H22, H29, H30 and H41–H43 belong to Shadow and are not to
be built here. The owner also set two standing constraints: prefer open-source software where it does
the job, and follow open standards rather than inventing a format where one exists.

---

### [DECISION] 2026-10-03 — D184: H10 is one file, kept current, not a paragraph per phase
Topics: h10, d153, migration, parity
Affects-phases: none
Affects-specs: specs/planning/what-moves-to-shadow.md, specs/decisions/index.md
Detail: G1 complete. D153 permitted this bridge on the condition that each phase say what migrates
and what is throwaway; phases 59–65 did not, so eight shipped capabilities had no planned home and
nobody had decided whether they survive. The correction is one file that *is* the answer and that
every later bridge phase updates before closing — a per-phase paragraph in a retrospective is the
mechanism that already failed. The evidence and the parity list are in
`specs/planning/what-moves-to-shadow.md`; the finding is also appended to phase 65's history, where
the work that found it lives.

---
### [DECISION] 2026-10-03 — D185/D186: the diff cap is the host's, and a cut diff is held, bounded
Topics: h20, diffs, environment, open-standards
Affects-phases: none
Affects-specs: none
Detail: G3. **D185 — the cap is the host's**: `Environment.open(change_diff_bytes=)`, an int or
`None` for the whole diff, defaulting to today's 4096 so nothing existing moves. The old comment
claimed *"a host that needs the whole change reads the file"*, which was never true for a contained
or remote environment — the case this record exists for. All four call sites had taken the default,
so lane P's workbench showed 4 KB per file because nobody could choose otherwise.

**D186 — a cut diff is held whole, by handle, bounded**: `change_diff` is a registered read-class
component paging by `handle`/`start`/`length`, deliberately `recall`'s idiom (D47) rather than a
second shape for the same problem. The hold is bounded (`change_diffs_held`, default 32, the host's)
because keeping every cut diff for an environment's life would hold the content of every file an
agent ever touched — a leak and a privacy problem nobody asked for. A handle exists **only** for a
cut diff, the oldest are evicted first, and asking for an evicted one is refused with *it was
dropped* rather than *no such handle*, which are different facts a host acts on differently.
`whole` reports the uncut size either way, so a host decides whether to ask before asking.

Open standards, per the owner's constraint: unified diff from the standard library's `difflib`, on
the record and through the door alike, so a product parses one format and we invent none.

The derivation moved rather than doubled: `changed` stays pure over two strings with the cutting done
by the environment that owns the cap and the hold, so the diff is computed once.

---

### [DISCOVERY] 2026-10-03 — three weak spots in G3's own tests, found by mutation
Topics: h20, mutation-testing
Affects-phases: none
Affects-specs: none
Detail: The eviction test passed for the wrong reason: its second write appended one line to the
same file, so the second diff was about eighty bytes, the cap never cut it, nothing was held and
nothing was evicted. Rewritten to write wholly different content. `change_diffs_held=0` was
documented as a supported choice with no test, so a mutation deleting the branch survived. And
`whole`'s contract — the **uncut** size — was invisible through an environment, because every
production call now passes `cap=None` and cuts afterwards; it is pinned directly on `changed` instead.
Also covered: `bool` is an `int` subclass in Python, so an unguarded `int(start)` turns `true` into 1
and silently drops the first character.

---

### [DECISION] 2026-10-03 — D187: Codex's strict mode existed all along (H23, ENH-005 closed)
Topics: h23, codex, mcp, capabilities, open-standards
Affects-phases: none
Affects-specs: docs/for-a-product.md, docs/packages/providers.md, specs/backlog/backlog.md
Detail: G4, and it closed by **reading the CLI rather than building anything**. ENH-005, measured
2026-09-12 on `codex-cli 0.154.0`, concluded Codex had no equivalent of `--strict-mcp-config` and
needed one upstream, and shipped that conclusion in the provider record's prose. `codex exec --help`
on that same version lists `--ignore-user-config` — *Do not load `$CODEX_HOME/config.toml`; auth
still uses `CODEX_HOME`*. Three phases were built on a claim that one `--help` would have corrected,
which is the same lesson as every item of phase 65: confirm a claim against the thing itself.

Two properties make it the right flag rather than a blunt one: our servers go in as `-c`
command-line overrides so they survive it (without that a governed run would have no tools at all,
BUG-226's outcome by another route), and auth still uses `CODEX_HOME`, which `backfill_env` already
carried. It is `mcp_strict_args`, the same seam Claude Code uses, applied only when tools are
injected.

`tool_path` stays `uncontrolled` and the **reason** changed: Codex still has no flag to refuse its
own tools, so its native reads remain outside the registry. Both documents that stated the old reason
said the axis was uncontrolled *because configured servers cannot be excluded* — which is now false,
so both were corrected. Raising the axis would be an unmeasured claim and needs a model-accepting
Codex account (TD-020); it is not made.

One consequence named rather than discovered later: the flag drops the whole user config, so a
governed run whose mode names no `model` gets the CLI's built-in default rather than the person's.
Lane P will set `model` explicitly on Codex modes.

---

### [SCOPE_CHANGE] 2026-10-03 — lane P settled H11's order, and B ships as the fix
Topics: h11, scope, lane-p, behaviour-change
Affects-phases: none
Affects-specs: specs/phases/phase-66-the-short-list/tasks.md
Detail: With the owner's agreement, lane P approved G2's recommended order — **A** (validate the
agent name on every path, and report a dropped agent), **B** (the agent's `system` and `tool_names`
honoured on a CLI, intersected with the mode's and never widening), **E** (`skill` on the row), **C**
(`plan` on the row), **D** (`description` on the row) — and accepted G2's recommendation on **F**:
`model` and `effort` stay on the mode, and the product composes a mode from the agent's default and
the conversation's choice through its own port.

B is a behaviour change and ships **as the fix, with no opt-in flag**, which lane P chose when
offered one. Today a mode naming an agent on a CLI does nothing, silently; afterwards it applies that
agent's instructions and tool narrowing. A flag would have been a way of keeping the bug. Lane P will
check any mode carrying an agent before pinning 0.45.x.

---
### [DECISION] 2026-10-03 — H11-A: the name is resolved on every path, and a drop is named
Topics: h11, agents, d176, honesty, wire
Affects-phases: none
Affects-specs: specs/phases/phase-66-the-short-list/tasks.md
Detail: G5-A, in lane P's approved order. Two defects, one cause: `_agent_named` returned early
whenever the host had no model — every CLI host — and `patterns.named`, which is the whole of D176's
refusal, sat on the line *after* that return. So a mode naming `"reviewr"` on Claude Code or Codex
was accepted in silence; D176's claim was true on a key-backed host and false on a CLI. Fixed by
resolving before deciding, which costs one store lookup and makes the refusal true everywhere it is
claimed.

And a dropped agent is now named. `agent_unhonoured(wanted, chosen=)` is the counterpart of
`agent_recorded`, and exactly one of the two is ever set: `agent` says what ran, the new field says
what could not. It is on `ThreadRecord` so a resume reports it too, and it crosses in
`thread/start`'s reply beside `agent`, because a product over the wire needs it as much as one in
process. Before this a product that named an agent and received the CLI's own loop had no field to
read at all — the shape of ENH-051 and BUG-229 both.

The wire-parity invariant caught the new public property before it could ship unaccounted for, and
one surviving mutation showed `wanted and not chosen` carried a redundant guard, now gone.

---

### [DISCOVERY] 2026-10-03 — D184 revised from Shadow's own reading; the parity list is five, not eight
Topics: h10, d184, parity, shadow, sink-port
Affects-phases: none
Affects-specs: specs/planning/what-moves-to-shadow.md
Detail: Shadow's session answered D184 row by row **from its source rather than its specs**, and
five rows moved. The lesson is methodological and belongs in the file: **a spec grep answers *is this
name present* and cannot answer *is this capability present under another name*.** Three of my eight
"not planned" rows existed there under other words — `tools_offered` as plan grants, the tool face
and a journaled per-turn projector narrowing; `silence_seconds` as a stall deadline reset by stream
progress, with approvals as durable parked decisions (so D182's point holds there structurally);
`update_plan`'s durable half as journaled `PlanRevisionAdmission`. Two more arrive before the alpha as
**run templates** (64 G5.1), which are our agent rows minus store CRUD and minus the mode indirection.

The remaining five are one group — file and shell tools — and Shadow has the **primitive** for every
one, so none is a from-scratch build: the payload store answers H20's harder half directly, and
owned async acts plus owned-resources-by-scope are the hard part of background jobs, checkpoints and
worktrees. Who writes the component is an owner decision between Shadow's phase 59 and the product's
adapter.

And the `Unknown` row is settled in the direction that matters: **Shadow has no `SinkPort`
equivalent and no phase names one**, so propose-never-commit is true there only vacuously — it holds
none of the six kinds because it has none of the concepts. Shadow recommends a Proposal port; I
recorded my own view that it should be built, because the gap is a governance boundary rather than a
feature and phase 55 would otherwise journal a compaction a product expected to be proposed. The
Codex fold is settled too: Shadow does not fold and forbids folding silently, so
`instructions_in_prompt` is throwaway while the capability is met by its agent profile.

---
### [DECISION] 2026-10-03 — D188: an agent's role and tool list compose into a CLI's behaviour
Topics: h11, agents, cli, instructions, narrowing, d14
Affects-phases: none
Affects-specs: none
Detail: G5-B, and G2's estimate held: no new mechanism, only the composition. A CLI gets everything
but its own loop — instructions through the flag-or-fold path (0.38.0, 0.41.0, measured live) and a
tool list through the registry narrowing (0.44.0) — and both shipped before this. What was missing is
`carried_into`, a pure derivation with two rules.

**Instructions layer, agent first**, reusing D168 rather than reinventing it: the role is who the
agent is and the mode is what this run wants of it, so a mode's aside must not outrank the role.
**Tool lists intersect and never widen**, because both are allow-lists over one registry and D178
made narrowing safe by applying it last so it can only take away; two allow-lists where the later
widened the earlier would let a mode be handed more than its policy left by naming an agent. The
mode's order is kept — a catalogue with two sources of ordering has none.

Composed in **one place**: `Conversation._behaviour_for_the_provider`, which runs at open and at every
reopen, and a reopen is what a `set_mode` performs. One place because two paths deciding the same
thing is exactly what H11-A's defect was. The runtime never learns what a `Pattern` is — the host
hands it `Carried`, two plain fields, which the layering invariant requires and which also leaves room
for E's `skill`.

Two findings. A surviving mutation showed the no-instructions case was only ever tested against an
empty `system`, so prepending nothing was invisible — and with a non-empty one it would have put a
blank line at the head of what reaches a CLI's `--system-prompt` flag and is paid for. And widening
the chooser's return **broke four existing doubles**, which is D14's rule catching me: a chooser is a
callable a host supplies, so the third element is read where offered and defaulted where not, rather
than required. Phase 64 broke twenty-two doubles the same way; this time the test suite said so
immediately.

---

### [NOTE] 2026-10-03 — handed over, with the two tools the project kept rebuilding
Topics: handover, tooling, mutation-testing
Affects-phases: none
Affects-specs: specs/phases/phase-66-the-short-list/handover.md
Detail: The phase is handed over mid-G5 at the owner's request, with E, C and D still to build, then
G6's H6–H8 and G7's release. [`handover.md`](handover.md) is self-contained: nothing in it depends on
a session transcript, the design for E/C/D is G2's already-approved one, and it lists the traps this
phase and the last one actually hit rather than general advice.

Two scripts went into `scripts/` on the way out. `project-rules.md` requires every assertion to be
mutation-checked and the repository had no tool for it, so each session wrote its own — phase 64's
got it wrong three times, including one **vacuous** pass where a shell function never passed its
arguments and all seven mutations reported success. `mutate-one.py` exits non-zero on a missing or
ambiguous anchor, which is exactly the property those three lacked. `reflow-long-lines.py` exists
because hand-wrapping prose to satisfy the formatter cost this session more round-trips than anything
else it did.

Gate at hand-over: ruff 0, format 0, mypy strict 0 over 511 files, 2200 passed, 20 skipped.

---

### [NOTE] 2026-10-03 — the tracking debts this phase had accrued, cleared before the hand-over
Topics: rule-2, rule-3, d184, changelog, backlog
Affects-specs: specs/changelog/2026-10.md, specs/backlog/backlog.md, specs/planning/what-moves-to-shadow.md
Detail: An audit before handing over found three things owed rather than done, and they are worth
naming because all three are rules this project has for a reason.

**Rule 2:** six commits of work and **no changelog line**. Logged now, which means it was written
from the history and the diffs rather than from the work — the reconstruction cost Rule 2 warns about,
paid in full.

**Rule 3:** H11-A's defect was found, fixed and committed inside G5-A, and **filed afterwards** as
BUG-236. The row says so. A defect filed after its fix is a weaker record than one filed when found,
because the filing is what makes the finding independent of whoever happened to fix it.

**D184, this phase's own decision:** `what-moves-to-shadow.md` did not carry phase 66's contracts.
Handing over a file that violates the decision stated inside it would have been the exact failure H10
exists to name — seven phases skipping the statement is how eight capabilities came to have no planned
home. It now has an *Added by phase 66* table, and two of our new mechanisms are recorded as
**throwaway with the capability met**: the in-memory hold for cut diffs, where Shadow's payload store
is content-addressed and erasable, and the Codex strict flag, where Shadow's tool face is structural.
The row for E, C and D says that whoever builds them updates it.

---

### [DISCOVERY] 2026-10-03 — BUG-237: the PostgreSQL adapters cannot run under a restricted role
Topics: postgres, ddl, production, lane-p, p0
Affects-phases: none
Affects-specs: specs/backlog/backlog.md, specs/phases/phase-66-the-short-list/handover.md
Detail: Reported by lane P as their Intent Studio BUG-280, blocking their 0.7.0, and **confirmed
against the source before answering**. `Pooled.pool()` executes its schema on first use and again
after every `aclose()` — `aclose` sets `_ready = False` — which is precisely the *first and reopened
access* they measured. Three adapters do it through `Pooled` and the fourth calls LangGraph's
`AsyncPostgresSaver.setup()`; five tables of ours plus LangGraph's four is the nine they report.

The subtle part, which they had right and which decides the fix: `CREATE TABLE IF NOT EXISTS` is
**not** DDL-free, because PostgreSQL checks the CREATE privilege before the existence check — so it
fails with 42501 against a table that already exists, which is why pre-provisioning did not help. The
fix cannot be *make the DDL conditional*; it must be *do not execute the schema at runtime*. Taking
the obvious reading would have shipped them something that still failed.

Recommended as **0.44.1 from the v0.44.0 tag**, not 0.45.x: their release is otherwise ready and this
branch still carries H6–H8 whose scope is deliberately unconfirmed and therefore undatable. Two
design questions were put to lane P rather than decided for them — whether runtime verifies the
schema (one catalogue query, turning *the schema is behind* into a named startup error) and whether
DDL-free becomes the default, which would invert behaviour for anyone relying on auto-setup. Also
flagged: LangGraph's `setup()` is third-party, so `prepare` must call it under the owner role and must
be re-run on a LangGraph upgrade, not only on ours.

Who builds it is the owner's call, open at the time of writing.

---
### [NOTE] 2026-10-03 — HDK's work moved to a Codex lane; the cold-start handoff written
Topics: handoff, codex, bug-237, maintenance
Affects-specs: specs/handoffs/2026-10-03-to-the-codex-lane.md, specs/status.md
Detail: The owner moved HDK's work to a Codex session, relayed by lane P, which also settles who
builds BUG-237: that lane, not this one. Nothing was started on it here.

`specs/handoffs/2026-10-03-to-the-codex-lane.md` is the cold-start document and `specs/status.md`
links it from the top, because a Codex session **cannot receive cross-session messages** — so the
repository is the only channel. Status goes in `status.md` and replies in `specs/epics/`, which lane P
reads from git.

It leads with BUG-237 as 0.44.1 from the `v0.44.0` tag, with all seven agreed points, then 0.45.x's
remainder, then the standing rules, then the traps that cost phases 65 and 66 real time. One wording
is marked as relayed rather than owned: HDK retiring *once Shadow runs on Windows* is lane P's, and
this repository has no independent record of it — a handoff is the wrong place to launder someone
else's condition into a fact.

Gate at hand-over: ruff 0, format 0, mypy strict 0 over 511 files, 2200 passed, 20 skipped.

---
### [DECISION] 2026-10-03 — D189: retirement is the owner's decision, and the release becomes a train
Topics: d189, retirement, release-train, d9, versioning, maintenance
Affects-specs: specs/planning/what-moves-to-shadow.md, specs/decisions/index.md, specs/handoffs/2026-10-03-to-the-codex-lane.md, specs/status.md
Detail: Three things the owner settled, relayed through lane P, folded into the Codex handoff.

**D189 — retirement.** `shadow-hdk` retires once Shadow runs on **Mac *and* Windows**, and at the
earliest **one release after Intent Studio's switch**; until then it is the rollback. Recorded as the
owner's own decision, which replaces the earlier handoff's marking of the Windows condition as merely
relayed — that marking was right when the condition had no owner and is not right now. Both platforms
rather than the alpha, because a rollback that cannot run where the product runs is not a rollback;
one release after the switch is a floor rather than a date, because the switch is the risky moment.

**The release train.** Small releases every few days: 0.44.1 first, then one item per release — E, C,
D, then H6–H8, each confirmed before being built — with the DDL-free default flip in the first 0.45
release and a note in `specs/epics/` for each so Intent Studio pins the latest.

**And a collision found while writing it down.** Lane P's shorthand was *"0.45.x item by item"*, and
D9 says that pre-1.0 **a contract change is a minor bump**. E, C and D each add a field to the agent
row, so on D9 the train is `0.45.0`, `0.46.0`, `0.47.0` — a run of **minors**, not `0.45.1` and
`0.45.2`. The handoff says so and tells the next lane not to pick one quietly: either follow D9 and
tell lane P the sequence is minors, because they are planning pins around the string "0.45.x", or have
the owner amend D9, which is a decision with their name on it. Writing `0.45.1` for a contract
addition without amending D9 would make the version number mean two things in one repository.

---
### [NOTE] 2026-10-03 — the D9 question settled: the train is minors
Topics: d9, versioning, release-train, lane-p
Affects-specs: specs/handoffs/2026-10-03-to-the-codex-lane.md, specs/planning/what-moves-to-shadow.md
Detail: Lane P settled it the way D9 already said: **follow D9**, so the train is `0.45.0` (the
DDL-free flip), then `0.46.0`, `0.47.0` as minors, with patches only where a release adds no contract.
They updated their roadmap, initiative 0057 and their own Codex handoff to match, so nobody is pinning
against the string "0.45.x". The handoff no longer presents this as an open question — leaving a
settled question open invites the next lane to re-litigate it, and the thing that matters now is
keeping it true rather than deciding it again.

Also, D189's rationale is marked as **this repository's reading** rather than the owner's words. The
decision is theirs; the *why* in that cell was written here, and a cold reader should be able to tell
which is which before relying on either.

---

### [DECISION] 2026-10-03 — Handoff #001 → shadow
Topics: orchestration, handoff, handoff-001
Affects-phases: phase-66-the-short-list (or "none")
Affects-specs: ../shadow/.momentum/inbox/handoff-001.md
Detail: Handoff #001 written to shadow/.momentum/inbox/. Summary: HDK is maintenance-only and handed to a Codex lane. Two decisions now sit with Shadow: D-M (who builds the five file-and-shell tools) and D-N (whether to add a Proposal port). D189 makes Windows a retirement condition, so Shadow phase 50 is on the critical path.

---

### [NOTE] 2026-10-04 — Codex pickup: E confirmed before building
Topics: agent-patterns, skills, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Clean branch at 08437fe. Source confirms the row-to-model binding gap; follow the approved CLI-only-own-skills boundary and name the unhonoured binding. Baseline gate running; E starts test-first, with C/D/H6–H8 held for later releases.

---

### [FEATURE] 2026-10-04 — E binds the existing procedure, without a new decision
Topics: agent-patterns, skills, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: The owner confirmed the approved binding-versus-choosing boundary and appended the clarification to E's evidence. New cases started red, then 17 passed; 37 PostgreSQL/store tests passed on a disposable server. Mutation checks proved the bound procedure reaches inference and unmet needs prevent it. C/D/H6–H8 stay out of this release.

---

### [NOTE] 2026-10-04 — 0.45.0 checkpoint gated, owner landing remains
Topics: skills, release-train, postgres
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Full gate passed with disposable PostgreSQL enabled: 2,238 passed, 8 skipped, 24 deselected; lint, format and strict types passed. All 17 new cases passed on a clean installed wheel outside the checkout, and twenty retained mutations bite. Release checkpoint evidence and owner commands are prepared; phase 66 remains open, and 0.45.0 is not published.

---

### [NOTE] 2026-10-04 — Freeze independently landable release checkpoints
Topics: release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: The owner requested continued autonomous implementation without waiting for publication. Each candidate is frozen on a codex/release branch; land parent-first, one release at a time. Correct the 0.45.0 instructions to use its frozen release branch rather than the moving phase branch.

---

### [FEATURE] 2026-10-04 — C confirmed and implemented test-first
Topics: agent-patterns, plans, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: The loader rejected stored plan limits while existing child admission consumed Pattern.plan. Six new cases failed on that gap before adding the approved contract parsing path; execution is counted under a stored bound. No absorb or offload_over row knobs are added.

---

### [NOTE] 2026-10-04 — C checkpoint verified for 0.46.0
Topics: plans, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Full gate passed: 2,248 passed, 8 skipped, 24 deselected with disposable PostgreSQL enabled; lint, format and strict types passed. Ten new cases pass on the clean installed wheel and ten mutations bite. Freeze the candidate separately for parent-first owner landing; D and H6–H8 remain, and no release is claimed published.

---

### [FEATURE] 2026-10-04 — D confirmed and wired test-first
Topics: agent-patterns, descriptions, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Five new cases failed before adding the approved optional description field. Stored text now reaches the existing agents-list reply; absent or null retains the old derivation and explicit empty text is kept. Role instructions remain separate, and this is D's own release item.

---

### [NOTE] 2026-10-04 — D checkpoint verified for 0.47.0
Topics: descriptions, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Full gate passed with disposable PostgreSQL: 2,254 passed, 8 skipped, 24 deselected; lint, format and strict types passed. Six new cases pass on the clean installed wheel and seven mutations bite. Freeze this separately for parent-first owner landing; H6–H8 remain, and publication is not claimed.

---

### [DISCOVERY] 2026-10-04 — H6 confirmed as BUG-238
Topics: context-fragments, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: A mode row retains dictionaries and shared assembly raises AttributeError. The existing store-put wire path already transports these rows, so the fix is typed decoding of the existing fragment contract, planned separately as 0.47.1.

---

### [NOTE] 2026-10-04 — H6 decoding repaired test-first
Topics: context-fragments, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Five cases red, then six green through the existing wire-store and shared assembler path; 118 mode tests pass. Ten anchored mutations bite. The patch candidate is 0.47.1, with the D184 map updated; full gate and installed-artifact verification are underway.

---

### [NOTE] 2026-10-04 — H6 checkpoint verified for 0.47.1
Topics: context-fragments, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Full gate passed with disposable PostgreSQL: 2,260 passed, 8 skipped, 24 deselected, lint/format/types clean. Six new cases pass against a fresh installed wheel and ten mutations bite. Schemas and TypeScript regenerate without drift; H7/H8 remain and owner publication is pending.

---

### [DISCOVERY] 2026-10-04 — H7 confirmed as BUG-239
Topics: provider-interruption, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Claude Code advertises native interrupt but its dialect sends no line, so cancellation closes the process. The cancelled reader also leaves interrupted frames for the next turn if only a line is added; verify both transport and turn boundaries before fixing. Official SDK control-request format checked.

---

### [NOTE] 2026-10-04 — H7 repaired and measured live
Topics: provider-interruption, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Two new cases failed first, then passed; all 74 JSONL cases pass and seven mutants bite. Claude Code 2.1.187 accepted interruption, kept the same process and session, and answered the following turn with SECOND_OK. Prepare 0.47.2 separately; full gate and installed verification underway.

---

### [NOTE] 2026-10-04 — H7 checkpoint verified for 0.47.2
Topics: provider-interruption, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Full gate passed: 2,264 passed, 8 skipped, 24 deselected with disposable PostgreSQL; lint/format/types clean. Four final installed-wheel cases pass and eight mutants bite; the completion-during-write case guards the cleared boundary. Source and installed live Claude Code 2.1.187 keep their process/session and answer the following turn. H8 remains; publication is pending.

---

### [DISCOVERY] 2026-10-04 — H8 confirmed as BUG-240
Topics: usage-accounting, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: The loop initializes, aggregates and emits only three usage fields; the model-session adapter reconstructs only those three. Cache counters already exist in Usage and runtime metering, so repair the adapter path and prove model responses through thread records and wire output, separately as 0.47.3.

---

### [DISCOVERY] 2026-10-04 — TD-021, mutation bytecode cache
Topics: testing, usage-accounting
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Same-size source edits in one second can reuse cached bytecode in a new Python process; a three-read reproduction reports 1, 1, then 2 after cache removal. File TD-021 and verify this train with source bytecode cleared before every anchored mutant and writes disabled. H8's twenty mutations now bite; earlier checkpoint assertions are being rechecked under that precaution.

---

### [NOTE] 2026-10-04 — H8 adapter path repaired test-first
Topics: usage-accounting, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Nine new cases failed before production changes; ten now pass on source and a fresh installed wheel outside checkout. Twenty H8 mutants and all 55 earlier train mutants bite with source caches cleared before each. Existing runtime metering and wire shapes suffice; prepare 0.47.3 separately, with full gate underway.

---

### [NOTE] 2026-10-04 — Correct the verified stale BUG-237 status
Topics: postgres, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: The backlog still marked BUG-237 open although its ad-hoc record documents v0.44.1 and both published distributions. Fresh GitHub release evidence confirms v0.44.1 published, non-draft, and still latest; correct only the row's status/phase cells, preserving its historical detail. The default flip is separately verified in the 0.45.0 candidate.

---

### [NOTE] 2026-10-04 — H8 verified; authorized train preparation complete
Topics: usage-accounting, release-train
Affects-phases: phase-66-the-short-list
Affects-specs: none
Detail: Full gate passed with disposable PostgreSQL: 2,274 passed, 8 skipped, 24 deselected; lint/format/types clean. Ten installed cases, twenty H8 mutants and all 55 earlier train mutants pass the cache-safe check. G1–G6 implementation is complete; prepare frozen 0.47.3 and audit all candidate refs/notes/evidence. G7 owner publication and phase closure remain outside this goal's authorization.

---

## Release execution authorized — 2026-10-04

The owner instructed this lane to release all six versions. Staging/main landing and GitHub
Release 0.45.0 completed after a fresh merged-tree gate (2,238 passed) and green CI 37159639057.
The clean-runner wire-test defect was reproduced, repaired and both assertions mutation-checked;
production sources still match the frozen candidates. PyPI workflow 37160034400 is running.
Advance to 0.46.0 only after seven-file and outside-CI fresh-install verification.
