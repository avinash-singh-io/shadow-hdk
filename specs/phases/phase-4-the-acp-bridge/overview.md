---
type: Phase
phase: 4
name: the-acp-bridge
epic: 0002-the-workspace-and-driving-another-agent
status: not-started
topics: [acp, bridge, subscription, governance, permission, usage, cost]
deps: [phase-3-workspace-and-code]
---

# Phase 4 — The ACP bridge

## Goal

**Another agent, driven as a component.** Codex, Claude Code, or anything else that speaks Zed's
Agent Client Protocol becomes a `ComponentPort` like any other: the agent composes it into a step,
governance judges it, its lease is carved from the parent's, and everything it does comes back as
observations.

This is R2's mechanism — *your own subscription answers the turn* — and `09` §8 puts it plainly:
**driving a locally installed agent over ACP is the harness's business; whether this deployment
allows it, and whose plan covers it, is the product's.**

## What Phase 2 already settled

`specs/phases/phase-2-the-spike/history.md` is the reference, and it changes the shape of this
phase. Measured, not assumed:

| | |
|---|---|
| `acp.Client` is **fourteen methods**, not two | the bridge is a governance surface, not a wrapper around `prompt` |
| A turn always ends with a `StopReason` from a closed set | "did it finish" needs no heuristic |
| There are **two ways to say no** — `DeniedOutcome`, and `AllowedOutcome` carrying a `reject_*` option id | the bridge has to choose, deliberately |
| **Nothing in ACP stops an agent looping on a denial** | the bridge needs its own wall clock, and the lease is it |
| `Usage` is required token counts; `UsageUpdate.cost` is `Cost(amount: float, currency: str)` | money arrives, and has to be converted honestly |

## The idea underneath

A child agent asking to `write_text_file` or `create_terminal` is **asking to do something our
effect vocabulary already has words for**. So the bridge does not answer those questions itself: it
turns each into an `EffectProfile` and asks the governance port, exactly as the runtime does for a
step of its own.

ACP's `ToolCallKind` — `read · edit · delete · move · search · execute · think · fetch ·
switch_mode · other` — maps onto the six fields, and anything unmapped or absent is `ASSUME_WORST`.
That is the MCP rule from Phase 1 again: **derive what is declared, assume the worst for what is
not.**

## Scope

### In
- `packages/adapters/acp` — an ACP agent as a `ComponentPort`, **resident for the session**
- The fourteen-method client surface, with the governable ones routed through governance
- `ToolCallKind` → `EffectProfile`, worst-case where absent
- `Allow` / `Ask` / `Refuse` mapped onto ACP's two nos, deliberately
- The bridge's own wall clock, bounded by the lease
- `Usage` and `Cost` translated, with the rounding decided rather than silently done

### Out
- The RecordingServer — our registry offered *to* the child (Phase 5)
- Installing Codex or Claude Code, which is the owner's to do

## Deliverables

| # | Deliverable | Verification |
|---|---|---|
| 1 | `AcpAgent` as a `ComponentPort`, resident across steps | `uv run pytest tests/adapters/acp` |
| 2 | Every governable client method judged, not answered blind | one test per method |
| 3 | `ToolCallKind` → effects, worst-case where absent | `test_kinds.py` |
| 4 | `Refuse` sent as the agent's own rejection option when offered | measured over the pipe |
| 5 | A looping agent stopped by the bridge's clock | measured, with elapsed |
| 6 | Usage and cost translated; sub-cent amounts not lost | `test_usage.py` |
| 7 | The contract suite | `tests/adapters/contract` |

## Acceptance criteria

- A real ACP agent, over a real stdio pipe, is invoked as a component and its answer is an `Observation`.
- A child asking to write a file is **judged** — allowed under a writing mode, refused under a reading one — and the refusal reaches the child in its own vocabulary.
- A child that loops on refusals is stopped by the bridge, and the stop is **measured**, not asserted.
- Two hundred calls of `0.004 USD` come out as `80` cents, not `0` — sub-cent amounts survive.
- A currency the bridge was not configured for yields `cost_cents = None`, never a guessed conversion.
