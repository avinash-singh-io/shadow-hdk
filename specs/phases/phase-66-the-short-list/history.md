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
