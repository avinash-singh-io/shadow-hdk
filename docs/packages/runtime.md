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
