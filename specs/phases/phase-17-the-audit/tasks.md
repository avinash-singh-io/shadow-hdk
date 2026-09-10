---
type: Tasks
phase: 17-the-audit
---

# Phase 17 — tasks

## Group 1 — BUG-004: the meter survives a park (D33)
- [x] reproduce: a 3-step lease admitted 5 invocations; `seq` restarted; `steps_taken` = 3
- [ ] `RunState.spent` and its reducer; `LeaseMeter.spent`/`restore`; `Emitter.restore`
- [ ] `_stream` seeds from the last checkpoint
- [ ] every package to 0.9.0; schemas republished; `test_versions` reason
- [ ] RED: the seven claims in the plan
- [ ] file the held-children half with its reproduction
- [ ] Gate

## Group 2 — BUG-005: the assistant's calls are in the transcript
- [ ] `Message.tool_calls`; the agent records them; the LangChain adapter builds them
- [ ] RED: the second turn carries them; the adapter's message carries them; a live multi-turn test
- [ ] Gate

## Group 3 — BUG-006: the wire resumes, or says it cannot
- [ ] a checkpointer per session; `initialize` required; callback timeouts; `wire.md` corrected
- [ ] RED: resume over the loopback; run before initialize refused; a hanging callback ends the run
- [ ] records, board, *Pins* rows, status, roadmap
- [ ] Gate
