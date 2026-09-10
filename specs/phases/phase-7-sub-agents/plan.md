---
type: Plan
phase: 7-sub-agents
---

# Phase 7 — plan

```
# Sequential:  Group 0 → Group 1 → Group 2
# Group 0 is the grammar's missing half; Groups 1 and 2 are built on it.
```

## Group 0 — `Await` parks

**Sequential.** Nothing else can wait until this does.

- An `Await` step whose component returns `Pending` parks the run through `interrupt()`, carrying
  the handle the component named
- A resume delivers the answer, which becomes that step's `Completed` observation
- `Invoke` is unchanged: a `Pending` from an ordinary step is still just an observation
- RED: an `Await` on `Pending` parks and emits no `Ended`; a resume finishes it with the answer; an
  `Invoke` returning `Pending` does **not** park

**Commit:** `feat(runtime): an Await that is told to wait, waits`

## Group 1 — spawn, send, release

**Sequential.**

- `Children` on the session: handle → (run id, composition, checkpointer, cancellation, ceiling)
- `RunContext.spawn_child(composition, ceiling)` → a handle; runs until it parks or ends
- `RunContext.send(handle, message)` → resumes the child; its events reach the parent as before
- `RunContext.release(handle)` → cancels the child, settles its lease, forgets the handle
- Each child holds **its own** `Cancellation` (D15), so releasing one leaves its siblings alone
- The `Held` event: a child is resident, and this is the lease it is holding
- RED: a child parks and is held; a send is answered without re-running the child's earlier steps;
  a release ends it; releasing one child leaves a sibling running; cancelling the parent's handle
  still stops a child that inherited it

**Commit:** `feat(runtime): spawn, send, release — a child kept between messages`

## Group 2 — the model's verbs, and the record

**Sequential.**

- `spawn` / `send` / `release` as **pattern** meta-tools (D3 — the runtime knows none of these
  names), alongside `done`, `propose`, `compose`
- RED: the pattern offers them; the runtime's registry does not
- `[~]` anything that cannot be settled without the owner, with the command that would settle it
- tasks, history, status, board; push

**Commit:** `feat(adapters): a model that can start, message and let go of a helper`
