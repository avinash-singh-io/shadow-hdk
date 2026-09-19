---
type: Phase
status: complete
tags: [wire, components, inversion, typescript, sidecar, stdio, proof, environment]
deps: [phase-36-plan-admission]
---

# Phase 44 — tools as code, from any language

## Goal

A host in any language writes its tools as **code** and the runtime calls them back — on the
**thread door**, where products live — through the inversion the wire has had since D21. Today that
inversion exists only on `run`/`resume`: `HostSide` serves `components.registrations` and
`components.invoke`, `wire/remote.py::RemoteComponents` asks a host for them, and the HTTP transport
already carries callbacks down the SSE stream and replies up by POST. `thread/start` composes from
the serving process alone, so a wire host has no code door for its own tools on the durable thread.
This phase opens it, proves it from TypeScript over HTTP and over a spawned stdio runtime, and fixes
the one line that made the D36 proof misread Python 3.13+ (BUG-057).

Nothing here names a product. Each item is a provider-neutral, language-neutral contract, tested by
the question *would a second, different host use it unchanged?*

**Epic 0009 amendment (forward-only, recorded there):** ENH-030 and ENH-031 — the thread door's
inversion and the TypeScript host-side stub — land here, ahead of Phase 34, which keeps the scaffold,
the bundle and the remaining D119 surfaces.

## Key decisions

| # | decision | why |
|---|---|---|
| P44-1 | **`thread/start` and `thread/resume` take `host_components: true`; the runtime adds a `RemoteComponents` port for the calling peer to that thread's registry**, `registered_by = "host:<session>"`, `source: "host"` in `tools/list`; judged, admitted and recorded exactly as a local port's | the inversion `run` already has, on the door products use; the served composition stays data — the host's code stays on the host's side of the wire (not the withdrawn ENH-022) |
| P44-2 | **A host that goes away takes its tools with it, by name.** The registry's refresh marks the peer's port absent; an in-flight invoke ends `Failed` naming the host; a new connection's `thread/resume {host_components: true}` replaces the old peer's port | a thread outlives a connection; never a silent tool that is not there |
| P44-3 | **A host-side component's irreversible effects carry posture `observed`** unless the host hosts the authority boundary — Phase 33's rule, unchanged | the wire cannot make a remote act `controlled` by wishing |
| P44-4 | **The TypeScript client gains a stdio transport beside HTTP** — `HarnessClient.spawn({ command, args })` starts the runtime as a child speaking JSON lines; `close()` ends it. The command is configurable; the documented default needs `uv` on the machine. **The pinned, no-prerequisite binary is Epic 0010 Phase 42's** and the README says so | the sidecar shape lands now; the artifact lands where it was decided |
| P44-5 | **`client.components.serve([...])` is the host-side `ComponentPort` in TypeScript** — `tool(id, { effects, input, description }, handler)` builds registrations from the published `Registration` schema; `components.invoke` is dispatched to the handler; the result is an `Observation` | the same contract the Python port meets; generated types, not hand-typed |
| P44-6 | **The proof is a wire test through a real `serve`, over HTTP and over stdio**: a scripted provider calls a TypeScript tool, the tool runs in the Node process, the record carries the observation | D119: every surface passes the same contract over the wire |
| P44-7 | **The D36 proof reads its markers from stdout and the exit code, never stderr** | 3.13+ echoes `-c` source in tracebacks; a denied write must never read as a write; mechanism-independent |

## Scope

**In:** ENH-030, ENH-031, BUG-057; the TS README's sidecar section with the honest prerequisite;
`docs/for-a-product.md` §7 rewritten; `0.32.md` under `docs/migrations/`; Epic 0009's amendment; v0.32.0.

**Out:** the pinned binary (Epic 0010 Phase 42); a Go or other-language stub (Phase 34); BUG-056,
ENH-023, ENH-024, ENH-028, ENH-032 (Phase 45, next); ENH-027 (OpenCode); a `components=` of Python
objects on the facades (withdrawn ENH-022).

## Deliverables

| deliverable | verification |
|---|---|
| `thread/start` / `thread/resume {host_components}` → a `RemoteComponents` port per thread; `registered_by`, `source: "host"`; host-gone semantics; posture | `uv run pytest -q tests/wire tests/serve tests/invariants` |
| BUG-057: the proof reads stdout and the exit code | `uv run pytest -q tests/adapters/environment` on 3.12 **and** 3.14 |
| TS: stdio transport, `components.serve`, `tool()`, `thread.start({ host_components })`, generated types, `smoke.ts` over both transports | `cd clients/typescript && npm run generate && npm run check && npm run build && npm test` |
| the wire test through a real `serve`, HTTP and stdio, from the Python suite | `uv run pytest -q tests/serve/test_the_typescript_client_talks_to_serve.py` |
| docs, migration note, backlog closes, the epic amendment, 0.32.0 | four-zero gate on 3.12 and 3.14 · `momentum okf check .` · the fresh-install smoke |

## Acceptance criteria

1. A TypeScript function registered through `components.serve` is invoked by a turn on a served thread, over HTTP **and** over a spawned stdio runtime; the record's `Observed` carries its output; `tools/list` names it with `source: "host"`.
2. The host disconnecting removes its tools from the catalogue by name; an in-flight call ends `Failed` naming the host; a reconnecting host's `thread/resume` restores them.
3. A host-side component declaring an irreversible effect is recorded with posture `observed`.
4. The proof returns `proven=True` on 3.12, 3.13 and 3.14 for one root; a fake box that echoes the script to stderr and exits non-zero yields `writes_confined=True`.
5. Nothing in the served process depends on host code; `Harness` and `ServeHost` take no Python components.
6. v0.32.0 released; the TS README states the sidecar's current prerequisite and points at Epic 0010 for the pinned binary. Protocol stays 3.
