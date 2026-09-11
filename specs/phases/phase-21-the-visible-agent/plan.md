---
type: Plan
phase: 21
---

# Plan — Phase 21, The visible agent

## Group 1 — `Reasoned` (kernel; contract 0.14.0 → 0.15.0)

- `Reasoned` event: `run_id · seq · at · step · text`, `kind="reasoned"`. In the `Event` union,
  in `CONTRACTS`, in the wire's published schemas.
- `ModelResponse.reasoning` and `ModelChunk.reasoning` (a delta), both defaulting empty so no
  adapter breaks (D14's rule for a field).
- `Turn.reasoning` on the agent seam, same default.
- `RunContext.reasoned(text)` — how a component puts thinking on the record, beside `propose` and
  `spawn`. Empty text emits nothing.
- The agent adapter emits it after every model turn that carried reasoning. The LangChain adapter
  reads provider reasoning where the provider exposes it. The `jsonl` transport reads Claude Code's
  thinking blocks. The ACP adapter reads `agent_thought_chunk` updates.
- Telemetry: a `reasoned` span event carrying length, never text (D28).

## Group 2 — the projection (runtime, wire)

- `Step` — one step's reasoning, invocation, outcome (observed / refused / asked / failed), spend,
  and its children (a `Spawned` opens a nested run; that run's steps fold under it).
- `steps(events)` — a pure fold from an event iterable to a step iterable, so any stored record
  can be projected after the fact.
- `run_steps(...)` — the same fold over a live `run(...)`, yielding steps as they complete.
- Over the wire: a `/runs/{id}/steps` SSE endpoint alongside the raw event stream.
- Nesting is by `run_id`: the runtime already forwards a child's events into the parent's stream.

## Group 3 — deferred tool schemas (agent adapter)

- A pattern field, default on: tools are offered as name + description; the full input schema is
  fetched by `describe` on first use and cached for the turn.
- A test that counts what reaches the model: two hundred registrations cost two hundred lines,
  not two hundred schemas.

## Group 4 — large-result offloading (runtime)

- `RunOptions.offload_over: int | None` — bytes. `None` off.
- An observation whose serialised payload exceeds it is written to the environment (the workspace,
  today; the environment, after Phase 22) and the observation the model sees carries a handle, a
  size and a preview.
- The full observation still reaches the sink and the record — offloading is about the *model's*
  context, never the host's.

## Close

Decisions D45–D47 in history.md; the index regenerated; every package to 0.15.0 with
`tests/test_versions.py`; the coder example shows reasoning; README's event list says twelve.
