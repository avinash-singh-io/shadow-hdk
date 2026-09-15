# `shadow_hdk.adapters.agent`

**The agent loop is a component** (D1). There is no `run_agent()` beside `run()`: "run one agent" is
a composition of one step, and "an orchestrator with workers" is an agent component whose
composition invokes other agent components.

**What kind of agent** is a `Pattern` — data, not a code path:

```python
single = Pattern("single", ROLE, meta_tools={"propose", "done"})
orchestrator_workers = Pattern(
    "orchestrator-workers", ROLE, meta_tools={"compose", "propose", "done"}
)
```

`single` offers the model no `compose`, so it **cannot** change its shape: it sees its tools and
answers. That is a fully deterministic one-agent product on the same runtime a dynamic product uses.
Adding a pattern — today's or one invented in five years — is a file.

`ModelAgent(model=..., pattern=...)` exposes that loop as an `AgentPort`. A product can therefore
hand a model API or a resident CLI to the same `Thread`, `Harness` and `ServeHost` lifecycle rather
than maintaining two product integrations. It sees only the `ToolSource` supplied at open, reports
unknown usage honestly, maps parked work to the durable child run, and cancels an active model call
when the thread is interrupted.
