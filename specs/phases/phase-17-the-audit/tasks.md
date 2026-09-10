---
type: Tasks
phase: 17-the-audit
---

# Phase 17 — tasks

## Group 1 — BUG-004: the meter survives a park (D33)
- [x] reproduce: a 3-step lease admitted 5 invocations; `seq` restarted; `steps_taken` = 3
- [x] `RunState.spent` and its reducer; `LeaseMeter.spent`/`restore`; `Emitter.restore`
- [x] `_stream` seeds from the last checkpoint — and from the interrupt's own `resume_seq`, because the state's mark is written when a node *returns* and a parking step emits after that
- [x] every package (17) to 0.9.0; schemas republished (unchanged — `RunState` is not a published contract); `test_versions` reason
- [x] RED: the seven claims in the plan, plus an await's numbering, a reused thread, the reducer's commutativity and the emitter's floor — 14 tests
- [x] file the held-children half with its reproduction — **BUG-015**, P1
- [x] Gate — ruff 0 / format 0 / mypy 0 (117 files) / pytest 711 passed, 9 deselected; 17 mutations, all bite

## Group 2 — BUG-005: the assistant's calls are in the transcript
- [x] `Message.tool_calls`; the agent records them; the LangChain adapter builds them
- [x] RED: every tool result's call is in some assistant message (asserted over the whole transcript); which tool and with what; a plain answer carries none; the contract round-trips; the adapter's `AIMessage` carries them; arguments that are not a mapping are carried, not dropped; **a live multi-turn test** behind `-m live` that skips without a key — 7 tests
- [x] every package to 0.10.0 (`ModelRequest` is a published contract); schemas republished
- [x] Gate — ruff 0 / format 0 / mypy 0 (118 files) / pytest 717 passed, 10 deselected; 5 mutations bite and one was a redundant literal, deleted

## Group 3 — BUG-006: the wire resumes, or says it cannot
- [x] a checkpointer per session (`RuntimeSide(checkpointer=…)`, defaulting to one that lives as long as the session); `initialize` required for **both** `run` and `resume`; an omitted version is a mismatch; a callback timeout on the runtime's peer, defaulting finite; a token on `serve`, and loopback-only without one; `wire.md` corrected on all four points and on HTTP/2
- [x] RED: resume over the loopback; the resumed run keeps its lease (D33 across the wire); run and resume before initialize refused; silence is not agreement; a wrong version still refused; a hanging `judge` ends the run naming the method; the default timeout is finite; a session on loopback; a token required, a wrong token refused; a routable host without a token refused before it binds — 12 tests
- [x] records, board, status, roadmap — no *Pins* row: no contract moved (the wire's own protocol version is unchanged)
- [x] Gate — ruff 0 / format 0 / mypy 0 (119 files) / pytest 729 passed, 10 deselected; 15 mutations, all bite
