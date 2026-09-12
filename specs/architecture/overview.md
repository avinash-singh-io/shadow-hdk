---
type: Architecture
---

# The shape in one page

> The design is `intent-ecosystem/vision/09-the-agentic-system.md`. This directory is that document
> made buildable: what the packages are, what the classes are, what the functions do, and how it is
> tested. Where the two disagree, `09` wins until an ADR says otherwise.

## Three packages, arrows pointing one way

```
  SERVE      the front door (D67, D71): Harness · harness.toml · shadow-hdk serve · batteries
  WIRE       the runtime over JSON-RPC — stdio, HTTP/SSE — for a host in any language; the schemas
  PROVIDERS  a provider is a file: Claude Code · Codex · OpenCode, your key or your subscription
                    │ depend on adapters (serve) / runtime (wire, providers)
  ADAPTERS   many small packages; each depends on runtime, none on another
    models: langchain (openai-compatible · anthropic · ollama · huggingface · …)
    agents: jsonl (Claude Code, Codex) · acp (OpenCode) · agent (the model loop as a component)
    components: callable · mcp · environment (local on the OS sandbox · a box) · recording · devices · mqtt · derivation
    governance: allow-all · modes (policy + behaviour + presentation + environment mode)
    sinks: list · stdout · file · callback          observers: stdout · callback · otel
                    │ implements ports
  RUNTIME    one package; depends only on kernel
    the registry · the governed step · composition → graph · leases · events
    sub-agent spawning · session handles · run / resume / current_run
    the thread (turns, modes, roots) · the offer · the environment base · processes · lines
                    │ pure types
  KERNEL     one package; depends on nothing
    Component · Registration · EffectProfile · Composition · Workspace
    Observation · Proposal · Lease · Event · the ports · Thread and Turn records
```

A host sits **above** all three as one more set of adapters plus its product. Nothing below the line
knows it is there, and nothing below the line is written for a particular one.

**One more package is the front door** (Phase 26–27, D67, D71): `serve` composes the shipped
adapters — the local environment with a mode, the shipped skills, the mode and rule registries
over files and a store, batteries (D70), the provider signed in here — and offers that one
composition two ways: `Harness` in-process (three lines, `harness.toml`) and `shadow-hdk
serve` over the wire for a host in any language. It depends on the adapters and on nothing
depends on it; two invariants hold it to public names and to keys that map to ports, so a product
that outgrows it composes the same objects itself.

## What each layer owns

**Kernel.** Frozen dataclasses and protocols. No I/O, no clock, no logging, no framework. Every type
is published as JSON Schema and round-trips through JSON in CI, which is what makes a service form of
the runtime a composition root later rather than a rewrite.

**Runtime.** The loop and the machinery around it, built on LangGraph: compositions compile to
graphs, sub-agents to subgraphs, `Ask` to `interrupt()`, sessions to checkpoints. Its entry point is a
plain async function, so it can be embedded in a system that has never heard of LangGraph or mounted
as a node inside someone else's graph. It owns everything ephemeral — the live registry, the session's
handles, the sub-run tree, counters, the event stream — and nothing durable.

**Adapters.** Each small, each replaceable, each tested against the port it implements. Adding a model
vendor, a protocol, a sandbox, or a way for components to arrive is a new adapter package, never a
runtime change.

## One governed step

Every step of every composition goes through the same seven moves. This is the whole enforcement
story, and it is one function (`runtime/step.py`):

```
lease check   →  the ceiling always beats everything; exhausted ends the run
resolve       →  registry: which component port owns this registration
inputs        →  bindings resolved from earlier steps' handles
judge         →  governance port: Allow | Ask | Refuse over the effect profile — told the run's
                 context (thread, turn, mode), which a child run inherits from its parent (D74)
   Refuse     →  Refused event + Refused observation; the component is never called
   Ask        →  Asked event; interrupt(); the host resumes with a judgement — or, for a step
                 that cannot park, the host's Approvals handle answers live (D58), the person's
                 rules read first (D65)
invoke        →  the component does its work; an exception becomes a Failed observation
observe       →  Invoked + Observed events; the output is stored under the step's handle
```

## Two kinds of write, and only one is forbidden

| the agent wants to… | how it happens | who decides |
|---|---|---|
| write a file, render a page, run code, call an API, move an actuator | a **component** whose effects are declared (`writes`, `reaches`, `reversible`, `contained`) | governance, per step |
| have the host **remember** something | a **Proposal** to the sink port | the host's gate |

The runtime has no write path into any host's durable store. That is the whole of "propose, never
commit" — it is about the record, not about the world.

## How a product uses it

```python
# a simple product: one agent, a few tools, no dynamic workflows, no sub-agents
agent = AgentComponent(pattern=single, tools=[search, calendar, crm])
async for event in run(Composition((Invoke("a1", agent_id, brief),)), ports, options=opts):
    render(event)

# a dynamic product: the agent composes its own multi-step, multi-agent work
agent = AgentComponent(pattern=orchestrator_workers, tools=record_tools + workspace_tools)
```

`single` offers the model no `compose` and no `spawn`, so it *cannot* change its shape — plain ReAct
over its tools. `orchestrator_workers` offers them, and leases bound the fan-out. The runtime is
identical in both cases; the pattern is a file.

A product with a *conversation* rather than a brief holds a **`Thread`** (D62): opened on the
roots the product names — one directory or several, added while it runs (D76) — in a mode it
can switch (the policy, the sandbox and the provider's catalogue move together — D64, D76),
turned once per message, each turn its own run on the record, with the tools it is offered
(`Thread.tools()`), the handles it answers through (`Approvals`) and the store every registry
reads (D66) — in-process, or over the wire as `thread/*` for a host in any language (D67).

## Where the boundary falls

**Mechanism here; policy and content in the product.** Model adapters here, *which* provider and
whose key there. The effect-rules engine here, *the rules* there. The composition grammar and the
compiler here, *what an intent may compose* there. Session handles and checkpoints here, the record
there. The typed event stream here, the UI and the meter there.

## Reading order

1. [`decisions.md`](decisions.md) — D1–D13, the choices `09` left open
2. [`runtime.md`](runtime.md) — the classes, the functions, the sequences
3. [`adapters.md`](adapters.md) — every adapter, the contract suites, patterns and modes as data
4. [`file-structure.md`](file-structure.md) — where everything lives, and when it arrives
5. [`testing.md`](testing.md) — the layers and the cases
6. [`wire.md`](wire.md) — the out-of-process form (Phase 9)
7. [`diagrams/`](diagrams/README.md) — six self-explaining views: the shape, how it is consumed, one run, the governed step, a run's life, and plan-to-record
