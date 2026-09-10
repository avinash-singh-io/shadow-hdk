---
type: Plan
phase: 17-the-audit
---

# Phase 17 — plan

```
# Sequential, hardest first. Each group reproduces before it fixes.
```

## Group 1 — BUG-004: the meter survives a park (D33)

- `RunState.spent` — `{steps, cost_cents, unpriced, elapsed_seconds, seq}` under one reducer that
  adds counts and takes the max of marks; `initial_state()` seeds it
- `_step_node` writes what the step spent; `LeaseMeter.spent()` reads its counters out and
  `LeaseMeter.restore()` seeds them; `Emitter.restore(seq)`
- `_stream` reads the last checkpoint before building the session and seeds both
- every package to **0.9.0**; `test_versions` says why; schemas republished
- RED: the filed reproduction (five steps, ceiling of three, an Ask on step 3) ends
  `lease_exhausted`; `seq` strictly increases across the resume; `steps_taken` counts the run; a
  cost charged before the park still counts after it; an unpriced call stays unpriced across it;
  parked wall time does not count against the ceiling; a `FanOut`'s branches merge in any order

**Commit:** `fix(runtime)!: what a run has spent survives the park (D33)`

## Group 2 — BUG-005: the assistant's calls are in the transcript

- `Message.tool_calls: tuple[ToolCall, ...] = ()`; the agent records them; the LangChain adapter
  builds `AIMessage(tool_calls=…)`; kernel minor bump
- RED: a second turn's request carries the assistant's calls with ids matching the tool results;
  the adapter's `AIMessage` carries them; a live multi-turn test behind `-m live` that skips
  without a key

**Commit:** `fix(kernel)!: an assistant message carries the calls it made`

## Group 3 — BUG-006: the wire resumes, or says it cannot

- a checkpointer per session in `_drive`; `initialize` required before `run`; a timeout on every
  callback; `wire.md` corrected on the run token and HTTP/2
- RED: a resume over the loopback returns the answer; a `run` before `initialize` is refused; a
  host that hangs in `judge` ends the run rather than the wall ceiling; `serve` says loopback-only

**Commit:** `fix(wire): a parked run resumes over the wire, and unbuilt is said plainly`

## Records

tasks, history, status, roadmap, board, *Pins* rows for 0.9.0 and the kernel bump.
