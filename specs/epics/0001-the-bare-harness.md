---
type: Epic
id: "0001"
slug: the-bare-harness
status: planned
owner: Avinash
started: "2026-09-09T22:35:14.744Z"
phases: [phase-0-the-runtime, phase-1-real-adapters, phase-2-the-spike]
policy_release: per-phase
policy_push: per-phase
policy_tdd: strict
---

# Epic 0001 — the-bare-harness

## Objective

A composition runs against an MCP server, an Ollama model and a sub-agent, governed by allow-all, written to stdout, with zero product code.

## Decisions

> Settled once; never re-asked. Per-phase specs are derived from this table.
> The full reasoning, and what would overturn each, is in
> [`specs/architecture/decisions.md`](../architecture/decisions.md).

| # | Decision | Rationale |
|---|---|---|
| D1 | The agent loop is a **component**, not a second entry point; `run(composition, ports)` is the only way in | One mechanism, and it is what makes patterns data rather than code paths |
| D2 | **Spawning is ambient** — a `run()` inside a step finds its parent through a contextvar, carves its lease, forwards its events | No label branch in the runtime; identical in-process and behind the wire |
| D3 | The model's **meta-tools belong to the pattern** (`compose`, `propose`, `done`, later `spawn`/`send`/`release`/`describe`) | How one product gets a deterministic ReAct agent and another a dynamic orchestrator from the same code |
| D4 | `Ports` and `RunOptions` are **runtime** types; the kernel defines only the port protocols | The kernel stays a vocabulary, not a wiring convention |
| D5 | **Ask and Await are `interrupt()`**; `thread_id = run_id`; resume with `Command(resume=…)` | Nothing LangGraph already does is rebuilt |
| D6 | Events go **two ways at once** — `run()` yields them and the observer port is fed from a queue on its own task | Embeddable and hostable with one API; the observer stays off the critical path |
| D7 | A **component** raising is a `Failed` observation; a **port** raising ends the run `failed`; no exception escapes `run()` | A component is untrusted and arrives from anywhere; a broken host cannot be reasoned past |
| D8 | **Test doubles ship** in `shadow_hdk.runtime.testing`; the tiny real adapters ship as `adapters/basic`, including `callable` | A host's suite must run the harness for $0; `callable` is how a product registers its own tools |
| D9 | **SemVer**; every package 0.1.0 at Phase 0's end; `v0.1.0` tagged at Phase 9; pre-1.0 a contract change is a minor bump **plus a row on the board** under *Pins* | The join is the only place two lanes can break each other |
| D10 | **LangGraph `>=1.2,<2`**, Python `>=3.12` — the product's major line | One framework version across the R3 join |
| D11 | **Latency is a budget with a benchmark**: ≤ 1 ms p50 runtime overhead per step; 100 sequential < 100 ms; 50-way fan-out < 50 ms, in CI | Governance in-process, no per-step serialisation, compiled-graph cache, observer off the critical path, opt-in checkpointing |
| D12 | **LangGraph executes; we compile and govern.** No hand-written composition interpreter; no agent framework that imposes a shape | The compiler is a few hundred lines; execution, concurrency, checkpointing, interrupts are the engine's |
| D13 | **Tools scale by scoping**: computed visibility, patterns, sub-agent partitioning, catalogue compaction | One flat registry; the harness's job is to make scoping free |

## Completion criteria

> Checkable. "It works" is not a criterion.

- [ ] `uv run pytest tests/test_bare_harness.py` passes **with the `xfail` marker removed**, driving an MCP server, an Ollama model and a sub-agent, governed by allow-all, written to stdout
- [ ] `uv run pytest tests/invariants` reports 0 violations: no product import, the kernel is pure, the runtime imports no adapter, no adapter imports another
- [ ] Two runs of the same composition with the scripted model and the fixed clock produce **JSON-identical** event streams
- [ ] `tests/runtime/test_benchmark.py` reports ≤ 1 ms p50 per-step overhead; 100 sequential steps < 100 ms; 50-way fan-out < 50 ms
- [ ] `uv run mypy` (strict) is clean; `uv run ruff check` and `ruff format --check` are clean
- [ ] Line coverage on `packages/runtime` ≥ 90 %
- [ ] Every package — kernel, runtime, adapters-basic, adapters-agent, adapters-langchain, adapters-mcp, adapters-modes — is at **0.1.0**
- [ ] `examples/bare.py` output is committed as phase evidence
- [ ] **J1 is answered on `intent-ecosystem/lanes/board.md`** with evidence: does a CLI whose tool call is refused end its turn cleanly, and does ACP report token usage
- [ ] Every adapter written in this epic subclasses and passes its port's contract suite

## Non-goals

Explicitly out of this epic, and each has its own phase later: ACP and the RecordingServer (4, 5);
the wire (9); effect rules and mode *files* checked in CI (10); contained sandboxes (11); derivation
(12); anything durable beyond `InMemorySaver`.

## Amendments

> Operator changes made during the run land here, newest last, and become
> inputs to the derivation of every not-yet-started phase.

_(none yet)_
