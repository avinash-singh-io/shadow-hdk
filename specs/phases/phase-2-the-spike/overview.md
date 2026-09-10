---
type: Phase
phase: 2
name: the-spike
epic: 0001-the-bare-harness
status: not-started
topics: [acp, spike, j1, usage, permission, refusal]
deps: [phase-1-real-adapters]
---

# Phase 2 — The spike

## Goal

Answer **J1** on `intent-ecosystem/lanes/board.md` — the half-day question the roadmap called *"the
only thing that can invalidate the shape"*:

1. **Does a CLI agent whose tool call is refused end its turn cleanly**, or does it hang or loop?
2. **Does ACP report token usage?**

R2 is built on the answers. If a refused tool call leaves a child agent wedged, driving somebody
else's CLI is not a mechanism we can govern. If ACP reports no usage, the meter records *unknown*
for every subscription-backed turn, and the product has to say so.

## What can be measured here, and what cannot

`codex` is not installed. `claude` **is** (2.1.235) but has no native ACP mode — Claude Code speaks
ACP through Zed's `claude-code-acp` npm bridge, which is not installed either. Installing global
packages on the owner's machine and spending their subscription while they are asleep are both
things this session will not do unasked.

So the spike is split, and the split is stated rather than blurred:

| | question | answerable here |
|---|---|---|
| **protocol** | what does ACP *provide* for refusal and usage | **yes** — the schema is the answer |
| **transport** | does a refused call end a turn cleanly over a real stdio pipe | **yes** — with our own conformant agent |
| **implementation** | what do Codex and Claude Code *actually do* | **no** — needs those CLIs |

The third is written down as exactly what remains and exactly what would settle it.

## Scope

### In
- Read the `agent-client-protocol` schema for every field bearing on J1
- Build a **minimal conformant ACP agent and client** and run them against each other over stdio
- Measure: a permission denial, a rejection option, an agent-side refusal, and a turn's usage
- Record the answer on the board's J1 row, with what is still open

### Out
- The ACP bridge itself (Phase 4) · the RecordingServer (Phase 5) · installing anything global

## Deliverables

| # | Deliverable | Verification |
|---|---|---|
| 1 | The protocol reading, with field names and types | `specs/phases/phase-2-the-spike/history.md` |
| 2 | A minimal ACP agent + client over stdio | `uv run pytest tests/spikes/acp` |
| 3 | Measured behaviour for all four refusal and usage shapes | the same tests |
| 4 | J1 answered on the board, with what remains | `../intent-ecosystem/lanes/board.md` |

## Acceptance criteria

- Every claim about ACP names the field or the run that proves it — no claim from documentation alone.
- A turn whose tool call is denied **ends**, with a stop reason, in a bounded time, proven by a test
  with a timeout rather than by an assertion that would hang.
- What Codex and Claude Code do is written as *unmeasured*, with the one command that would measure it.
