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
