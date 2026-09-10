---
type: Architecture
---

# The shape in one page

> The design is `intent-ecosystem/vision/09-the-agentic-system.md`. This directory is that document
> made buildable: what the packages are, what the classes are, what the functions do, and how it is
> tested. Where the two disagree, `09` wins until an ADR says otherwise.

## Three packages, arrows pointing one way

```
  ADAPTERS   many small packages; each depends on runtime
    models: langchain (openai-compatible · anthropic · ollama · huggingface · …) · acp
    components: callable · mcp · cli · http · agent · workspace · recording
    sandboxes: subprocess · gvisor · firecracker
    governance: allow-all · modes · effect-rules
    sinks: list · stdout · callback          observers: stdout · callback · otel
                    │ implements ports
  RUNTIME    one package; depends only on kernel
    the registry · the governed step · composition → graph · leases · events
    sub-agent spawning · session handles · run / resume / current_run
                    │ pure types
  KERNEL     one package; depends on nothing
    Component · Registration · EffectProfile · Composition
    Observation · Proposal · Lease · Event · the ports
```

A host — Intent Studio, or anything else — sits **above** all three as one more set of adapters plus
its product. Nothing below the line knows it is there.

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
judge         →  governance port: Allow | Ask | Refuse over the effect profile
   Refuse     →  Refused event + Refused observation; the component is never called
   Ask        →  Asked event; interrupt(); the host resumes with a judgement
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
