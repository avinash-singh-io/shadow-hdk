---
type: History
phase: phase-65-the-claims-are-true
---

# Phase 65 history

### [SCOPE_CHANGE] 2026-10-02 — Wave 1 only, from a forty-item audit
Topics: audit, scope, native-line
Affects-phases: none
Affects-specs: specs/phases/phase-65-the-claims-are-true/overview.md
Detail: Lane P's audit of 2026-10-02 lists forty items. The decision taken was to build only its
A-group — claims this kit already makes that are not true — on the ground that new capability
belongs to the native line rather than to a maintenance-supported implementation. Every other item
is named in the overview's **Out** so no later reader mistakes it for an oversight.

---

### [DISCOVERY] 2026-10-02 — five claims confirmed false against the source, three of them mine
Topics: honesty, behaviour, tools-offered, model-port, conversation, timeout, agents
Affects-phases: none
Affects-specs: specs/backlog/backlog.md
Detail: BUG-230 through BUG-234 filed after reading the source rather than trusting the audit —
the audit itself asked for that. `tools_offered` narrows nothing while two fields report it
honoured (phase 62, mine); `request.model` is discarded by the only real `ModelPort` while phase 62
claimed otherwise (mine); a key-backed conversation opens fresh every turn with nothing saying so;
a 600s ceiling counts a person's thinking time and blames the provider; and phase 64's agent
selection survives neither `set_mode` nor a resume (mine, and it bounds what 0.43.0 delivered).
TD-020 records the one Wave 1 item that cannot be closed here — Codex's fold is unmeasurable on
this laptop's account.

---
### [ARCH_CHANGE] 2026-10-02 — the narrowing lives in two catalogues, by one derivation
Topics: tools-offered, narrowing, offer, registry, catalogue
Affects-phases: none
Affects-specs: none
Detail: BUG-230 could have been closed in `AgentSession.catalogue` alone, and that would have left
the claim false for every provider a product actually runs: Claude Code and Codex are handed no
catalogue — they **list the registry over MCP** and decide for themselves. So the kernel gains one
pure derivation (`narrowed`/`unanswered`) and it is applied twice: in the in-process catalogue, and
on the offer that answers a CLI's listing, through a settable `narrow_to` that the conversation sets
at open and again at every `set_mode`. Settable rather than a construction argument the way
`withhold` is, because the narrowing travels on the mode and a mode changes mid-thread. `Narrowing`
is a separate `runtime_checkable` Protocol rather than a method on `Offer`, so a host that wrote its
own offer against that port still satisfies it (D14).

---

### [DISCOVERY] 2026-10-02 — the `tools_offered` union in `unmapped_behaviour` was dead code
Topics: honesty, mutation-testing, tools-offered
Affects-phases: none
Affects-specs: none
Detail: `unmapped_behaviour` unioned `"tools_offered"` into its `mapped` set, which read as *this is
delivered elsewhere*. A mutation deleting the union **survived**: the function walks five field names
and `tools_offered` is not one of them, so the union could never change an answer. The lie was not
merely false, it was inert — and the test that first covered it passed vacuously. Both were fixed:
the dead union is gone, and the test now pairs a narrowing with a `temperature` the CLI genuinely
cannot take, so exactly one name comes back and it is the other one. Two further equivalent mutants
(redundant empty-offered guards) were resolved by deleting the guards rather than by inventing tests
that could not distinguish them.

---
### [DECISION] 2026-10-02 — `model` is the port's answer, not a constant
Topics: model-port, honesty, langchain, selects-model
Affects-phases: none
Affects-specs: none
Detail: D180 held: no kernel change, because `ModelRequest.model` was always there — what was
missing is an adapter that reads it. `LangChainModel` now builds a chat model for the asked-for spec
and caches one per spec, with the host's own keyword arguments carried over so a second spec on an
OpenAI-compatible endpoint still gets its `base_url` and key. The `over()` seam genuinely cannot be
re-specified, so it reports `selects_model` false and the run names `model` as unhonoured —
`unmapped_for_a_model` gained a `selects_model` argument and `_ModelSession` asks the port instead of
assuming. The default is **true**: `model` is a request field, so a port is expected to read it, and
the kit's own adapter is the one that has to be accurate. Phase 62 reported it honoured
unconditionally while the only real adapter discarded it (BUG-231).

---
### [DECISION] 2026-10-02 — a key-backed model's continuity is its transcript, as a CLI's is its session id
Topics: conversation, transcript, model-agent, reopen, compaction
Affects-phases: none
Affects-specs: none
Detail: D181 landed as structured messages rather than as seeded text. The loop is built fresh every
turn, so the transcript lives on the `_ModelSession` that outlives it — everything after the system
message, so the role is rebuilt per turn and a `set_mode` is never shadowed by a stale one. A
provider reopen (which `set_mode` does) would have dropped it, so `Conversation` keeps it over a
reopen exactly as it keeps `session_id`, through a duck-typed `_remember_transcript` /
`_give_the_transcript_back` pair — set on the session rather than passed to `open()`, because every
CLI adapter's opener would refuse the keyword and that is how phase 64 broke twenty-two doubles.

One latent bug came with it and was caught by a surviving mutation: `_compact` kept `messages[:2]`
with the comment *the role and the brief — `work()` puts them first and in that order*. With a
transcript between them that slice is the role and the **oldest carried message**, so the request the
model was answering would have been summarised away while a stale one was kept. The brief's position
is recorded now, and survives a park.

---

### [DISCOVERY] 2026-10-02 — a resumed key-backed thread still forgets, and ENH-052 filed
Topics: conversation, transcript, resume, budget
Affects-phases: none
Affects-specs: specs/backlog/backlog.md
Detail: Two things this group deliberately did not close. A thread resumed in a **new process** has
no carried transcript and `_seed_if_fresh` only seeds a fork (`seeded_turns > 0`), so it starts
empty — that belongs with BUG-234's resume work in G5, where the record is already being changed, and
is handled there rather than twice. And the carried transcript is **unbounded**: ENH-052 records the
interaction with a token budget and compaction, which are the audit's H33/H34 and outside Wave 1.
Filed at the moment the risk was introduced, and named in the comment that introduces it.

---
### [DECISION] 2026-10-02 — the ceiling measures silence, not work
Topics: timeout, patience, jsonl, approvals, behaviour
Affects-phases: none
Affects-specs: none
Detail: D182 landed as a change of *what is measured* rather than a bigger number. One
`asyncio.timeout(600)` wrapped the whole wait, so a turn was failed for taking long — and a turn is
not a failure for being long. What a ceiling is for is a hung process, and a hang is silence, so the
deadline is rearmed on every frame the CLI writes: a provider that keeps streaming is never given up
on, however long the run takes, and one that stops is given up on after `silence_s`. The default
moved to 1800s **because the number now means something else** — leaving 600 would have invited the
next reader to assume nothing had changed. A mode sets its own through
`Behaviour.silence_seconds`, which is where `tools_offered` already lives: a field the kit honours
itself, because no CLI has a flag for our patience.

The second half was a person's time. `Routing.call` now reports how long it took, and the
conversation wires that to the session's `waited_for_us`, which pushes the deadline out — because a
CLI waiting for a tool call is waiting for **us**, and that call may be put to a person who takes
twenty minutes (D58). Both ends are read by name, so a key-backed session (no pipe to go quiet on)
and a host's own `Offer` are left alone. A surviving mutation showed the `hasattr` guard untested; it
guards a `__slots__` offer, which now has a test, because without the guard a thread opened on one
fails at open.

---
### [DECISION] 2026-10-02 — the agent is on the record, and the runtime is handed a chooser
Topics: agents, modes, resume, set-mode, layering
Affects-phases: none
Affects-specs: none
Detail: D183 landed in three pieces. `ThreadRecord.agent` carries which agent a thread runs, and
`Thread.agent` became a property over it, so an attribute and a column cannot disagree. `set_mode`
asks for the mode's agent again through a `choose_agent` callable the host hands in — resolving a name
to a loop is `ServeHost`'s business and the runtime is not learning about patterns to do it — and an
unknown name on the new mode refuses by raising, the D176 cut at the second door that selects one.
`ServeHost.resume` resolves from `record.agent` rather than falling through to its own default.

Two things the mutation pass found. A test asserting the override survives a switch was **vacuous**:
it switched into a mode naming the same agent as the override, so dropping the override entirely
passed. And once that was fixed, the initial value of `_agent_override` was still unreachable — which
exposed a real gap rather than a dead line: a *resumed* thread had no override at all, so a `set_mode`
after a restart followed the new mode while the same switch before it kept the override.
`ThreadRecord.agent_override` closes that, and `_agent_override` is a property over the record too.

The invariants earned their keep twice: `test_the_runtime_imports_no_adapter` caught `agent_now`
being imported into `runtime/conversation.py`, so both pure decisions moved to `kernel/threads.py`
and the adapter re-exports them; and the wire-parity invariant caught `Thread.agent` becoming public
surface that neither crossed nor said why.

---
### [NOTE] 2026-10-02 — the skips say what they need, and the live legs were run
Topics: codex, measurement, skips, release
Affects-phases: none
Affects-specs: docs/migrations/0.44.md
Detail: TD-020's two live tests now skip with a message naming the account required (any ChatGPT or
OpenAI account on which Codex accepts a model), what the measurement would prove, and the debt's own
id — a silent skip is how an unmeasured claim stays unmeasured. The two Claude Code legs were run
live for this release and passed: with `--system-prompt` removed from its record the fold is the only
way in, and the paired negative shows the sentinel is not something the model says anyway.

Also corrected here: `specs/status.md` still headlined v0.42.0 while 0.43.0 had been tagged, merged
and published. Lane P's audit flagged exactly that (its H9) and was right; its companion claim that
0.43.0 is untagged and unpublished is now stale, and the reply says so.

---
### [DISCOVERY] 2026-10-02 — the narrowing reached a CLI's calls but not its listing (BUG-235)
Topics: tools-offered, narrowing, recording-server, listing
Affects-phases: none
Affects-specs: specs/backlog/backlog.md, docs/migrations/0.44.md
Detail: Found while answering lane P's BUG-258 (*Claude Code gets no tools in the installed desktop
app*), by re-reading G1 against the code path that defect lives in. `Routing.shows()` was built as
*the* predicate for what a provider may see and call, and `Routing.call` used it — but
`RecordingServer.tools()`, the thing that actually answers a CLI's `tools/list`, still filtered by
`withheld` alone. A narrowed Claude Code was therefore served the whole catalogue and refused *no
component named …* on anything it used. The G1 tests missed it because they asserted on the refusal
and never on the length of the served list: the narrowing was tested through the door that refuses
and not the door that offers. Fixed, with two mutations biting. The lesson is the general one — a
narrowing has two doors, and a test has to walk both.

---

### [NOTE] 2026-10-02 — lane P's BUG-258 answered, and verified rather than recalled
Topics: bug-258, relay, no-tools, approvals, release
Affects-phases: none
Affects-specs: specs/epics/0011-reply-to-lane-p-2.md
Detail: *Claude Code gets no tools in the installed desktop app* is the symptom of BUG-226 (a relay
path containing a space split into a command and its arguments) and its sibling BUG-227 (the ACP
transport dropping `ToolSource.env`), both closed in **0.34.2** — and lane P pins 0.34.1, so the
version they are looking for is 0.34.2 or later. Verified rather than recalled: the eleven tests in
`tests/adapters/test_the_relay_reaches_the_child.py` cover the spaced path on all three transports,
the port and token travelling with the source, and the relay being resolved beside the running
interpreter before `PATH`, and all eleven pass on this tree. Their other half — *does "Ask first"
still stop* — was checked the same way: the 52 approval and park tests pass, which matters because
this phase's G4 wrapped exactly that call path.

---
### [NOTE] 2026-10-03 — the runway was one doc commit divergent, and a lane row was stale
Topics: release, landing-order, status
Affects-phases: none
Affects-specs: specs/status.md
Detail: Two things found in the landing pre-flight rather than during a protected-branch merge.
`origin/main` carried `8e7b880` (*the phase 62 retrospective named a note that is not in its tree* —
the fix for the v0.41.0 red tag) and `origin/staging` never received it, so the two had diverged by
one commit of content. Merged into this phase's branch first, where a conflict would have been
cheap, rather than discovering it on `main`.

And the Active Phase table still described phase 64 as *complete, unmerged* when v0.43.0 was tagged,
merged and published on 2026-10-02. Corrected to *released as v0.43.0*. Rule 15 keeps a lane out of
another lane's row, but phase 64 is not an active lane — it is a released one, and a row asserting
something untrue about a shipped release is worse than the convention it protects.

---
### [DECISION] 2026-10-03 — H10 answered: eight shipped capabilities have no planned home
Topics: h10, d153, migration, shadow, parity
Affects-phases: none
Affects-specs: specs/planning/what-moves-to-shadow.md, specs/decisions/index.md
Detail: Written after this phase closed, on the owner's instruction, because the finding came out of
this phase's work and the evidence existed only in two session transcripts. D153 permitted this
bridge on one condition — *each phase stating what migrates and what is throwaway* — and phases 59
through 65 did not state it, this one included. So it was satisfied in letter and not in substance,
and that is how eight capabilities came to be built without anyone deciding whether they survive.

The evidence, from `shadow` at `origin/main` plus `phase-64-models-and-tools`: Shadow's **Phase 59**
is the only phase chartered to bring this kit's work across (*"After the alpha, bring the
capabilities already built in `shadow-hdk` into the new architecture"*), and its named scope is ACP,
Agent Skills/`SKILL.md`, `AGENTS.md` and OKF bundles, and OpenTelemetry — **none of the eight**.
Phase 59 is `planned` and depends on Phase 51, which **is** the alpha and is itself `planned`; Phase
61 (hardening, before the alpha) is `planned`; Phase 64 is `in-progress`.

The parity list: `change` diffs on the record, `apply_patch`, `run_background`/`job_output`/`kill_job`,
`checkpoint`/`restore`/`list_checkpoints`, `open_worktree`/`close_worktree`, `update_plan`,
`tools_offered`, `silence_seconds`, agents as store rows, and `ThreadRecord.agent`. Each appears in
**no** Shadow phase in any file.

Two method notes, because counting nearly misled this: a term in a phase's `overview.md` is scope
while a term only in its `history.md` or `evidence/` is a record, which is not a plan; and the
generic words had to be read for sense — `checkpoint` in Shadow is the durable engine's state and "an
internal checkpoint, not a supported release", and `worktree` is a development worktree in
`repository-layout.md`. `SinkPort` and the Codex fold are recorded as **unknown** rather than guessed.

D184 names the decision; `specs/planning/what-moves-to-shadow.md` is the statement, and any later
bridge phase adds its contracts to it before closing.

---
