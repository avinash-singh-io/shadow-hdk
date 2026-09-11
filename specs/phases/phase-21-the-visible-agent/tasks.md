---
type: Tasks
phase: 21
---

# Tasks — Phase 21, The visible agent

## Group 1 — `Reasoned`
- [x] `Reasoned` in the kernel, in the union, in `CONTRACTS`, round-tripping
- [x] `ModelResponse.reasoning`, `ModelChunk.reasoning`, `Turn.reasoning` — defaulting empty
- [x] `RunContext.reasoned(text)`; empty emits nothing
- [x] the agent adapter emits after a model turn that reasoned
- [x] LangChain reads provider reasoning where exposed
- [x] `jsonl` reads Claude Code's thinking blocks; ACP reads `agent_thought_chunk`
- [x] telemetry carries length, never text
- [x] every package to 0.15.0; `EXPECTED` and its reason

## Group 2 — the projection
- [x] `Step` and `steps(events)` — a pure fold, tested on a recorded stream
- [x] nesting by run id: a child's steps fold under its parent's `Spawned`
- [x] `run_steps(...)` live
- [x] the wire: a `step` notification beside `event` on the existing SSE session (one path, not two); the schema published

## Group 3 — deferred schemas
- [x] the pattern field; `describe` fetches on first use
- [x] two hundred tools cost two hundred lines, counted

## Group 4 — offloading
- [x] `Pattern.offload_over` — a pattern field beside `catalogue_threshold`, not `RunOptions` (D47)
- [x] a large observation is held by the agent — never a file (D47); the model sees a handle, a size, a preview
- [x] the sink and the record still get the whole thing

## Close
- [x] D45–D47 recorded; index regenerated
- [x] the coder example shows reasoning on a live turn
- [x] README: twelve kinds
- [ ] status, roadmap, changelog, board
