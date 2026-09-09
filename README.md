# shadow-hdk

A generic agentic system: a runtime that runs an agent over a set of components under a governance
policy, and hands what the agent produces to whoever is listening. It has no database, no schema,
no product concepts, no UI. Intent Studio uses it; it never knows Intent Studio exists.

**The design is `intent-ecosystem/vision/09-the-agentic-system.md`.** This repository is that
document made executable, and where the two disagree the code is wrong until an ADR says otherwise.

## The one rule

**Mechanism lives here. Policy and content live in the product.** Every "where does X go" is
answered by asking which of the two X is. Concretely: this repository governs *effects*, never
names — a component declares six fields (`reads · writes · reaches · reversible · contained ·
costs`) and everything downstream is a rule over them.

## The test that defines done

A composition invokes an MCP server, an Ollama model and a sub-agent, governed by allow-all, with
every event written to stdout — using zero lines of any product's code. That is
`tests/test_bare_harness.py`, an expected failure until the runtime lands, and strict: the day it
passes, the marker must come off.

Two invariants run today and fail the build: nothing under `packages/` imports a product, and the
kernel imports no I/O, clock, logging or framework (`tests/invariants/test_stands_alone.py`).

## Layout

```
packages/kernel     shadow-hdk-kernel   pure types, one partial order, six ports   ← R0, here
packages/runtime    shadow-hdk          the loop on LangGraph; compositions → graphs  R3
packages/adapters   shadow-hdk-adapters-<x>   mcp · ollama · openai · acp · allow-all …  R1→
```

One import name, `shadow_hdk`, as a namespace package, so the three ship separately.

## Run it

```bash
uv sync
uv run ruff check && uv run ruff format --check
uv run mypy
uv run pytest
```

## Status

R0 of the harness track (`10-the-roadmap.md` §5). Private until a licence is chosen — that
decision is the owner's, and it is on R0's list because a permissive licence grants rights for
that version irrevocably.
