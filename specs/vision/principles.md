---
type: Vision
---

# Principles

> Guiding decisions throughout the project. When trade-offs arise, these resolve them.

## Core Principles

1. **Govern effects, not names.** A component's name is open; what it does to the world is six ordered fields. A name is never a permission, and a new field is a scope-set or a boolean, never a predicate.
2. **Mechanism here; policy and content in the product.** Every "where does X go" is answered by asking which of the two X is. Modes, constitutions, record shapes and prompts are the product's; the enforcement point, the loop and the adapters are ours.
3. **Act through components; record through the sink.** The agent acts on the world through components whose effects are declared and judged. The runtime has no write path into any host's durable store — what it wants kept leaves as a proposal, and the host decides.
4. **Composition is data.** The agent's plan is a small structure, not code: visible while it runs, changeable mid-flight, replayable for $0, judged one step at a time, and it works on a laptop with no sandbox. One tool call is a composition of one step.
5. **Built on LangGraph, generic above it.** Nothing LangGraph does is rebuilt; nothing LangGraph is leaks above the ports. The contract a host implements names no framework.
6. **The bare-harness test defines "generic".** Zero product imports, enforced by an AST walk in CI. If the demo needs a product import, the decoupling is a claim.
7. **A change nothing can measure is not allowed.** Red test first; assertions mutation-checked; every contract round-trips through JSON in CI; the per-step overhead has a budget and a benchmark.
8. **Grow by adapters and pattern files, never by runtime branches.** A new provider, protocol, pattern, mode set or device is a plug-in or a file. The runtime does not know their names.
