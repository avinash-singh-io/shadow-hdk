---
type: Tasks
phase: 6-the-compiler-complete
---

# Phase 6 — tasks

## Group 0 — cancellation (D15)

- [ ] `runtime/cancel.py` — `Cancellation` with `cancel(reason)`, `cancelled`, `reason`
- [ ] `RunOptions.cancellation`
- [ ] `StepExecutor.invoke` asks it before the lease
- [ ] `spawn_options` passes the handle down
- [ ] RED: cancelled before the first step → no step runs
- [ ] RED: cancelled between two steps → the second does not run
- [ ] RED: a child stops when its parent's handle is cancelled
- [ ] RED: a child holding its own handle survives the parent's
- [ ] RED: the host's reason is on `Ended`
- [ ] Gate

## Group 1 — nested composites are subgraphs

- [ ] `_Builder` compiles a nested composite to its own `Plan`
- [ ] `compile_composition` adds it as one node, with its checkpoint namespace
- [ ] `FanOut` to a subgraph node; `Until` whose body is one
- [ ] the plan cache still keys on the composition
- [ ] RED: a nested `Sequence` runs in order; its observations reach the parent's state
- [ ] RED: two scopes may reuse a step id
- [ ] RED: an interrupt inside a subgraph carries its namespace
- [ ] the benchmark still meets D11's budget — the number, recorded
- [ ] Gate

## Group 2 — resume, durability, and the record

- [ ] RED: a run parked on an `Ask` inside a nested composite resumes into it
- [ ] `langgraph-checkpoint-sqlite` as a dev dependency
- [ ] RED: a run parked with a file-backed checkpointer resumes after the saver is discarded
- [ ] records, board, status
- [ ] Gate
