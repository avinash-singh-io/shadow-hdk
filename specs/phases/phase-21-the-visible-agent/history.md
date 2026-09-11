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
