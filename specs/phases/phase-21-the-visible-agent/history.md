---
type: History
phase: 21
---

# History — Phase 21, The visible agent

### [DECISION] 2026-09-11 — D45: thinking is on the record, beside what it led to

Topics: events, reasoning, visible-agent
Affects-phases: phase-21-the-visible-agent
Affects-specs: architecture/runtime.md#events

`Reasoned` is the twelfth event kind: a model's reasoning, stamped and sequenced. Three rules:

**Why before what.** The thought goes on the record ahead of the calls it led to — the agent
adapter emits after the model turn and before dispatching its tool calls; a transport streams each
chunk as it arrives rather than holding it to the end of the turn, because the calls it led to are
already landing through the socket as they happen and a thought delivered afterwards reads as
hindsight.

**Nothing to say, no event** — `Spent`'s rule (D20). A model that reports no reasoning emits none.

**The model's own words, never a summary.** The record is not the place to put words in a model's
mouth, and an adapter that fell back to the answer when no reasoning was present would put the
answer on the record twice, once mislabelled as thought. A test holds that.

Where thinking lives is a **field on the record**, not a branch: `Dialect.think_on` / `think_at`
for line-delimited transports (D40), the same shape the dialect already uses for text. The
LangChain adapter reads three provider shapes and joins what it finds. ACP carries it as
`agent_thought_chunk`, kept apart from what was said.

Telemetry carries **length, never text** (D28): a trace holds the shape of a run, and reasoning is
the most sensitive payload on it.

Contract 0.14.0 → 0.15.0: `Reasoned` in the union; `reasoning` on `ModelResponse`, `ModelChunk`
and `Turn`, each defaulting empty so no adapter breaks — D14's argument for a method, applied to a
field.

*Why:* a person watching a run wants to know why before what. *Overturned by:* a provider that
cannot be made to expose reasoning at all, which emits none and is not wrong to.

---
### [DECISION] 2026-09-11 — D46: the stream folds into steps, once, and the fold crosses the wire folded

Topics: projection, steps, wire, parity
Affects-phases: phase-21-the-visible-agent, phase-23-a-host-in-any-language
Affects-specs: architecture/runtime.md#modules, architecture/wire.md

Twelve raw kinds are the record; every client renders **steps**. The fold from one to the other is
done once, in the runtime, as a pure function over any event iterable — a live run or a stored
record — so no host derives it and no two derive it differently. `Step` carries what a step
thought, reached for, got back (or was refused, or asked), cost, and the steps of every run spawned
while it was executing, nested by run id to any depth. A stream cut short still folds; the last
step says `running`.

**Over the wire it crosses already folded.** The runtime side feeds the same `Fold` as it streams
and sends each closed step as a `step` notification beside the `event` ones, so a host in another
language renders agent steps without porting the fold. Parity with in-process is by construction
— one `Fold`, both sides — rather than by two implementations kept in step. `Step`'s schema is
published with the kernel's contracts because a client needs it as much as any of theirs.

*Why:* the screenshot every host wants is the same screenshot. *Overturned by:* a host that needs
a different fold, which is evidence the step type is missing a field, not that the fold should
move.

---

### [DISCOVERY] 2026-09-11 — the agent adapter cannot run over the wire; two of three gaps closed

Topics: wire, parity, agent
Affects-phases: phase-23-a-host-in-any-language

Found by trying to prove `Reasoned` crosses the wire with an agent that thinks: the agent adapter
**cannot run over the wire at all today**. Three crossed-context gaps, in the order they bit:

1. `remaining()` is synchronous in-process and refused across a wire. **Closed**: `remaining_now()`
   exists on both contexts now, and the agent adapter uses it in its three places — an adapter
   written once runs both sides.
2. `reasoned()` did not cross. **Closed**: it crosses back like `propose` does, for the same reason
   (one record, one author), and carries the *step* — a thought answered on the peer's task has no
   executing step, and the host-side context is the one that knows. Which found a second thing: the
   crossed `invoke` sent the registration id where the host needed the step id. It sends both now.
3. `visible()` does not cross. **Open**, and Phase 23's: the registry belongs to the run and the
   catalogue an agent builds from it has to cross back with registrations serialised.

The Phase 21 claim is proven with a plain component that thinks; the agent over the wire is
Phase 23's explicit task, with this as its starting measurement.

---
### [DECISION] 2026-09-11 — D47: a large result is held by the agent, never written by the runtime

Topics: offloading, context, principles
Affects-phases: phase-21-the-visible-agent
Affects-specs: architecture/adapters.md#agent

A tool that returns a hundred kilobytes costs a hundred kilobytes of context on every turn after
it. Past `Pattern.offload_over` the model sees a handle, a size and a preview, and `recall` pages
the rest — offered whenever the threshold is set, because a handle the model cannot follow is worse
than the flood it replaced (the rule `describe` follows above the catalogue threshold).

**The plan said *the environment, as a file*, and the plan was wrong.** That would give the runtime
a write path, which the second principle forbids: the runtime acts through components and records
through the sink, and a file it wrote itself is neither. Offloading is about the *model's* context
and nothing else. The agent adapter holds the full result in memory for the run; the record and
the sink get the whole observation exactly as they always did, and a test proves the stream was
not truncated.

The threshold is a pattern field beside `catalogue_threshold`, not a `RunOptions` field as first
planned: what the model sees is the pattern's to say, and the two thresholds belong together.

*Why:* the cost is in the transcript, not on disk. *Overturned by:* a result too large to hold in
memory for a run, which is a component's problem to solve before it returns, not the loop's.

---

### [DISCOVERY] 2026-09-11 — where Claude Code's thinking is, measured

Topics: reasoning, claude-code, measurement
Affects-phases: phase-21-the-visible-agent

Three subscription turns, against claude 2.1.235:

* The `thinking` block arrives on `assistant` events at `message.content[].thinking` — the path
  the provider file named — **with its text empty** and only a signature, by default. Print mode
  redacts reasoning.
* `--thinking-display` accepts `summarized` and `omitted`; `full` is refused (probed by
  value-rejection, the way the reference probes hidden flags). With `summarized` the block carries
  the provider's own summary — 143 characters for a one-line question.
* `--include-partial-messages` streams it as `thinking_delta` events beside `text_delta`.
* Through our own `JsonlSession` with the shipped provider: `Turn.reasoning` carried the summary.
  Two earlier example turns — write a file, read it back — carried none, because the model does
  not engage extended thinking for every task; that is the model's call and reads as *did not say*.

So what reaches the record is a **summary the provider wrote**, never the raw text, and D45 holds:
the record carries what the model said, and a summary is what this one says. The flag is a field
on the record with the measurement beside it.

---

### [SCOPE_CHANGE] 2026-09-11 — deferred schemas were already built; the phase fixed one lie in them

Topics: catalogue, describe, d13
Affects-phases: phase-21-the-visible-agent

D13's fourth mechanism — `thin()` at `catalogue_threshold` — shipped in Phase 8. Group 3 did not
build it again. It found two things and fixed both:

* Above the threshold a pattern that had not enabled `describe` was told to call it anyway. The
  loop now offers `describe` whenever it thins, whatever the pattern said — a mechanism offered by
  halves is a lie, and the existing wiring test had encoded exactly that lie.
* The *call describe* sentence was appended to every one-liner; over two hundred tools it was
  measured at a third of the catalogue, which is not what *a name and a line each* means. It is
  said once, on the verb. Two hundred tools now cost under a quarter of their whole schemas.

---
