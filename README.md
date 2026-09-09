# shadow-hdk

A generic agentic system: a runtime that runs an agent over an open set of components under a
governance policy, and hands what the agent produces to whoever is listening. It has no database, no
schema, no product concepts, no UI. Intent Studio uses it; it never knows Intent Studio exists.

**The design is `intent-ecosystem/vision/09-the-agentic-system.md`.** This repository is that
document made executable, and where the two disagree the code is wrong until an ADR says otherwise.
The low-level design lives in [`specs/architecture/`](specs/architecture/overview.md).

## The four public names

```python
from shadow_hdk.runtime import run, resume, current_run, Ports, RunOptions

async for event in run(composition, ports, options=RunOptions(lease=lease)):
    render(event)
```

`run` compiles a composition to a LangGraph graph, judges **every** step through the governance
port, emits nine kinds of event, hands proposals to the sink, and carves children from the parent's
lease. `current_run()` is how a component proposes, reads what is left of its lease, and spawns.

## The two rules

**Govern effects, not names.** A component declares six fields — `reads · writes · reaches ·
reversible · contained · costs` — and everything downstream is a rule over them, so the registry can
be open while the proof that a mode only narrows stays finite.

**Act through components; record through the sink.** The agent acts on the world through components
whose effects are judged. The runtime has no write path into any host's durable store: what it wants
kept leaves as a proposal, and the host decides.

## What kind of agent

A `Pattern` — data, not a code path:

```python
single = Pattern("single", ROLE, meta_tools=frozenset({"propose", "done"}))
```

`single` offers the model no `compose`, so it cannot change its own shape: a deterministic one-agent
product on the same runtime a dynamic one uses.

## The test that defines done

```bash
uv run pytest tests/test_bare_harness.py
```

A composition runs against a component that arrived from outside, a model and a sub-agent, governed
by allow-all, everything written to stdout — with **zero lines of any product's code**. See
[`examples/bare.py`](examples/bare.py); run it with `uv run python examples/bare.py`.

Four invariants fail the build rather than a review: nothing under `packages/` or `examples/`
imports a product; the kernel imports no I/O, clock, logging or framework; the runtime imports no
adapter; no adapter imports another.

## Layout

```
packages/kernel            shadow-hdk-kernel            pure types, one partial order, six ports
packages/runtime           shadow-hdk                   the loop, on LangGraph
packages/adapters/basic    …-adapters-basic                 allow-all · stdout · clock · callables
packages/adapters/agent    …-adapters-agent                 the model loop as a component; patterns
```

One import name, `shadow_hdk`, as a namespace package, so the four ship separately.

## Run it

```bash
uv sync --all-packages
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
```

## Status

**Phase 0 complete** (`specs/planning/roadmap.md`): the runtime, the agent, the basic adapters, the
bare harness. 150 tests, 96 % line coverage on the runtime, 0.586 ms of overhead per step against a
1 ms budget. Every package at 0.1.0.

Phase 1 next: one `ModelPort` over LangChain's providers (OpenAI-compatible, Anthropic, Ollama,
HuggingFace), the MCP component adapter, and modes as data.

Private and unlicensed. A permissive licence grants rights for that version irrevocably, so the
choice is the owner's and publishing waits on it.
