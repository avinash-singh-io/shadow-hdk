---
type: Phase
phase: 30
name: a-product-owns-what-it-owns
status: active
topics: [turn, conversation, park, streaming, tokens, contracts, questions, governance, errors, run-store, versioning, idle, reconnect]
deps: [phase-29-one-app-server]
---

# Phase 30 — A product owns what it owns

**What a development kit owes the products built on it, done**: the governed turn as a
primitive a product uses without the kit's record; a question a turn parks *on purpose* for a
later request; an agent that streams; tokens and running time on the record; the contract
suites shipped so a product proves its own stores; a `Questions` port a product implements
without inheriting ours; governance composed by routing; refusals a client can switch on; a
parked run behind a port of ours; the record versioned; sessions that idle out; a stream that
survives a drop.

Opened from `specs/research/2026-09-14-what-a-harness-development-kit-owes-its-products.md`
— sixteen things a kit owes, read from the field's runtimes and from what Intent Studio wrote
*around* the kit — and the owner's *go* (2026-09-14). **The admission rule** of that note
governs every group: a thing enters the kit only when at least two of the field's runtimes have
it or it is a port every product would otherwise reimplement; never when it is a product
concept. Intent Studio is the evidence, not the reason.

## What this phase makes true

- **Q1** `Conversation` — one provider session, its turns governed and recorded as events,
  usable with no record container; `Thread` is a `Conversation` plus a record, a store and a hold.
- **Q17** `turn(on_question="park")` and the `Parked` answer: the turn ends `parked`, the
  question stays on the record, the act runs from its checkpoint when a later request settles it.
- **Q2** the agent streams: `AgentComponent` through `ModelPort.stream`, its words and reasoning
  as activity; `LangChainModel.stream` keeps reasoning and merges tool calls across chunks.
- **Q5 · Q10** `Spent` carries tokens; a thread's seconds are its turns' running legs.
- **Q4** `shadow_hdk.testing.contracts` — the suites a product runs against its own ports;
  provider doubles shipped. A `Questions` port the runtime asks through.
- **Q6 · Q11** `Routed` governance by component; refusals on the wire with a published `kind`.
- **Q7 · Q12** `RunStore` — a small port of ours a parked run sleeps behind, the LangGraph
  saver over it; `version` on the record.
- **Q9 · Q8** a thread's provider closed when idle and reopened on its session id at the next
  turn; a wire session that outlives its stream for a grace period and replays what a
  reconnect missed.

## What does not change

The kernel's effects and the governed step; every method a product calls today (additions
only; `Thread` keeps its surface over `Conversation`); the wire's methods (parameters and one
answer kind added); the shipped stores.
