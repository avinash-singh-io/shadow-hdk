---
type: Tasks
phase: 1-real-adapters
---

# Phase 1 — tasks

## Group 0 — the port grows a method

- [x] `ModelChunk(text, tool_calls, usage, done)` in `kernel/ports.py`
- [x] `ModelPort.stream(request) -> AsyncIterator[ModelChunk]`
- [x] `streaming_by_completing` — the default an adapter inherits: call `complete`, yield one chunk (D14)
- [x] RED: `tests/kernel/test_streaming.py` — the default yields exactly one chunk carrying the whole response; a real streamer yields many and the last carries the usage
- [x] `ModelPortContract` gains: `stream` yields at least one chunk; the concatenated text equals `complete`'s; usage is a number or `None`
- [x] `ScriptedModel.stream` — deltas from the scripted text, so replay still works
- [x] every package to the new minor version; `test_versions.py` updated
- [x] Gate

## Group 1 — one model adapter, every provider

- [x] `packages/adapters/langchain/pyproject.toml` with extras `openai`, `anthropic`, `ollama`, `huggingface`
- [x] `LangChainModel(spec, **kw)` — `init_chat_model` under the hood, nothing vendor-specific above it
- [x] `Message` → langchain messages, including `tool` messages carrying `tool_call_id`
- [x] `Interface` → a tool schema langchain will bind
- [x] `AIMessage.tool_calls` → our `ToolCall`, arguments as JSON
- [x] `usage_metadata` → `Usage`; **absent means `None`, never `0`**
- [x] `stream` over `astream`
- [x] RED: `tests/adapters/langchain/` against a fake `BaseChatModel` — text, tool calls, usage, streaming, and a model that reports no usage
- [x] `TestLangChainModelIsAModelPort(ModelPortContract)`
- [x] live: the same adapter against **real HuggingFace Inference Providers**, marked `live`,
      deselected by default. Ollama was the plan until the owner supplied an HF token mid-phase
- [x] Gate

## Group 2 — components arriving over MCP

- [ ] `packages/adapters/mcp/pyproject.toml` depending on the official `mcp` SDK
- [ ] `McpComponents` — a stdio session, opened once and held
- [ ] `tools/list` → registrations, `inputSchema` carried verbatim
- [ ] annotations → `EffectProfile.from_mcp_annotations`; **absent → `ASSUME_WORST`**
- [ ] `tools/call` → `Completed`; `isError` → `Failed`; a transport error → `Failed`, never a raise
- [ ] RED: `tests/adapters/mcp/` against a **real** server over stdio, written for the test
- [ ] a tool that declares nothing is `ASSUME_WORST`, and a mode that forbids reaching refuses it
- [ ] `TestMcpComponentsIsAComponentPort(ComponentPortContract)`
- [ ] Gate

## Group 3 — modes

- [x] `packages/adapters/modes/pyproject.toml`
- [x] `Mode(name, ceiling, ask_above)`; `ModeGovernance(modes, key, default)`
- [x] `Allow` when the profile narrows the ceiling; `Ask` when it narrows the ceiling but not the ask line; `Refuse` otherwise
- [x] `layer(base, over)` — composition by `EffectProfile.meet`
- [x] RED: `tests/adapters/modes/` — the four example modes; an unknown mode refuses and says so; a hypothesis property that a layer can only narrow
- [x] `TestModeGovernanceIsAGovernancePort(GovernancePortContract)`
- [x] Gate

## Group 4 — the demo on real components

- [ ] `examples/real.py` — the bare harness on a real model and a real MCP server
- [ ] `tests/test_real_harness.py`, marked `live_ollama`, skipped **with a reason** when nothing serves
- [ ] markers registered in `pyproject.toml`; CI runs the fake path
- [ ] exit criteria checked, with numbers, into `history.md`
- [ ] board: lane H row + log line; `specs/status.md`
- [ ] Gate
