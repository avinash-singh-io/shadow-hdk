---
type: Tasks
phase: 6-the-compiler-complete
---

# Phase 6 — tasks

## Group 0 — cancellation (D15)

- [x] `runtime/cancel.py` — `Cancellation` with `cancel(reason)`, `cancelled`, `reason`
- [x] `RunOptions.cancellation`
- [x] `StepExecutor.invoke` asks it before the lease
- [x] `spawn_options` passes the handle down
- [x] RED: cancelled before the first step → no step runs, and none is **charged**
- [x] RED: cancelled between two steps → the second does not run
- [x] RED: a child stops when its parent's handle is cancelled
- [x] RED: a child holding its own handle survives the parent's
- [x] RED: the host's reason is on `Ended` — a new `Ended.detail`, general rather than
      cancellation-only, so every package moves to **0.4.0** (D9)
- [x] RED: the first reason is the one recorded
- [x] Gate

## Group 1 — nested composites are subgraphs

- [x] `_Builder` compiles a nested composite to its own `Plan`
- [x] `compile_composition` adds it as one node, with its checkpoint namespace
- [x] `FanOut` nested in a sequence; `Until` nested in one — each with a test
- [x] the plan cache still keys on the composition
- [x] RED: a nested composite is **one node** of the root graph (the discriminating test); it
      runs in order; its observations reach the parent's state
- [~] ~~two scopes may reuse a step id~~ — **wrong, and replaced.** `RunState.handles` is one
      flat dict keyed by step id, and that flatness is what lets a `Binding` reach an earlier
      sibling in an outer scope. See the scope change in history
- [x] RED: a duplicate step id ends the run rather than running a graph nobody wrote
- [x] RED: an `Ask` raised inside a subgraph parks the whole run
- [x] the benchmark, with a nested case added: **53.0 ms flat, 60.7 ms across ten subgraphs**
      (0.607 ms/step against D11's 1 ms)
- [x] Gate

## Group 2 — resume, durability, and the record

- [x] RED: a run parked on an `Ask` inside a nested composite resumes into it
- [x] `langgraph-checkpoint-sqlite` as a dev dependency
- [x] RED: a run parked with a file-backed checkpointer resumes after the saver is discarded
- [x] RED: two runs on one shared checkpointer each wake where they slept
- [x] records, board, status
- [x] Gate
