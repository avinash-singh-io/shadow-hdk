---
type: Guide
title: Reading shadow-hdk
description: Every box in the five diagrams, what it is and does, the directions data can flow, and every way the harness can be consumed.
---

# Reading shadow-hdk

A companion to the five diagrams in this directory. It answers four things: **what each box is**,
**how to read each diagram**, **which directions anything can flow**, and **how somebody actually
uses this**.

---

## 1. The one-paragraph version

shadow-hdk runs an agent over an open set of components, under a governance policy, and hands
what it produces to whoever is listening. It is a library first: `run()` is a plain async function
you import. Three packages, dependencies pointing one way — a **kernel** of frozen types depending
on nothing, a **runtime** depending only on the kernel, and **adapters** depending on the runtime
and never on each other. Six **ports** are the seams you plug into. The single design decision is
that it governs **effects, not names**: a component declares what it reads, writes and reaches, and
whether it is reversible, contained and costly, and policy is a comparison over those six fields.
That is why a rule written today still holds for a component nobody has written yet.

**What it deliberately does not do.** It has no opinion on what a "claim", "intent" or "record"
means. It never writes to your database. It does not know what your modes are called. Mechanism
lives here; policy and content live in your product.

---

## 2. How to read the five diagrams

Read them in this order. Each one answers a question the previous one cannot.

| # | Diagram | Read it to learn | What it deliberately omits |
|---|---|---|---|
| 1 | `harness.architecture` | What the pieces are, and which way dependencies point | Time. It cannot show that governance is asked *before* a component runs |
| 2 | `a-run.sequence` | What happens, in order, during one run | Branches. It shows one path, the one where everything works |
| 3 | `governed-step.workflow` | What decides, and what every answer produces | What happens *between* steps |
| 4 | `run.lifecycle` | How a run waits, resumes, and ends | Content. No payload appears anywhere in it |
| 5 | `plan-to-record.dataflow` | What becomes what, from a brief to the record | Control. Nothing about who decided |

### 2.1 Walking the architecture, box by box

Start at the left and move right. The spine is the load-bearing path.

1. **Host / Product** — you. Your product owns the policy, the record and the UI.
2. **run()** — the entry point you call. It is an async generator, so events arrive *while* the run
   is going.
3. **Compiler** — turns the plan into a LangGraph graph.
4. **Governed step** — the one enforcement point. Every graph node is one of these.
5. **Components** — everything the agent can invoke.
6. **Model** — reached *through* a component (the agent adapter), never directly by the runtime.

Then read the ring around the spine. Above it: **Governance** (asked before every step). Left of
it: **Sink** and **Observer**, the two ways anything comes back to you. Below everything: the
**Kernel** slab — the shared vocabulary that all of the above depends on and that depends on
nothing itself.

The one thing to take away: **the arrows never point back into the kernel's dependencies**, and the
runtime never reaches sideways into an adapter.

### 2.2 Walking the sequence

Read top to bottom; the four labelled bands are the acts.

1. **Starting** — you call `run()`, and `Started` plus `Composed` come back *immediately*. You are
   not waiting for the end.
2. **One step: judged, then done** — the step asks governance first, gets `Allow`, and only then
   invokes the component. Notice the agent calls the model, and the runtime does not.
3. **A step that must ask** — the same judgement returns `Ask`. The run parks. You answer whenever
   you like.
4. **The record, and the end** — a proposal goes to the sink, and `Ended` closes the stream.

The one thing to take away: **the judgement always precedes the invocation**, and there is no path
around it.

### 2.3 Walking the workflow

Read the middle lane left to right — that is the step. Then read *down* from each box: those are
the ways it can go wrong.

- **Lease check** → up to `Ended` if the budget is gone.
- **Refresh · resolve** → down to `Failed` if the id is unknown.
- **Inputs** → down to `Failed` if a binding points at nothing.
- **Judge** → down to `Refused`, or across to `Ask`.
- **Invoke** → down to `Failed` if the component raised, up to `Ended` if a *port* raised.
- **Observe** — the step is on the record.

The one thing to take away: the top lane and the bottom lane mean different things. **Bottom is
data** the agent sees and can route around. **Top is the run ending.**

### 2.4 Walking the lifecycle

Read the top rail left to right: `Started → Running → Parked → Resumed → Completed`, with the loop
back from `Resumed` to `Running` for a run with more steps to take. Then read the bottom rail: the
three terminal exits, each hanging off the state that can reach it.

The one thing to take away: **Parked is a checkpoint on disk, not a process held open.** That is
why a run can resume in a different process, on a different machine, days later.

### 2.5 Walking the dataflow

Read left to right through the five stages, then read the fan at the end.

`Brief` and `Catalogue` feed the `Model`. The model's tool calls become a `Composition`. That
becomes a `Governed step`. And then three different things come out, and they are **not** the same
kind of thing:

- **Event stream** — information. Fire and forget.
- **Proposal** — a request to remember. Your gate decides.
- **The world** — an act that already happened, with a receipt.

The one thing to take away: **two kinds of write, and only one is forbidden.** Changing the world
happens through a judged component. Changing your record happens only by proposing.

---

## 3. Every component, one by one

### 3.1 The kernel — the vocabulary

Frozen dataclasses and protocols. No I/O, no clock, no logging, no framework import. Every type is
published as JSON Schema and round-trips through JSON in CI, which is what lets the whole runtime
be put behind a wire later without a rewrite.

| Type | What it is | What it is for |
|---|---|---|
| `Interface` | name, description, input schema, output schema | What the model is shown about a tool |
| `EffectProfile` | six fields: `reads`, `writes`, `reaches`, `reversible`, `contained`, `costs` | What a component does to the world. The thing governance judges |
| `ScopeSet` | a set of scope names, or honestly "everything" | Lets `reads` and `writes` name areas like `workspace`, `record`, `world` |
| `Provenance` | who registered it, through which adapter, when, signed by whom, and its posture | Attribution, and the signature that makes a driver's claim checkable |
| `Component` | interface + effects + provenance + labels | The registrable unit |
| `Registration` | an id bound to a component | What the registry is a set of |
| `Composition` | a tuple of steps | The plan, as a value |
| `Invoke` `Await` `Sequence` `FanOut` `Until` | the five step kinds | The grammar a plan is written in |
| `Binding` | a literal, or a reference to an earlier step's handle | How a step gets its inputs without flattening them to text |
| `Lease` | a `Ceiling` (steps, wall seconds, money) and a `Floor` (minimum effort) | The budget and the anti-give-up counter |
| `Observation` | `Completed` `Refused` `Asked` `Failed` `Pending` `Acted` | What a step saw |
| `Acted` | foreign id, idempotency key, exit, grounds | The receipt for anything that changed the world |
| `Proposal` | kind, payload, provenance, grounds | A request that the host remember something |
| `Event` | eleven kinds, each with `run_id`, `seq`, `at` | The only channel out |
| `Usage` | tokens and cost, any of which may be `None` | Honest metering — unknown is never zero |

**Two vocabulary points that matter.** `Posture` is `controlled` or `observed`: *we gated it before
it happened* versus *we found out afterwards*. Only `controlled` can satisfy a consent-before-effect
claim. And "everything" in a `ScopeSet` exists because a component that will not declare what it
touches must be assumed to touch everything, never nothing.

### 3.2 The six ports — the seams

A port is a protocol you implement. Six is a starting set, not a ceiling: a new port is a kernel
change with a default that refuses the steps needing it rather than crashing.

| Port | Signature | Who implements it | If you don't |
|---|---|---|---|
| **Model** | `complete(request)`, `stream(request)` | `langchain`, `acp`, or yours | The agent cannot think |
| **Component** | `registrations()`, `invoke(id, inputs)` | `mcp`, `basic` callables, `workspace`, `agent`, … | Nothing can be invoked |
| **Governance** | `judge(effects, context) -> Allow \| Ask \| Refuse` | `basic.AllowAll`, `modes`, `effect_rules` | Nothing is permitted |
| **Sink** | `propose(proposal)` | yours — it is your record | Proposals go nowhere |
| **Observer** | `on(event)` | `basic` stdout/callback, `otel` | You still get events from the generator |
| **Clock** | `now()`, `new_id()` | `basic` system clock, `testing.FixedClock` | No stamps, no ids |

`Ports` bundles all six; only `observer` is optional, because `run()` yields events regardless. It
carries one field that is **not** a port: `trust`, the keys a deployment holds and the effects it
demands proof for. That is configuration checked at the registry, not a seam somebody implements.

**Why the clock is a port at all.** It is the runtime's one source of non-determinism. Behind a
port, a replay costs nothing and two runs of the same input are comparable.

### 3.3 The runtime — the machinery

Everything here is ephemeral. The runtime owns nothing durable, on purpose: a runtime that persists
its own state is a runtime you cannot replace.

| Part | What it does | How it does it |
|---|---|---|
| **`run()` / the drive** | Starts a run and yields its events | An async generator over a task, so a host watches it happen rather than hearing about it after |
| **`resume()`** | Continues a parked run | **You pass the composition back in**, with the answer and a checkpointer. The runtime owns nothing durable, so it cannot remember the shape of a run it parked — the checkpointer holds the state, whoever resumes holds the plan |
| **Compiler** | Turns a `Composition` into a LangGraph graph | `Invoke`/`Await` become nodes, `Sequence` wires in order, `FanOut` becomes a dispatcher plus join, `Until` becomes a conditional edge. It compiles; it never interprets |
| **Registry** | Answers *what exists right now* | The union of every component port, **refreshed every step**, so a server connected mid-session is invocable on the next one. A port that will not answer contributes nothing rather than ending the run |
| **Trust** | Refuses a registration that cannot prove itself | Checks the signature over what the driver declared. Unsigned where required, unknown key, revoked or forged is **absent from the catalogue**, with the reason kept |
| **Step executor** | The seven moves | Lease check → refresh → resolve → inputs → judge → invoke → observe. One function; the whole enforcement story |
| **Session + LeaseMeter** | Holds handles and the budget | Charges each step, tracks wall time and cost, and carves a child's ceiling out of what is left |
| **Emitter** | Stamps and fans out events | Decides `seq` and `at` in one place; feeds the generator and the observer through separate queues, so a slow observer can never slow a step |
| **Handles** | Keep real values between steps | A step's output is stored under its id; a later `Binding` refers to it. A large result is never flattened into tokens |
| **Children** | `spawn`, `send`, `release` | A held child is a **parked run**, not a resident object. `send` is a resume with the message as the answer |
| **Cancellation** | Stops a run, with words | Per-branch, so releasing one child says nothing about its siblings |
| **Replay** | Re-runs a recorded run for free | Fingerprints a request over messages, tools *and* model name. A miss raises loudly rather than falling through to the live model |
| **`current_run()`** | How a component reaches its own run | An ambient context handle — how a component proposes, reads what is left of its lease, and spawns children, without any of those becoming ports |

### 3.4 The adapters — every one that exists today

Each is its own package. Each imports the runtime and the kernel, and **never another adapter**.

| Adapter | Port(s) | What it gives you |
|---|---|---|
| `basic` | governance, sink, observer, clock, component | The small real ones every deployment has: `AllowAll` and `Controlled` governance, stdout / file / callback sinks, stdout and callback observers, the system clock, a `Mailbox`, and Python callables as components |
| `agent` | component | The model-driven loop as a component, and agent architectures as data (`single`, `plan-and-execute`, `orchestrator-workers`, …) |
| `langchain` | model | One adapter over every provider LangChain integrates |
| `acp` | model + component | Another agent — Codex, Claude Code — driven as a governed component over Zed's Agent Client Protocol |
| `mcp` | component | An MCP server's tools become components, with effects derived from its annotations rather than trusted |
| `modes` | governance | Governance as data: a mode is a ceiling plus an ask line |
| `workspace` | component | A filesystem the agent can write to, confined to a root it cannot leave |
| `sandbox_subprocess` | component | Run code with a leash — a timeout, an output cap, and an honest account of what it is *not* |
| `contained` | component | A sandbox that proves containment at construction or refuses to exist |
| `recording` | component | Your registry offered to a child agent as an MCP server, so what it does is routed and therefore recorded |
| `derivation` | component | Total expressions over typed tables, fixed-point arithmetic, re-executable grounds |
| `devices` | component | One device contract with three roles — sensor, actuator, witness — and fakes that ship |
| `mqtt` | component | MQTT topics as those three roles |
| `otel` | observer | The shape of a run as an OpenTelemetry trace: ids, kinds, reasons, the lease, usage — never a payload |

**The pattern to notice.** Every one of these is additive. Adding a model vendor, a tool protocol,
a sandbox or a device protocol is a new package. None of them is a runtime change.

---

## 4. The flows — how many directions anything moves

There are **six**, and they are genuinely different. Most confusion about this architecture comes
from collapsing two of them.

| # | Direction | What moves | Who starts it |
|---|---|---|---|
| 1 | **Inward** — host → runtime | `run(composition, ports, options)`, `resume(composition, answer, ports, options)` | You |
| 2 | **Downward** — runtime → adapters | `judge`, `complete`, `invoke`, `propose`, `now`, `registrations` | The runtime |
| 3 | **Outward** — runtime → host | The event stream: eleven kinds, in `seq` order | The runtime |
| 4 | **Sideways** — component → its own run | `propose`, `remaining`, `spawn`, `send`, `release` via `current_run()` | A component, mid-invocation |
| 5 | **Reflexive** — the agent starts another run | The agent component calls `run()` again; that turn is a child run with a carved lease | A component |
| 6 | **World-ward** — component → the world | A file written, an API called, an actuator moved; an `Acted` receipt comes back | A component, under judgement |

**Which are loops.** Two, and only two.

- **The turn loop.** Model produces tool calls → they become a composition → the runtime executes it
  → the observations become messages → the model is asked again. This is direction 5 folding back
  into direction 2, and the **lease** is what terminates it.
- **The park loop.** Running → Parked → Resumed → Running. This is direction 3 going out (`Asked`)
  and direction 1 coming back (`resume`). It can cross a process boundary in the middle.

**Which are one-way, permanently.** Direction 3 is fire-and-forget: nothing an observer does can
reach back into a run. And there is no direction from the runtime into your durable store — a
proposal is a request, and your gate answers it.

---

## 5. How to consume the harness

Five ways, in order of how much machinery they need.

### 5.1 Embedded — import it and call it

The default, and the one everything else is built on.

```python
from shadow_hdk.runtime import Ports, RunOptions, run

ports = Ports(model=..., components=(...), governance=..., sink=..., clock=...)
async for event in run(composition, ports, options=RunOptions(lease=lease, run_id="r-1")):
    render(event)
```

**Choose it when** your product is Python and in the same process. You get the lowest latency, real
Python objects across the boundary, and the simplest debugging.

### 5.2 As one node inside somebody else's graph

`run()` is a plain async function, so a system that has never heard of this project can await it,
and a LangGraph application can mount it as a node.

**Choose it when** the harness is a governed sub-part of a larger orchestration you already own.

### 5.3 A child process over stdio

```bash
python -m shadow_hdk.wire --stdio
```

JSON-RPC 2.0 over stdin and stdout — the same shape MCP and ACP use. The host drives; the runtime
calls back. `run` and `resume` go host → runtime; `judge`, `complete`, `invoke` and `propose` invert
and are answered by the host; events stream host-ward.

**Choose it when** your product is not Python, or you want the runtime in its own process with its
own crash boundary.

### 5.4 A server you connect to

`serve` speaks JSON-RPC over HTTP with events over SSE. Because an HTTP server cannot call its
client, the two directions split: the host POSTs its calls and its answers, and the runtime's
callbacks and events come back down the SSE stream. Each connection gets its own session.

**Choose it when** the client is on another machine. Note the current state honestly: it is
**loopback-only by default** and refuses another bind without a token, because the per-run token
described in the wire spec is designed but not yet built.

### 5.5 Offering your registry to a child agent

The `recording` adapter exposes the running registry to a child agent as an MCP server. The child
calls tools; the calls are routed through your governed step; what it did is therefore on your
record. The topology is inverted — the parent spawns the child and serves over its pipes — because
this server holds a live run and cannot be launched fresh by somebody else.

**Choose it when** you want another agent's work attributable and governed rather than merely
reported.

### 5.6 And one way to consume *other* systems

The `acp` adapter drives Codex or Claude Code as a governed component. The mode you wrote for the
harness governs somebody else's agent without that agent knowing this project exists.

---

## 6. The counted vocabulary

Worth memorising; every number here is closed and changes only by an ADR.

| Set | Count | Members |
|---|---|---|
| Ports | 6 | model, component, governance, sink, observer, clock |
| Effect fields | 6 | reads, writes, reaches, reversible, contained, costs |
| Step kinds | 5 | Invoke, Await, Sequence, FanOut, Until |
| Observation kinds | 6 | Completed, Refused, Asked, Failed, Pending, Acted |
| Event kinds | 11 | Started, Composed, Invoked, Observed, Proposed, Refused, Asked, Spawned, Held, Spent, Ended |
| End reasons | 5 | completed, lease_exhausted, gave_up, cancelled, failed |
| Judgements | 3 | Allow, Ask, Refuse |
| Postures | 2 | controlled, observed |
| Error classes | 2 | component failure is data; port failure ends the run |

---

## 7. If you remember six things

1. **Govern effects, not names.** Six declared fields with a "narrower than" order. Policy is a
   lattice comparison, which is why it holds for components nobody has written yet.
2. **One governed step.** The entire enforcement story is seven moves in one function, run for every
   step of every composition. There is no second path.
3. **The plan is data.** Tool calls become a composition, which is compiled rather than interpreted,
   and re-emitted whenever it changes — so plan-versus-actual costs nothing.
4. **Two kinds of write.** The world changes through a judged component. Your record changes only by
   proposal, and your gate decides. The runtime has no write path into any durable store.
5. **Two error classes.** A component failing is data the agent can work around. A port failing means
   your host is broken, and the run ends rather than reasoning past it.
6. **Parking is a checkpoint.** Not a held process. That single choice is why a governance question,
   a slow job, and a sub-agent between messages are all the same mechanism.
