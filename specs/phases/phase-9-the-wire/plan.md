---
type: Plan
phase: 9-the-wire
---

# Phase 9 — plan

```
# Sequential:  Group 0 → 1 → 2 → 3 → 4
# Group 0 settles what crosses; 1 proves the shape; 2 and 3 are the two transports; 4 releases.
```

## Group 0 — what crosses (D19, D20)

- `RunState.observations` holds **JSON**; the runtime loads observations back at its edge
- `Spent(step, usage)` — the eleventh event kind — emitted where the meter is charged
- Every package to the next minor (D9), and a *Pins* row
- RED: a run parked and resumed under `LANGGRAPH_STRICT_MSGPACK=true` with no unregistered type;
  observations still arrive as observations on the event stream; `Spent` reaches an observer with a
  model call's tokens, and a step that cost nothing emits none

**Commit:** `feat(kernel)!: what crosses a boundary is JSON, and what a step cost is an event`

## Group 1 — the protocol, and the suite through a loopback

- The method names, the envelope, and `initialize` — refusing a version mismatch rather than
  degrading
- The **inverted ports**: `RemoteGovernance`, `RemoteModel`, `RemoteComponents`, `RemoteSink`,
  `RemoteObserver` — each issues a request the host answers
- A **loopback** transport: two in-memory streams, no sockets, so the shape is provable without one
- RED: `run` and `resume` cross host → runtime; each of the five ports crosses runtime → host;
  events stream back; an `initialize` with the wrong version is refused with what it wanted
- **The acceptance test:** the in-process runtime suite passes through the loopback

**Commit:** `feat(wire): the ports invert, and the suite passes both ways`

## Group 2 — `--stdio`

- The same protocol over stdin/stdout, the shape MCP and ACP use
- A real child process, driven end to end — Phase 5's lesson about pipes applies
- RED: a composition run over stdio; a refusal crossing; events arriving in order

**Commit:** `feat(wire): a runtime a child process can drive`

## Group 3 — `serve`, which **listens**

- HTTP for calls, SSE for the event stream — the transport Phase 5 said was missing
- Bound to localhost in every test, never anything else
- RED: a client that did not launch it runs a composition and watches events; a run token scopes one
  run; a second client cannot resume somebody else's

**Commit:** `feat(wire): a runtime you connect to rather than launch`

## Group 4 — schemas, the version, and the record

- `all_schemas()` published as files, and the published set checked against the code
- Every package prepared at a releasable state; the release itself **is the owner's** — prepared
  and said to be ready, never tagged here
- `[~]` anything that cannot be settled without the owner, with the command that would settle it
- tasks, history, status, board — and the *Pins* row P2 has to read

**Commit:** `feat(wire): the schemas a client is generated from`
