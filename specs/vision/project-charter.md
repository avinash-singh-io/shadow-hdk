---
type: Vision
---

# Project Charter

> **Product**: Shadow (current repository/distribution: `shadow-hdk`)
> **Created**: 2026-09-10

> **2026-09-21 target:** [native architecture](../architecture/native-foundation.md), including
> both discussion diagrams; [Epic 0010](../epics/0010-cross-platform.md), D142–D152. The current
> engine is still Python/LangGraph; native implementation and repository rename have not occurred.

## Problem Statement

Agent integrations often couple their loop to a product — its schema, its idea of a tool, its
notion of "done". Intent Studio's own loop did the same, and the cost was a runtime that could not be
replaced, could not be shaped per situation, and could not be used by anyone else. Teams that need a
governed agent — one that can be narrowed, watched, replayed and trusted with effects on the world —
have to build the governance themselves, every time, inside the loop.

## Solution

**Shadow** is the umbrella framework for building and running agents, workflows and custom
harnesses. Its development kit contains contracts, primitives, components, patterns, runtime,
governance, persistence ports and adapters. Ready-made reference assemblies use those public
parts. A user may run the defaults, configure them, compose different pieces, extend them or
replace ports without adopting a second execution engine. HDK describes the capability rather
than a separate product identity.

The runtime executes a composition over an open set of components under host-owned governance and
hands the record and live activity to whoever is listening. It governs *effects*, never component
names, so the set is open while the proof that a mode only narrows stays finite. A person or agent
may author a workflow as data; the same composition grammar represents deterministic workflows,
model-assisted workflows, agent-owned loops and hybrids. Today LangGraph executes the compiled
graph; the target shared executor is Rust. Shadow judges every step and keeps authority, budgets,
consent and irreversible effects under the host. Patterns, modes, components, providers, skills and adapters are data or plug-ins; the runtime
does not change when they do.

The founding design is `intent-ecosystem/vision/09-the-agentic-system.md`. This repository's
numbered decisions and native-foundation amendment govern the new implementation direction;
historical context does not silently override an approved architectural revision.

## Stakeholders

| Role | Name / Team | Responsibility |
|------|-------------|----------------|
| Owner | Avinash Kumar Singh | Final decisions; landings; licence |
| First user | Intent Studio | Exercises the public HDK contracts as a cloud-linked local host; exposes generic gaps without donating product concepts to the kernel |
| Users | Any system that runs Shadow Harness or implements/replaces the HDK ports | From a ready-made agent through a deterministic workflow to dynamic multi-agent work |

## Scope

### In
- The kernel: types, the effect vocabulary and its order, the composition grammar, observations, leases, events, the ports, JSON Schema contracts
- The runtime: compile a composition to a graph, run it under governance and leases, emit events, propose to the sink, carve children
- The agent as a component, and patterns as data — `single` first, the rest as they are needed
- Adapters, each small and replaceable: models (one adapter over LangChain's integrations, HuggingFace included), components (MCP, Python callables, CLIs, HTTP, other agents over ACP), modes and effect rules, sandboxes, sinks, observers, the wire (`serve`, `--stdio`)
- The workspace and code: the agent writes files, pages and code; a sandbox component runs code where the deployment allows it
- Any environment reachable through a component adapter — including devices: sensors, actuators, robots, warehouses (a later epic, *the environment*)
- The libraries 09 §9 names, extracted from the product as they are touched
- Progressive construction artifacts: primitives, components, patterns, blueprints, presets and a
  first-party reference harness, all reducible to the same public contracts
- Generic persistence and recovery contracts, reference stores, and an append-only execution
  journal; the product chooses and operates its durable backend
- Boundary adapters for open tool, peer, UI, event, telemetry, identity and packaging standards

### Out
- Any product concept: cloud job, claim, intent, subscription, tenant-specific policy schema,
  product activity vocabulary or domain projection
- Product databases, hosted control planes and application UI. Shadow may ship generic UI protocol
  adapters and reusable reference components, but the host owns rendering, vocabulary and state
- A second implementation language (contracts are language-neutral; the runtime is Python)
- Rebuilding what LangGraph already does
- Rebuilding provider loops, sandboxes, schedulers, browsers, memories or protocol stacks that can
  be consumed behind a port

## Success

The bare-harness test (`tests/test_bare_harness.py`) passes with zero product code; the ready-made
Shadow Harness is built only from public HDK contracts; and every row of
[`success-criteria.md`](success-criteria.md) is met at its phase.
