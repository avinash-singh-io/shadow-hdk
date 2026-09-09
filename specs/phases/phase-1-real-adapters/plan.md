---
type: Plan
phase: 1-real-adapters
---

# Phase 1 — plan

```
# Mixed:  Group 0 → (Groups 1 + 2 + 3 in parallel) → Group 4
```

Group 0 changes a kernel contract, so everything waits for it. The three adapters touch no shared
file and can be built in any order. Red first, every assertion mutation-checked.

---

## Group 0 — the port grows a method

**Sequential. Blocks everything.**

- `ModelPort.stream(request) -> AsyncIterator[ModelChunk]` and `ModelChunk` in the kernel
- **The default**: a `stream` mixin that calls `complete` and yields one chunk, so an adapter that
  does not implement it keeps working (D14)
- `ModelPortContract` gains streaming cases; `ScriptedModel` gains `stream`
- Every package to the new minor version; the *Pins* row on the board

**Commit:** `feat(kernel)!: ModelPort grows stream, with a default that keeps every adapter working`

---

## Group 1 — one model adapter, every provider

**Parallel with Groups 2 and 3.**

- `packages/adapters/langchain` — `LangChainModel(spec, **kw)` over `init_chat_model`
- Messages both ways: our `Message` ↔ langchain's `BaseMessage`; `Interface` → tool schema;
  `AIMessage.tool_calls` → our `ToolCall`; `usage_metadata` → `Usage`, with **unknown as `None`**
- `stream` over `astream`, yielding text deltas
- Optional extras: `openai`, `anthropic`, `ollama`, `huggingface`
- Contract suite against a fake `BaseChatModel`; a `live_ollama` marker for the real one

**Commit:** `feat(adapters): one model port over every LangChain provider`

---

## Group 2 — components arriving over MCP

**Parallel with Groups 1 and 3.**

- `packages/adapters/mcp` — `McpComponents(server)` over the official SDK's stdio client
- `tools/list` → registrations; annotations → `EffectProfile.from_mcp_annotations`; **absent
  annotations mean `ASSUME_WORST`, never a guess**
- `tools/call` → `Observation`; an error result is `Failed`, not an exception
- The session's lifetime is the adapter's, not a run's
- Tested against a **real** MCP server written for the test and spoken to over stdio

**Commit:** `feat(adapters): an MCP server's tools become components`

---

## Group 3 — modes

**Parallel with Groups 1 and 2.**

- `packages/adapters/modes` — `Mode(name, ceiling, ask_above)`, `ModeGovernance(modes, key, default)`
- Layering by `EffectProfile.meet`, with a property test that a layer can only narrow
- Four shipped modes as examples — `read`, `build`, `act`, `auto` — as *data in the tests*, not as a
  vocabulary the adapter imposes
- An unknown mode name **refuses**, and says so; it never falls back to a wider one

**Commit:** `feat(adapters): modes are data — a ceiling and an ask line`

---

## Group 4 — the demo on real components

**Sequential. Last.**

- `examples/real.py` — the bare harness with `LangChainModel("ollama:…")` and a real MCP server
- `tests/test_real_harness.py`, marked `live_ollama`, skipped with a *reason* when nothing is serving
- `pytest.ini` markers registered; CI runs the fake path, the live path is opt-in
- Phase 1's exit criteria checked and recorded with numbers

**Commit:** `feat: the harness runs on a real model and a real MCP server`
