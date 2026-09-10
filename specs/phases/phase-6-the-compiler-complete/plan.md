---
type: Plan
phase: 6-the-compiler-complete
---

# Phase 6 — plan

```
# Sequential:  Group 0 → Group 1 → Group 2
# Group 0 touches the runtime only; Group 1 changes the compiler under it.
```

## Group 0 — cancellation (D15)

**Sequential.** No compiler change, so it lands first and Group 1 inherits a run that can be stopped.

- `Cancellation` in `runtime/cancel.py`: `cancel(reason)`, `cancelled`, `reason`
- `RunOptions.cancellation: Cancellation | None`
- `StepExecutor.invoke` asks it **first**, before the lease — a cancelled run does not spend a step
- `RunContext.spawn_options` passes the parent's handle down, so a subtree stops together
- `_stop_reason` already walks the cause chain; `Cancelled` arrives as `Ended(reason="cancelled")`
- RED: cancelling before the first step; between two steps; a child stops when its parent is
  cancelled; a child given its own handle does **not** stop when the parent's is used; the reason
  the host gave is on the record

**Commit:** `feat(runtime): a host can stop a run, and the record says who asked`

## Group 1 — nested composites are subgraphs

**Sequential.** The compiler's shape changes; everything already green must stay green.

- `_Builder` learns a `subgraphs` map: a composite that is a *child* of another compiles to its own
  `Plan`, added to the parent graph as one compiled node
- The root composition's own top-level steps stay in the root graph — a subgraph per nested
  composite, not per step
- `FanOut` sending to a subgraph node, `Until` whose body is a subgraph node
- The plan cache still keys on the composition, so a nested shape is planned once
- RED: a nested `Sequence` runs in order and its observations reach the parent's state; two scopes
  may reuse a step id; an interrupt inside a subgraph carries its namespace; the benchmark holds

**Commit:** `feat(runtime): a nested composite is a subgraph with a name of its own`

## Group 2 — resume, durability, and the record

**Sequential.**

- RED: a run parked on an `Ask` **inside a nested composite** resumes into that composite and
  finishes
- RED: a run parked with a **file-backed** checkpointer (`langgraph-checkpoint-sqlite`, dev
  dependency) resumes after the original saver object is discarded — durability, not memory
- `[~]` anything that cannot be settled without the owner, with the command that would settle it
- tasks, history, status, board; push

**Commit:** `feat: a parked run survives the process that parked it`
