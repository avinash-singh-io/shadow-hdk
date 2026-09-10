---
type: Tasks
phase: 7-sub-agents
---

# Phase 7 — tasks

## Group 0 — `Await` parks

- [ ] an `Await` whose component returns `Pending` parks through `interrupt()` under its handle
- [ ] a resume delivers the answer as that step's `Completed` observation
- [ ] `Invoke` unchanged — a `Pending` there is an observation, not a park
- [ ] RED: each of the above
- [ ] Gate

## Group 1 — spawn, send, release

- [ ] `Children` registry on the session
- [ ] `RunContext.spawn_child(composition, ceiling)` → handle
- [ ] `RunContext.send(handle, message)`
- [ ] `RunContext.release(handle)`
- [ ] each child holds its own `Cancellation` (D15)
- [ ] the `Held` event, and the version bump it costs (D9)
- [ ] RED: a child parks and is held
- [ ] RED: a send is answered without re-running the child's earlier steps
- [ ] RED: a release ends the child and settles its lease
- [ ] RED: releasing one child leaves a sibling running
- [ ] RED: cancelling the parent's handle still stops an inheriting child
- [ ] Gate

## Group 2 — the model's verbs, and the record

- [ ] `spawn` / `send` / `release` meta-tool interfaces on the pattern
- [ ] RED: the pattern offers them and the runtime does not know the names
- [ ] records, board, status
- [ ] Gate
