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

Design: `intent-ecosystem/vision/09-the-agentic-system.md`; low-level design:
`specs/architecture/runtime.md`.
