---
type: Phase
phase: 20
name: providers
epic: 0009-bring-your-own-provider
status: in-progress
topics: [providers, model-port, agent-port, subscription, byok, detection, injection]
deps: [phase-19-the-p2s]
---

# Phase 20 — Providers: your key, or your subscription

Every phase up to here assumed the model arrives one way: a host constructs a `ModelPort` and hands
it in. That is *bring your own key*, and it works — `LangChainModel` reaches OpenAI and every
OpenAI-compatible endpoint, Anthropic, Ollama, Bedrock, Vertex, Mistral.

It leaves out the other half of the market. A great many people already pay for a coding agent —
Claude Code, Codex, Copilot, Cursor — and that subscription is inference they have already bought.
Today this runtime cannot use it. This phase is *bring your own subscription*, built so that the
next CLI costs a file rather than a phase.

## The distinction the whole design rests on

**An API key sells inference. A subscription sells an agent.**

- Inference is stateless: messages and tool schemas in, text and tool calls out. **The caller owns
  the loop.** That is `ModelPort`, and it is built.
- An agent is stateful: a prompt in, work done, a stream of what happened out. It holds its own
  conversation, chooses its own tools, decides when it is finished. **It owns the loop.**

These are different products at different layers, and the temptation is to hide that behind one
interface. It must be resisted. A `ModelPort` over a coding CLI would have to defeat the CLI's own
loop to extract a single tool call, and there is no supported way to do that in any of them.

The reference implementation agrees, and its agreement is worth more than the argument: open-design
carries twenty-eight provider definitions and **no `complete(messages, tools) -> tool_calls` seam
anywhere**. Nobody has made a coding CLI behave as a model, because it is not one.

So: **two seams.** D22 leaves the port set open precisely for this.

## What makes the two seams equal

If a subscription-backed agent runs its own loop, what is left of governance?

Everything that matters, provided one invariant holds:

> **Every effect routes through the run's component registry, whoever decided to call it.**

For a model provider this is already true — our loop invokes our components. For an agent provider
it is made true by **injection**: the provider is launched with the run's own registry as its tool
source, and its native tools are refused. Then a file it writes, a command it runs and a claim it
proposes all arrive as `Invoke` on our graph — judged on effects (never on the tool's name), charged
to the parent's lease, stamped with a posture, and on the event stream. The sink still decides what
is kept, because the runtime still has no write path.

This is *govern effects, not names* raised one level: **the harness does not govern a provider, it
governs the effects.** It is also the difference between this and the reference — open-design
injects tools; this injects **governed** tools.

The invariant has a hole in it today and closing that hole is a task in this phase: the ACP bridge
refuses `create_terminal` outright, so a child agent asked to run code either cannot, or runs it in
its own process where nothing sees it. A socket with a hole is not a socket.

## What a provider is

**A provider is data.** D17 made agent architectures TOML that a team writes without touching
Python; a provider is the same kind of fact, and it is stored the same way. Adding a CLI is adding
a file. Only a genuinely new transport costs an adapter.

The provider record carries what must be *measured* rather than assumed: how to find the binary,
how to ask its version, how to ask whether it is signed in, what it must not inherit from our
environment, and how our tools reach it.

## What is deliberately not attempted

**The loop stays theirs.** When a subscription drives, our patterns and compositions do not run —
we own the tools, the judgement, the lease and the record; the provider owns the reasoning. This is
not a shortfall to be fixed later: you cannot buy an agent and also own its loop. A host that needs
this runtime's loop uses `ModelPort`, which is what it is for.

**No credential is ever read, stored, forwarded or logged.** Authentication is the CLI's business.
We ask it a question and believe the answer or say we could not tell.

**Nothing is ever installed.** A provider that is absent is reported as absent, with the command
that would fix it, and that is the end of our involvement.

## The lessons taken from the reference, and the two places it is not followed

Read from `nexu-io/open-design`, `apps/daemon/src/runtimes/`:

* **Resolution returns every candidate, not the winner.** A directory earlier on the path can hold
  a wrapper left by a half-finished install; resolution cannot tell it from a working CLI and only
  spawning can, so the caller walks candidates until one runs.
* **`PATH` alone is not the search path.** A process started by a launcher rather than a shell has a
  minimal `PATH`, so the user-level toolchain directories are searched too — and the *spawn* path
  must contain the same directories, because a binary can resolve and still fail to execute when
  its interpreter lives in one of them.
* **The launcher failing is not the program failing.** "The wrapper never reached its script" and
  "the CLI ran and disliked the argument" need different remedies and must not be confused.
* **Authentication has three answers, not two** — signed in, not signed in, and *could not tell*.
* **A capability is probed, never believed**, including flags a CLI does not document.

Two places this phase deliberately does **not** follow it, both being where the reference has
decayed into per-provider code:

* Its `spawnEnvForAgent` is a hand-written branch per provider. Here the environment a provider
  needs — what to set, strip and backfill — is **fields on the record**.
* Its authentication classification is a per-provider function matching English error text. Here the
  patterns are **fields on the record**, and where a CLI cannot be classified the answer is
  *unknown* rather than a guess.

Both follow from the same rule: a provider is data, and every time provider-specific knowledge
leaks into a code path, adding the next provider costs a phase again.
