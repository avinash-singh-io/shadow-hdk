---
type: Phase
phase: 1
name: real-adapters
epic: 0001-the-bare-harness
status: complete
topics: [adapters, langchain, ollama, huggingface, mcp, modes, streaming, ports]
deps: [phase-0-the-runtime]
---

# Phase 1 — Real adapters, streaming, and modes

## Goal

The bare harness stops being a demo of stubs. A **real** model answers through one adapter that
covers every provider LangChain integrates; a **real** MCP server's tools arrive as components with
their effect profiles derived from annotations; and **modes** exist, so a product can say what its
agent may do without writing a governance port.

## Why these three together

They are the three things a host must bring before it can use this for anything: something that
thinks, something to do, and a rule about what is allowed. Phase 0 proved the shape with doubles;
this phase is the first time the shape meets something it did not write.

## Key decisions

Inherited from Epic 0001 (D1–D13). Three that shape this phase, and one new:

| # | in this phase |
|---|---|
| D8 | the doubles stay; the real adapters sit beside them and pass the same contract suites |
| D9 | `ModelPort.stream` is a **contract change**: a minor bump on every package, plus a *Pins* row on the board |
| D12 | one adapter over LangChain's integrations rather than one per vendor; a direct adapter only where LangChain has nothing |
| **D14** | **a port may grow a method with a default.** `stream` is added to `ModelPort` with a fallback that calls `complete` and yields one chunk, so every existing adapter keeps working. This is the refuse-not-crash rule (`09` §3) applied to a *method* rather than a whole port |

## Scope

### In
- `packages/adapters/langchain` — one `ModelPort` built with `init_chat_model`; providers as optional extras; tool calls and usage translated both ways; `stream`
- `packages/adapters/mcp` — an MCP server (stdio) becomes a `ComponentPort`; annotations become effect profiles; anything undeclared assumes the worst
- `packages/adapters/modes` — `Mode(name, ceiling, ask_above)` and `ModeGovernance`; layers compose by `EffectProfile.meet`
- `ModelPort.stream` in the kernel, with its default
- Every new adapter subclasses its port's contract suite
- The bare-harness demo runnable against a real model and a real MCP server

### Out
- ACP and the recording server (Phases 4–5) · files and code (Phase 3) · the rules-as-rows engine and mode *files* checked in CI (Phase 10) · a TypeScript client (Phase 9)

## Deliverables

| # | Deliverable | Verification |
|---|---|---|
| 1 | `ModelPort.stream` and its default | `uv run pytest tests/kernel tests/adapters/contract` |
| 2 | `adapters/langchain`, contract-tested against a fake chat model | `uv run pytest tests/adapters/langchain` |
| 3 | The same adapter against **live Ollama** | `uv run pytest -m live_ollama` |
| 4 | `adapters/mcp`, against a real MCP server over stdio | `uv run pytest tests/adapters/mcp` |
| 5 | `adapters/modes` | `uv run pytest tests/adapters/modes` |
| 6 | The demo on real components | `uv run python examples/real.py` |
| 7 | Every package at the new minor version | `uv run pytest tests/test_versions.py` |

## Acceptance criteria — checked 2026-09-10

| | criterion | evidence |
|---|---|---|
| ✅ | A composition runs end to end with a **real** model and a **real** MCP server, zero product code | `tests/test_real_harness.py`, 7 live tests, 34.6 s |
| ✅ | An MCP tool that declares nothing is `ASSUME_WORST`, and a mode refuses it | `test_a_tool_that_declares_nothing_is_assumed_to_be_the_worst`; and live, where `wipe`/`mystery`/`explode` never entered the catalogue |
| ✅ | A team mode layered on a base can only narrow | `test_layering_is_narrowing_whatever_the_layers_say` (hypothesis) |
| ⏸ | **Tokens from a streaming model reach the observer before the call returns** | **Not met, and deliberately not forced** — see below |
| ✅ | Every adapter passes the contract suite for the port it implements | 5 suites, 6 adapters + 5 doubles |

**Why the streaming criterion is left open.** `ModelPort.stream` exists, has a default, and is
contract-tested against a fake *and* a live provider. What is missing is the last hop: the agent
adapter calls `complete`, and carrying deltas onward would need a **tenth event kind**, because
`09` §7's stream is `Started · Composed · Invoked · Observed · Proposed · Refused · Asked · Spawned
· Ended` and none of them is a token.

Adding one is a kernel change with an ADR (D9, D14), and it belongs where it is actually needed:
**Phase 9, the wire**, where a host watching over SSE is the reason tokens matter at all. Forcing it
here would add an event kind nothing consumes, to satisfy a line in this document. The criterion was
written before that was understood; it is carried forward rather than ticked.

## Non-goals worth stating

- **No paid provider is called by the suite.** Live tests run against local Ollama only; the
  OpenAI/Anthropic paths are exercised through a fake chat model that satisfies LangChain's
  interface. Spending someone's money is not something a test suite gets to decide.
