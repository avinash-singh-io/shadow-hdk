---
type: Phase
phase: 27
name: batteries-and-the-facade
epic: 0016-batteries-and-the-facade
status: in-progress
topics: [batteries, mcp, web-search, facade, harness-toml, budget, optimiser, serve]
deps: [phase-25-the-hosts-controls, phase-26-any-language]
---

# Phase 27 — Batteries and the facade

**Simple by default, deep by choice** (principle 9). Phase 26 left one door in-process
(`a_thread`) and one over the wire (`shadow-hdk serve`), both over a composition a product
still has to know the shape of to change. This phase gives a product **three lines** — a
`harness.toml` it can read, `Harness.load()`, `turn()` — and puts the two tools every agent
product asks for first, **web search and web fetch**, behind the component port as *batteries*:
consumed, never built (principle 5), each with an honest effect profile the shipped modes already
judge.

## What this phase makes true

- A product that wants defaults writes a `harness.toml` and three lines of Python — or none, and
  runs `shadow-hdk serve harness.toml`. Every key in the file maps to a port or a profile
  (an invariant walks the table), so there is nothing the file can say that the ports cannot.
- The facade reaches only public port APIs (an invariant walks its imports), so nothing a product
  does through it is closed to a product that goes deeper.
- `web_search` and `web_fetch` are batteries: a *battery is a file* naming an MCP server (or a
  Python callable), the tools to expose under the harness's names, and their effects — wigolo
  (AGPL-3.0, its own process, never linked) first; `ddgs` the light alternative; a registry with a
  store source, like every registry (D66). Judged by the modes as they are: `reaches` is what the
  profile says and no rule is added.
- The coder and host examples are the facade, not a composition of their own.
- The optimiser port is **specified** — what would be optimised, what the locked evaluator is
  (Rule 11), and what DSPy would sit behind — and not built.

## Out of scope

- Building a search engine, a crawler or a fetcher — consumed.
- DSPy itself — specified behind a port; built when Rule 11's evaluator exists.
- Context engineering (Phase 28) and collaboration (Phase 29).
