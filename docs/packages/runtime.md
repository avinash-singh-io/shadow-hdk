# `shadow_hdk.runtime`

The runtime. Four public names:

```python
from shadow_hdk.runtime import run, resume, current_run, Ports, RunOptions
```

`run(composition, ports, options=…)` compiles a composition to a LangGraph graph, judges every step
through the governance port, emits the nine events, hands proposals to the sink, and carves children
from the parent's lease. It yields events as they happen and feeds an observer if one is bound.

The environment projects its effective mode and isolation into `EnvironmentCapabilities` and may
be opened against `EnvironmentRequirements`. A `Thread` persists `ExecutionRequirements`, retains
the accepted `execution` selection, and requires a fresh compatibility decision when resumed.

`StreamSession` is the reusable transport-independent session beside the durable record: bounded
monotone replay, exactly one attachment, typed stale-cursor and expiry failures, injected-time
grace expiry, and optional ephemeral heartbeats. The HTTP adapter consumes this primitive; another
transport can use it without importing `serve` or `wire`.

The item fold now carries the invoked JSON in `Item.inputs`. Inputs whose canonical encoding is
larger than 64 KiB use an explicit omission marker; the complete `Invoked` event remains the source
of truth.

Design: `intent-ecosystem/vision/09-the-agentic-system.md`; low-level design:
`specs/architecture/runtime.md`.

**Plan admission (Phase 36).** `Children.spawn` admits every plan before `run()` — structure and
existence in the kernel, each leaf's declared effects dry-judged in the child's own context — and
raises `PlanNotAdmitted` after `plan_refused` is on the record; nothing is spawned. `RunOptions`
and `Session` carry `plan_limits`; a child's are the meet of its parent's and the pattern's.
`runtime.planning.plan_components()` is the `compose` component (D110). `Children.defer` and
`Pattern.absorb=False` run an admitted plan after its planner's step (D112). The checkpoint carries
the composition (`RunState.plan`), so `resume` handed a different one admits it as an amendment
(D116) and `runtime.parked_composition()` lets a settle resume on the shape it parked with.
`Thread.amend(handle, composition, answer)` is `settle` with `Amend`; `Thread.plan_limits` is the
host's met with the mode's, live.
