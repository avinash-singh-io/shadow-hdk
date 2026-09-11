---
type: Plan
phase: 23
---

# Plan — Phase 23

## Group 1 — the agent runs over the wire

- `CONTEXT_VISIBLE`: the registry's visible registrations, serialised, crossing back. The catalogue
  an agent builds from them is built host-side from what the runtime says is visible.
- `CONTEXT_FLOOR_MET`, `CONTEXT_SPAWN_OPTIONS`: queries, crossing back.
- `children`: `spawn`, `send`, `release` crossing back. The child run lives in the runtime; the
  component it invokes crosses to the host like any other; the handle and the child's events return
  to the caller. Held children survive a park because the runtime holds them (D37).
- A `single` pattern runs over the loopback wire and emits `Reasoned`; an orchestrator spawns a
  sub-agent over the wire and the child's events land in the host's stream under the parent's step.

## Group 2 — parity as an invariant

- `tests/invariants/test_the_wire_is_at_parity.py`: every public method on `RunContext` is either
  overridden by `WireRunContext` to cross, or named in a table with the reason it does not; every
  kind in the `Event` union is in the wire's published schemas; `Step` is published.

## Group 3 — the socket is authenticated

- `serve_over_socket` mints a token (`secrets.token_urlsafe`) and yields `(port, token)`.
- The relay reads `SHADOW_HDK_REGISTRY_TOKEN` and sends it as the first line; the server reads one line
  before handing the stream to MCP; a mismatch closes the connection and increments a counter.
- The token is never logged, never on an event, never in an `Available`.

## Group 4 — a host, and BUG-019

- a host example under examples: a generic in-process host — its own `GovernancePort` (a policy over effects),
  its own `SinkPort` (an in-memory record with a JSON dump), a LangGraph checkpointer, the
  projection rendered as steps; a provider by key (LangChain) or by subscription (detected), the
  host's choice. Generic: it is "a host", not a product.
- BUG-019: `JsonlSession` and `AcpAgent` register their child with an `atexit` and a signal-safe
  finaliser so the child dies with the process; the example's REPL catches `KeyboardInterrupt`
  around `input()` and closes. A test spawns a session in a subprocess, kills the parent, and
  asserts the child is gone.

## Group 5 — on demand

- a live workflow under .github with `workflow_dispatch`; `make live` / a documented `uv run pytest
  -m live` line in the README.
- Codex: `npm install --prefix $SC @openai/codex`, measure `--version` and the CLI's stream shape;
  update `codex.toml` with what was measured and mark the rest unverified.

## Close

D51–D53; index; status, roadmap, changelog, README, board. Contract change if any → 0.17.0; else
a patch.
