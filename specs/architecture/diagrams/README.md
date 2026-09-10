---
type: Guide
---

# Five views of shadow-hdk

One diagram answers one question well. These five answer five different ones, and only together do
they describe the harness. Each `.json` is the source; each `.html` is a self-contained page with
themes, pan and zoom, search, relationship tracing, and curated views in its header.

| The question it answers | Kind | Open |
|---|---|---|
| What are the pieces, and which way do dependencies point? | architecture | `harness.architecture.html` |
| What actually happens, in order, during one run? | sequence | `a-run.sequence.html` |
| What decides whether a step may run, and what does each answer produce? | workflow | `governed-step.workflow.html` |
| What states can a run be in, and how does it survive a process? | lifecycle | `run.lifecycle.html` |
| What becomes what, from a brief to the record? | dataflow | `plan-to-record.dataflow.html` |

> **New here? Read [`reading-guide.md`](reading-guide.md) alongside these.** It explains every box
> by name, walks each diagram in order, names the six directions anything can flow, and lists every
> way the harness can be consumed.

## What the harness is, in a paragraph

shadow-hdk runs an agent over an open set of components under a governance policy, and hands
what it produces to whoever is listening. Three packages with dependencies pointing one way: a
kernel of frozen types that depends on nothing, a runtime that depends only on the kernel, and
adapters that depend on the runtime and never on each other. Six ports are the seams a host plugs
into. The single design decision is that it governs **effects, not names**: a component declares
what it reads, writes, reaches, whether it is reversible, contained, and costly, and policy is a
comparison over those six fields. Adding a model vendor, a tool protocol, a sandbox, or a device
protocol is a new adapter package, never a runtime change.

## Why one diagram is not enough

- The **architecture** shows structure and layering. It has no time in it, so it cannot tell you
  that governance is asked before a component is ever called.
- The **sequence** shows exactly that order, across one run. But it shows one path through the
  system, not the branches.
- The **workflow** shows the branches: the seven moves of the governed step, governance's three
  answers, and the two classes of error. It says nothing about what happens between steps.
- The **lifecycle** covers that: how a run parks on a checkpoint, resumes possibly in another
  process, and which five endings it can have.
- The **dataflow** shows none of the control and all of the content: how a brief becomes a plan,
  and the two very different ways anything leaves the runtime.

## The ideas worth carrying away

1. **Govern effects, not names.** Six declared fields with a "narrower than" order. A policy is a
   lattice comparison, which is why it holds for components nobody has written yet.
2. **One governed step.** The whole enforcement story is seven moves in a single function, run for
   every step of every composition.
3. **The plan is data.** The model's tool calls become a composition, which is compiled to a graph
   rather than interpreted, and re-emitted as an event whenever it changes.
4. **Two kinds of write.** A component changes the world under judgement. Reaching the host's
   record is only ever a proposal, and the host's own gate decides. The runtime has no write path
   into any durable store.
5. **Two error classes.** A component failing is data the agent can see and work around. A port
   failing is a broken host, and the run ends.
6. **Parking is a checkpoint, not a held process.** A governance Ask, an Await on something slow,
   and a sub-agent kept between messages all use it.

## Regenerating

The Archify skill lives at `~/.claude/skills/archify`. From that directory:

```bash
node bin/archify.mjs deliver architecture <spec>.json <out>.html --quality showcase --json
```

Every page here passed that showcase gate with zero composition errors and zero warnings.
Automated browser evidence is **skipped**: `visual-check` needs Chrome or Chromium, which is not
installed on this machine. Each page was instead opened and read at desktop sizes by hand.

The MQTT adapter — one adapter among many, and deliberately the most replaceable part — has its own
five diagrams under `specs/phases/phase-16-mqtt/diagrams/`.
