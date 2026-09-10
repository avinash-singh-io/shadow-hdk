---
type: Phase
phase: 6
name: the-compiler-complete
epic: 0003-composition-at-scale
status: not-started
topics: [compiler, subgraphs, checkpoints, resume, cancellation, langgraph, d15]
deps: [phase-0-the-runtime]
---

# Phase 6 — The compiler, complete

## Goal

Phase 0 compiled the grammar and stopped where the shortcut still held. Three things were left,
and each is a place where the runtime currently cannot say *where* something happened or *stop* it:

| left in Phase 0 | why it matters now |
|---|---|
| a nested composite is **inlined** | one flat namespace: two scopes cannot reuse a step id, and nothing can be resumed or cancelled *per branch* |
| nothing raises `Cancelled` | `errors.py` has had the class since Phase 0 and `EndReason` has had `"cancelled"`. A host with a runaway run has no gesture |
| `resume` is proven on a flat graph only | Phase 7's sub-agents park inside nested scopes, which is the case nobody has run |

The fourth deliverable, **host checkpointers**, is already a parameter (`RunOptions.checkpointer`).
What is missing is not code but a measurement: everything has been proven against `InMemorySaver`,
which is not durability. This phase parks a run, throws the saver away, and resumes from a file.

## The shape

```
root graph
├── s1            Invoke        a node
├── inner         Sequence      a SUBGRAPH node, checkpoint namespace "inner"
│   ├── a         Invoke
│   └── b         Invoke        may Ask here — the interrupt carries the namespace
└── s2            Invoke
```

A nested composite becomes a compiled graph added as one node. Its state schema is the same
`RunState`, so handles and observations flow through the parent's reducers unchanged; what it gains
is a checkpoint namespace, which is the thing every later feature needs a name from.

## D15 — cancellation is a handle the host holds, checked where the lease is checked

A run stops for a reason, and the reasons already have one shape: **the executor asks, before it
spends a step, whether it may.** The lease is asked that question at the top of `invoke`.
Cancellation is the same question from a different asker, so it is asked in the same place — first,
before the lease, because a cancelled run should not spend the step it was about to be refused for.

```python
cancellation = Cancellation()
events = run(composition, ports, options=RunOptions(lease=…, cancellation=cancellation))
…
cancellation.cancel("the user closed the tab")   # → Ended(reason="cancelled")
```

Three properties, each of which is a test:

1. **A child inherits its parent's cancellation** unless handed its own. Cancelling a parent stops
   the subtree, because a child that outlived the run that spawned it is a leak with a budget.
2. **A cancelled run stops at a step boundary, not mid-step.** A component already running is not
   interrupted — the harness does not own other people's code. The next step does not start.
3. **The reason reaches the record.** `Ended(reason="cancelled")`, and the host's words are on it.

*Considered and rejected:* a `CancelPort`. Ports are what the **host implements for the runtime**;
this is the host reaching *in*, which is what `Lease` already is. Making it a port would mean the
runtime polls the host on every step for a value the host already knows.

*Considered and rejected:* cancelling the asyncio task. It would work and it would say nothing —
no `Ended`, no reason, no record, and a component mid-write cut in half.

*Overturned by:* a host that needs to stop a run *between* two of its own awaits rather than at a
step boundary, which would mean step granularity is too coarse and the executor needs a checkpoint
inside `invoke`.

## What is NOT in this phase

- **Branch-level cancel** (cancel one fan-out arm, keep the others) — Phase 7, with sub-agents,
  which is the first thing that has branches worth keeping.
- **`run.*` events** for spawn/send/release — Phase 7.
- A checkpointer we ship. The host brings one; we prove we can use somebody else's.

## Exit criteria

- A nested composite is a subgraph with its own namespace, and the benchmark still meets D11's budget
- A host can cancel a run and the record says so, including a child's
- A run parked inside a nested composite resumes into that composite
- A run parked with a **file-backed** checkpointer resumes after the saver object is gone
