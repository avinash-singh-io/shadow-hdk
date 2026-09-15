---
type: Vision
---

# Success Criteria

> Measurable targets. When all are met, the project has achieved its goals.

## Phase 0 Targets

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| The bare-harness test passes | `xfail` marker removed, green, with stub adapters | `uv run pytest tests/test_bare_harness.py` |
| Zero product imports | 0 violations across `packages/` | `uv run pytest tests/invariants` |
| Layering holds | runtime never imports adapters; adapters never import each other | `tests/invariants/test_stands_alone.py` |
| Contracts round-trip | 100 % of `CONTRACTS` and every union member | `tests/kernel/test_contracts_round_trip.py` |
| Replay is deterministic | two runs, same inputs, JSON-identical event streams | `tests/runtime/test_replay.py` |
| Per-step overhead | ≤ 1 ms p50 on a no-op component under allow-all; 100 sequential steps < 100 ms; 50-way fan-out < 50 ms | `tests/runtime/test_benchmark.py` (reported in CI) |
| Type and lint gates | mypy `--strict` 0 errors; ruff check and format clean | CI |
| Runtime coverage | ≥ 90 % lines on `packages/runtime` | `uv run pytest --cov=shadow_hdk.runtime` |
| Every package at 0.1.0 | kernel, runtime, adapters-agent, adapters-basic | `pyproject.toml` versions |

## Long-Term Targets

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Real components | the demo runs a real MCP server through Ollama (Phase 1) | `examples/bare.py` output committed as evidence |
| Modes for any product | two-mode, granular and full-auto sets expressed as data with the same adapter (Phase 1) | `tests/adapters/modes` |
| The spike answered | J1 on the board with evidence (Phase 2) | `intent-ecosystem/lanes/board.md` |
| The agent writes code and files | a markdown file and a runnable script produced through components; code refused where uncontained (Phase 3) | `tests/adapters/environment` |
| Your subscription answers the turn | Codex or Claude Code driven over ACP; every tool call an observation (Phases 4–5) | `tests/adapters/acp`, `tests/adapters/recording` |
| Every adapter passes its contract suite | 100 % | `tests/adapters/contract` |
| A host drives it over the wire | `serve` and `--stdio` pass the same suite as in-process (Phase 9) | `tests/wire` |
| `v0.1.0` tagged, schemas published | J2 on the board (Phase 9) | `gh release view v0.1.0` |
| The product's R3 replay differ runs on it | lane P reports both engines diffed on the same inputs | the board |
| Streaming | tokens reach the observer as they arrive (Phase 1) | `tests/adapters/langchain` |
| A seventh port can be added without breaking an adapter | the growth rule proven once | the ADR that adds it, and green contract suites |
| A host selects honestly | typed requirements match only measured/proven provider and environment capabilities; unknown never satisfies strict | Phase 31 capability and wire contract suites |
| One durable agent surface | CLI-backed and model-backed agents have the same `Thread` lifecycle and host controls | Phase 32 provider, thread and wire contract suites |
| Authority holds at the act | approval followed by narrowing is refused before execution; a child cannot widen or reuse a grant | Phase 33 authority adversarial suite |
| Effects survive uncertainty | crash-before, crash-after-before-ack, duplicate delivery and unknown reconciliation never cause a blind non-idempotent retry | Phase 33 effect journal and recovery suite |
| Ready-made and composable are one system | Shadow Harness imports only public Shadow HDK contracts and can be materialized through its primitive/component/pattern/blueprint/preset layers | Phase 34 invariants and examples |
| Dynamic plans do not grant authority | a planner-proposed workflow is admitted only within host capability, authority, budget, depth and fan-out bounds | Phase 36 adversarial suite |
| Scheduling is durable and separate from authority | duplicate or missed trigger delivery creates the documented logical runs without granting an effect | Phase 37 scheduler contracts |
| Evolution cannot self-install | every candidate is evaluated against a frozen corpus and needs a versioned human-approved rollout with rollback | Phase 40 evaluator and rollout contracts |
