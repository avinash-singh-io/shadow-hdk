---
type: Vision
---

# Project Charter

> **Project**: shadow-hdk
> **Created**: 2026-09-10

## Problem Statement

Every agent framework couples its loop to a product — the product's schema, its idea of a tool, its
notion of "done". Intent Studio's own loop did the same, and the cost was a runtime that could not be
replaced, could not be shaped per situation, and could not be used by anyone else. Teams that need a
governed agent — one that can be narrowed, watched, replayed and trusted with effects on the world —
have to build the governance themselves, every time, inside the loop.

## Solution

A library that runs an agent over an open set of components under a governance policy, and hands
what the agent produces to whoever is listening. It governs *effects*, never names, so the set of
components is open while the proof that a mode only narrows stays finite. The agent authors its own
workflow as data — a composition — which the runtime compiles to a LangGraph graph and executes,
judging every step as it goes. The runtime acts through components and records through the sink: it
has no write path into any host's store. Patterns (what kind of agent), modes (what it may do),
components (what it can reach) and adapters (how things arrive) are all data or plug-ins; the runtime
does not change when they do.

The design is `intent-ecosystem/vision/09-the-agentic-system.md`; this repository is that document
made executable.

## Stakeholders

| Role | Name / Team | Responsibility |
|------|-------------|----------------|
| Owner | Avinash Kumar Singh | Final decisions; landings; licence |
| First user | Intent Studio — lane P (`intent-studio-backend`, `-frontend`) | Joins at R3 through the six ports; drives priority until then |
| Users | Any system that implements six small ports | From one deterministic agent with a few tools to dynamic multi-agent work |

## Scope

### In
- The kernel: types, the effect vocabulary and its order, the composition grammar, observations, leases, events, the ports, JSON Schema contracts
- The runtime: compile a composition to a graph, run it under governance and leases, emit events, propose to the sink, carve children
- The agent as a component, and patterns as data — `single` first, the rest as they are needed
- Adapters, each small and replaceable: models (one adapter over LangChain's integrations, HuggingFace included), components (MCP, Python callables, CLIs, HTTP, other agents over ACP), modes and effect rules, sandboxes, sinks, observers, the wire (`serve`, `--stdio`)
- The workspace and code: the agent writes files, pages and code; a sandbox component runs code where the deployment allows it
- Any environment reachable through a component adapter — including devices: sensors, actuators, robots, warehouses (a later epic, *the environment*)
- The libraries 09 §9 names, extracted from the product as they are touched

### Out
- Any product concept: record, claim, intent, workspace, tenant
- A UI; persistence of anything durable (the sink's job); hosted services
- A second implementation language (contracts are language-neutral; the runtime is Python)
- Rebuilding what LangGraph already does

## Success

The bare-harness test (`tests/test_bare_harness.py`) passes with zero product code, and every row of
[`success-criteria.md`](success-criteria.md) is met at its phase.
