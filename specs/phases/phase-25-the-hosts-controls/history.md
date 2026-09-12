---
type: History
phase: 25
---

# History — Phase 25

### [NOTE] 2026-09-12 — opened
Topics: thread, turn, item, activity, modes, approvals, store
Affects-phases: phase-25-the-hosts-controls
Affects-specs: none
Detail: Opened from `planning/the-substrate.md` (accepted 2026-09-12). Group 1 first: the industry's terms as one contract change, because every later group names things.

---

### [DECISION] 2026-09-12 — D61: the record speaks the industry's words

Topics: terminology, thread, turn, item, approval, input, reasoning, usage
Affects-phases: phase-25-the-hosts-controls
Affects-specs: architecture/runtime.md#modules, architecture/wire.md, decisions/index.md

Where the industry has a term, we use it; where the thing is ours — governance by effects, the
lease, the sink, provenance, posture — we keep the word and document the mapping; invented names go
(`planning/the-substrate.md` §1.9). Applied as one contract change, 0.21.0: event kinds
`reasoning` (was `reasoned`), `usage` (was `spent`), `approval_requested` (was `asked`, carrying
component and inputs from D59), and a thirteenth, `input_requested` — the agent's own question to
the person, which Codex, Claude Code and OpenCode all have as an item and ours wrote into prose.
Observations `ApprovalRequest` and `InputRequest`. The projection a host renders is an `Item`
(`runtime.items`; the kernel's plan unit stays a `Step`, a standard word too). The host's handle
is `Approvals`; its answers are `Approve`, `Deny`, `ApproveAndAddRule` — Codex's
accept · decline · acceptWithExecpolicyAmendment, Claude Code's "yes, and don't ask again" — and
`RunContext.request_approval` turns them into the loop's judgement. The wire's `step` notification
is `item`; `context.reasoned`/`context.ask` are `context.reasoning`/`context.request_approval`.

Measured on the way: a blind sweep renamed two things that were *not* the vocabulary — the
LangGraph state channel `spent` and a test's plain-English "asked" — and the suite caught both
(spend across a park, a parametrize name). The state channel keeps its name: it is the
checkpoint's, not the record's.

*Why:* a host reads the record without a glossary, and a client developer who knows Codex or
the Responses API already knows ours.

---

### [DECISION] 2026-09-12 — D62: a thread is turns, and a turn is a run

Topics: thread, turn, run, registry, offer, store, provider-state
Affects-phases: phase-25-the-hosts-controls
Affects-specs: architecture/runtime.md#modules, architecture/adapters.md, planning/the-substrate.md#1.8

The plan's §1.8 said a turn would be a *step* of the thread's run. Building it said otherwise: a
composition is fixed when compiled, and a run parks between turns only by a grammar the person
would have to answer, so the truthful unit is what the loop already has — one execution under a
lease, with its own record. A **turn is a run**; the thread is the container above runs; the
agent's tool calls are child runs under the turn's step. That is Thread → Run → Step, the OpenAI
Assistants API's own shape, and Codex's Thread → Turn → Item with nothing invented.

`Thread` (runtime) opens the provider once and holds it across turns; the registry is offered for
the thread's lifetime under the host's name and **attached to each turn's run** — the routing
(`runtime.offer.Routing`) moved out of the recording adapter into the runtime, because the thread
needed it without a socket; the adapter's `RecordingServer` is now the MCP front of it and
`SocketOffer` serves it over the authenticated socket. Each turn carves its ceiling from the
thread's lease and settles what it did not use. `ThreadStore` is a port with `InMemoryThreads`
(runtime) and `SqliteThreads` (basic adapter) held to one contract suite; a product keeps threads
in its own tables by implementing it, or drives turns directly. **Fork and rollback are honest**: a
provider's transcript cannot be rewound, so a rollback is a fork of the first N turns that says
`seeded_turns=N`. The coder's former `session` module is gone; the coder and the studio compose
harness parts only; `providers.ready()` and `NoProvider` moved into the providers package.

Measured live on the subscription: one turn, one run, two child runs (write, read), `reasoning`
and `usage` (26¢) on the record, the file written through the sandbox. Measured on the way: the
first live turn was **refused** — the thread put the *environment's* mode name into the context
key governance selects by, and the record then said `completed` with an empty answer. The mode a
thread carries is the policy's id (until group 4 makes them one thing); a refused turn is
recorded `refused` with its reason. Seven mutants killed on the thread (never attach, withhold
nothing, no carve, outcome never saved, rollback not seeded, reasoning dropped, failure not
recorded).

*Why:* the container is the harness's to offer, composable and optional (principle 7 / §1.9);
and the loop is built once.

---

### [DECISION] 2026-09-12 — D63: the record is complete; the activity is live

Topics: activity, streaming, deltas, observer, leash, steer, interrupt, principle-6
Affects-phases: phase-25-the-hosts-controls
Affects-specs: architecture/runtime.md#modules, architecture/wire.md, architecture/adapters.md

Everything that *happened* is on the record, once, replayable. Everything that is *happening* — a
token of thinking, a token of text, a chunk a running command printed, "composing" — is
**activity**: a kernel type (`Activity(run_id, step, kind, text, at)`, kinds open, four named)
delivered through the emitter's observer channel to an `ActivityObserver` — its own protocol, so
an observer that only knows `on` still works (D14) — bounded and dropped-oldest (D11), forwarded
from a child run to the root the way its events are, **never** on `run()`'s stream and never in a
checkpoint. Surveyed first: LangGraph's `custom` stream mode has exactly this shape (ephemeral,
written from inside a node, not checkpointed); ours rides the emitter because that already owns the
run↔host seam and the child-forwarding path. `RunContext.activity` and `activity_now` (for a
reader task); `context.activity` crosses the wire as a fire-and-forget notification.

Fed by: the jsonl transport from `--include-partial-messages` — `Delta(on, kind, at)` rows on the
`Dialect`, measured on Claude Code (`stream_event` / `event.delta.type` of `thinking_delta` or
`text_delta`); the leash's `on_output`, each chunk as it prints, turned into `output` activity by
the local environment; `AgentSession.steer`/`interrupt` with defaults and `Thread.steer`
(mid-turn if the provider takes it, folded into the next prompt if not) and `Thread.interrupt`
(the provider told if it can be, the turn's run cancelled either way, the turn recorded
`cancelled`).

Measured live in the studio: 38 thinking deltas and 36 text deltas streamed into the page while
the turn ran, and a command's lines `1`, `2`, `3`… arrived one by one as it printed; 27¢. Found on
the way: with partial messages on, Claude Code emits an `assistant` line per content block, each
carrying the whole message so far, so a thought went on the record twice — deduplicated within the
turn and pinned. Also found: the emitter's `close()` raised `QueueFull` when the observer's backlog
was full (a latent TD-005 bug the flood test reached); the sentinel now lands by dropping the
oldest. And the studio never *kept* its item lines, so a reloaded page showed every part running.
Five mutants killed.

*Why:* a person watching a run should see it happen; the record should never pay for that.

---

### [DECISION] 2026-09-12 — D64: a mode is a policy, a behaviour and a presentation — data, live

Topics: modes, behaviour, presentation, set_mode, registry, provider-file, mode_changed
Affects-phases: phase-25-the-hosts-controls
Affects-specs: architecture/adapters.md#modes, architecture/runtime.md#modules, planning/the-substrate.md#3.3

Every product that ships an agent has modes, and every one of them is two things wearing one name
(the-substrate §1.4): an approval policy, and who the model is. Ours had the policy half only —
and its three defaults lived in an example. Now: `Behaviour` (kernel) — `system`, `append_system`,
`model`, `effort`, `temperature`, `tools_offered`, every field optional so a mode carries only what
it means to change; `ModeSpec` (modes adapter) = the policy (`Mode` over effect profiles, as
before) + a `Behaviour` + a presentation (`id`, `name`, `description` — ACP's `SessionMode` shape);
`ModeRegistry` the set, with `shipped_modes()`: **`read-only`, `workspace-write`, `full`** — the
same words as the environment's modes, so the two vocabularies that collided at group 2's first
live turn are one vocabulary. `AgentPort.open(tools, workspace, behaviour)`.

**A provider file maps a behaviour to that CLI's flags** — `[[dialect.behaviour_args]]`, `field →
flag`; Claude Code's are measured (`--system-prompt`, `--append-system-prompt`, `--model`,
`--effort`); a field the file does not map is **reported** (`unmapped_behaviour`), never silently
dropped — a mode that asks for a temperature a CLI cannot take is told so. Codex and OpenCode map
nothing yet and say so the same way.

**`set_mode` on the thread**: the policy the governance selects by changes at the next step (the
context key); if the new mode's *behaviour* differs, the provider is reopened with it, resuming
the thread by its session id; `ModeChanged` goes on the record — a fact a replay needs; setting
the mode a thread already has records nothing (a mutant that announced a change for a no-op
survived until the test said so). `set_option` for a product's own knobs. The runtime reads a
registry structurally and never imports the modes adapter, so a product hands in its own.

*Why:* the mode a person picks in the input box must be one thing that carries the role and the
permission together, switchable without a restart (principle 10), with the harness's uniqueness —
governance by effects — underneath.

---

### [DECISION] 2026-09-12 — D65: "approve and add a rule" is a rule the person makes; the agent's question is an item

Topics: approvals, act-rules, rules, input-request, ask_person, governance, sink
Affects-phases: phase-25-the-hosts-controls
Affects-specs: architecture/runtime.md#modules, architecture/adapters.md#modes, planning/the-substrate.md#3.5

Every product has "yes, and don't ask again" (Claude Code, per repository and command; Codex's
`acceptWithExecpolicyAmendment`). Ours is an **`ActRule`** (kernel): a component, the inputs it
applies to (exact on every key it names; a string ending `*` by prefix; none for every act of the
component), a decision `allow | deny`, and optionally the mode it holds in. The host keeps them in
an **`ActRules`** registry (modes adapter) handed in as `RunOptions.rules` — a host handle like
`Approvals` and `Cancellation` (principle 7), inherited by children — and **`ModeGovernance`
consults it after its own judgement says *ask*, never before**: a rule stands in for the person
or refuses for them, and cannot widen a ceiling. Governance sees the act because the context now
carries the step's resolved `inputs` beside `component` and `posture` (reserved — a host cannot
set it, so a driver cannot shape a rule's view).

**Both answer paths make the rule the same way.** `RunContext.accept_answer` turns the host's
words into the loop's judgement — live through the handle (D58) or on resume of a parked step —
and on `ApproveAndAddRule` adds the rule to the run's registry the moment it is given and proposes
it through the sink (`Proposal(kind="rule")`, provenance `person`), so the record says a rule was
made, about what. The wire's JSON answer vocabulary (`approve`, `deny`, `approve_and_add_rule`
with its rule) is accepted there too.

**`ask_person`** (runtime `person.py`): the agent's own question as a component — declares no
effects, so every mode offers it; `RunContext.request_input` puts `InputRequested` on the record
where it was asked and waits on the same handle for text (`Request.kind == "input"`); nobody
there is a failure that says so. It crosses the wire (`context.request_input`).

Measured live on the subscription (two turns, 30¢): the first write in `full` mode asked; answered
*approve and don't ask again*; the second write to the same path ran on the rule with no question
— after one correction: the studio had built the rule from every input, and the same file with
different text asked again, which is not what the button means. **What a rule names is the
product's vocabulary** (principle 8): the studio makes it the `path` for a file act and the exact
command otherwise; the harness's `ActRule` stays general. Then a task the agent could not finish
without asking: it called `ask_person`, got "Hindi", asked approval for the write, and wrote
`नमस्ते!`. Nine mutants killed, two after the tests were widened to cross the bounds they had not
(a rule for another component; a prefix that should not match).

---
