---
type: Tasks
phase: 7-sub-agents
---

# Phase 7 — tasks

## Group 0 — `Await` parks

- [x] an `Await` whose component returns `Pending` parks through `interrupt()` under its handle
- [x] a resume delivers the answer as that step's `Completed` observation
- [x] `Invoke` unchanged — a `Pending` there is an observation, not a park
- [x] RED: each of the above, including that the wait is recorded **once**
- [x] Gate

## Group 1 — spawn, send, release

- [x] `Children` registry, reached as `RunContext.children`
- [x] `children.spawn(composition, ceiling)` → handle, and the child's events
- [x] `children.send(handle, message)`
- [x] `children.release(handle)`
- [x] each child holds its own `Cancellation` (D15)
- [x] the `Held` event — the tenth kind — and every package to **0.5.0** (D9)
- [x] RED: a child parks and is held
- [x] RED: a send is answered without re-running the child's earlier steps
- [x] RED: a release ends the child `cancelled` and the parent forgets it
- [x] RED: releasing one child leaves a sibling running
- [x] holding costs the parent **what the child spent** (2 steps), not the child ceiling (10) —
      measured, and it corrected what D16 first claimed
- [~] cancelling the parent's handle still stopping an inheriting child is already covered by
      Phase 6's `test_cancelling_a_parent_stops_its_child`; not duplicated here
- [x] Gate

## Group 2 — the model's verbs, and the record

- [~] **deferred to Phase 8, with the reason.** D3 says meta-tools belong to the Pattern, and a
      model-facing `spawn` needs the Pattern to shape the child — a brief, then a wait — which is
      a *pattern*, and patterns are Phase 8's subject. The runtime half is done and tested; what is
      missing is the shape, not the mechanism
- [x] the **mailbox**: the component a held child waits on, shipped in `adapters/basic` so the
      shape is a convention rather than three lines each host writes under its own name
- [x] RED: a child held on the real mailbox with nothing doubled; and the narrowest mode there is
      still lets a child wait, which is why the empty effect profile is load-bearing
- [x] TD-001 recorded: our observation classes ride in graph state, which LangGraph will block in
      a future version. Measured green today under `LANGGRAPH_STRICT_MSGPACK=true`
- [x] records, board, status
- [x] Gate
