---
type: Phase
phase: 21
name: the-visible-agent
epic: 0010-the-visible-agent
status: complete
topics: [events, reasoning, projection, sse, deferred-tools, offloading, context]
deps: [phase-20-providers]
---

# Phase 21 — The visible agent

The event stream records what an agent **did**: what it invoked, what it observed, what it was
refused, what it asked, what it spent. It does not record what it **thought**. A model's reasoning
— the thinking a provider streams before a tool call — is the one thing on a run a person most
wants to read, and it is the one thing this runtime throws away.

A person watching a run needs to see it as *steps*: this is what it thought, this is what it
reached for, this is what came back, this sub-agent went off and did that, this was refused, this
cost that. Every client renders that view; none should have to derive it from eleven raw kinds.

## What this phase makes true

**Thinking is on the record.** `Reasoned`, the twelfth event kind — a model's reasoning content,
stamped and sequenced beside the `Invoked` it led to. Emitted by whoever holds the model's answer:
the agent adapter from a `ModelResponse`, a transport from a provider's stream. A model that
reports no reasoning emits none — a kind that appears when there is nothing to say is a kind
readers learn to skip (the rule `Spent` set).

**The stream has a shape a client can render.** A **projection** — the event stream folded into
steps: each step's reasoning, invocation, observation, refusal or question and spend; sub-agents
nested by run id; the run's totals. In-process it is an async iterator over the same events; over
the wire it is Server-Sent Events. It is a runtime type, not a UI, and it is *generic*: a browser
agent's steps and a coding agent's steps and a device's steps fold the same way.

**Many tools cost little until one is chosen.** A registry of two hundred tools sends two hundred
names and a line each; the full schema arrives when the model reaches for one. D13's `describe`
meta-tool is the mechanism; this makes it the default rather than the exception.

**A large result does not flood the context.** An observation past a threshold lands in the
environment as a file and the stream carries a handle and a preview. The threshold is a
`RunOptions` field, because what counts as large is the host's to say.

## Why these four together

The last two are what a benchmarked competitor credits for a 30–75% cost advantage over a managed
loop at equal accuracy: fewer tool calls, a leaner context each turn. They are cheap here because
the registry is already recomputed every step and `describe` already exists. The first two are
what makes a run *legible*, which every host renders and no host should build.

## What is deliberately not here

A UI. Automatic compaction (Phase 25 — D18's meta-tool exists; making it fire itself is a
separate decision). Memory (consumed, Phase 25). Nothing coding-specific: reasoning is any model's,
a step is any component's, a large result is any observation's.
