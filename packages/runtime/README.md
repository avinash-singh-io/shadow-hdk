# shadow-hdk

The runtime. Four public names:

```python
from shadow_hdk.runtime import run, resume, current_run, Ports, RunOptions
```

`run(composition, ports, options=…)` compiles a composition to a LangGraph graph, judges every step
through the governance port, emits the nine events, hands proposals to the sink, and carves children
from the parent's lease. It yields events as they happen and feeds an observer if one is bound.

Design: `intent-ecosystem/vision/09-the-agentic-system.md`; low-level design:
`specs/architecture/runtime.md`.
