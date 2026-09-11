---
type: Phase
phase: 17
name: the-audit
epic: 0008-what-the-audit-found
status: complete
topics: [audit, leases, resume, durability, transcript, wire, d33]
deps: [phase-16-mqtt]
---

# Phase 17 — What the audit found

## Why this phase exists

A full-codebase review landed in `specs/backlog/backlog.md` on 2026-09-10: eleven bugs and seven
tech-debt items, written by another agent, several naming line numbers. The rule for this phase is
that **every row is reproduced before it is fixed** — one of them was already right about this
lane's own gate, and being right eleven times is not the same as being right this time.

**What it changed about what this lane had claimed.** BUG-007 (fixed before this phase, `8a9e566`)
found that `mypy_path` omitted `wire`, `contained` and `derivation`; all three ship `py.typed`, so
mypy silenced them as site-packages. Every *mypy 0* reported from Phase 9 to Phase 16 excluded the
wire package, where nine errors sat. The gate now covers 116 files and an invariant asserts the set
of packages. That is the standard the rest of this phase is held to: a claim is what a test makes
true, not what a summary says.

## Group 1 — BUG-004: what a run has spent survives a park

**Reproduced, exactly as filed.** Five sequential steps under a `Ceiling(max_steps=3)`, with
governance asking on step 3:

```
first:  steps invoked = 2   seq = [0…6]   ended = []
after:  steps invoked = 5   seq = [0…6]   ended = [(completed, 3)]
VERDICT: a lease of 3 steps allowed 5 invocations
```

`run` and `resume` both call `_stream`, which builds a fresh `Session`, `LeaseMeter` and `Emitter`
every time; `RunState` carries handles, observations and iterations and nothing about spend. So the
meter starts at zero on every resume, `seq` restarts at 0 for the same run id, and `Ended.steps_taken`
reports the last leg rather than the run. `refusal.md`'s argument that *the bound has to be
structural* rests on this bound holding, and an Ask is the ordinary way a governed run pauses — so
this is the lease failing in its most common case, not an exotic one.

### D33 — what a run has spent is part of the run, and the checkpoint is where it lives

The meter's counters — steps, priced cost, whether the price is known, elapsed seconds, and the
emitter's sequence — ride in `RunState` as plain JSON (D19) and are read back when a run resumes.
One field, `spent`, with a reducer that adds counts and takes the maximum of the marks, so a
`FanOut`'s concurrent branches merge in any order.

**Parked time is not spent time.** `max_wall_seconds` bounds the run's own elapsed time, and a run
waiting for a human is not running: a person who takes a day to answer must not find the budget
gone. So elapsed seconds accumulate across legs rather than being measured from the first start.
The alternative — wall-clock from the beginning — turns every Ask into a race against a deadline
nobody told the human about.

**Rejected.** *A durable meter behind a port* — that is state the runtime owns, which `09` §6
refuses; the checkpoint is the host's. *Passing the meter back in `RunOptions`* — it would make
every host reimplement the accounting, and a host that forgot would silently get the bug back.
*Counting a re-run node once* — the node really does run again (BUG-010), and a meter that hid that
would be lying in the other direction; the count is what ran, and BUG-010 is where the re-run
itself is fixed.

**Contract change: 0.8.0 → 0.9.0** (D9) with a *Pins* row — `RunState` grows a field, and a host
reading graph state directly sees it.

**Not in this group, and filed rather than half-done.** A parent that parks while holding a child
still resumes with `children.held == ()`: a `HeldChild` carries a checkpointer and a cancellation
handle, which are objects, not JSON, so restoring one is a design question of its own rather than a
field. Filed as its own row with the reproduction, so it is a decision somebody makes rather than a
sentence in a phase nobody reads.

## Group 2 — BUG-005: the assistant's tool calls reach the model

`Message` (kernel) has `role`, `content` and `tool_call_id` and nothing for an assistant's calls;
the agent appends the text and drops them; the LangChain adapter emits a bare `AIMessage` before
the `ToolMessage`s. Every real provider rejects a tool result with no preceding call. Every agent
test uses `ScriptedModel`, which never checks — so the suite is green and a real second turn is not.

## Group 3 — BUG-006: the wire's resume, and what `serve` admits

`_drive` builds `RunOptions` with no checkpointer, so every resume over the wire raises; nothing
covers it. `open_session` issues a session on a bare GET with no credential; `_initialize` is never
required; no callback has a timeout. Either the wire resumes or it says it cannot — and what is not
built is said plainly in `wire.md` rather than listed as fixed.

## Done when

- Group 1: the reproduction above ends `lease_exhausted` after three steps, `seq` is monotone
  across a resume, `Ended.steps_taken` counts the run; every package 0.9.0, *Pins* row, schemas
  republished
- Group 2: an assistant message carries its calls; the LangChain adapter builds them; one live
  multi-turn test behind `-m live` that skips without a key
- Group 3: a resume over the wire works or refuses honestly; `initialize` required; a callback
  timeout; `wire.md` says what is unbuilt
- gate: ruff 0, format 0, mypy 0 over every package, pytest 0; every mutation bites or is named
