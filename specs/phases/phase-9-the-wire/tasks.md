---
type: Tasks
phase: 9-the-wire
---

# Phase 9 — tasks

## Group 0 — what crosses (D19, D20)

- [x] `RunState.observations` holds JSON; the runtime loads at its edge
- [x] **measured**: `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q -W default` reports **zero**
      "Deserializing unregistered type" lines across 406 tests, where before it reported them.
      TD-001 is settled
- [x] RED: observations still arrive as observations on the event stream — the types stay ours,
      only what crosses is plain
- [x] `Spent(step, usage)` — the eleventh kind — where the meter is charged, and only there
- [x] RED: `Spent` reaches an observer with a model call's tokens
- [x] RED: a step that cost nothing emits no `Spent`
- [x] every package to **0.6.0** (D9); `test_versions.py`; a *Pins* row. `Usage` moved to
      `kernel/usage.py` because `ports` already imports `events`, and is re-exported from `ports`
- [x] Gate

## Group 1 — the protocol, and the suite through a loopback

- [ ] method names, envelope, `initialize` with version refusal
- [ ] the five inverted ports
- [ ] the loopback transport
- [ ] RED: each direction, and a refused `initialize`
- [ ] the in-process runtime suite passes through the loopback
- [ ] Gate

## Group 2 — `--stdio`

- [ ] the protocol over stdin/stdout
- [ ] RED: a real child process drives a composition end to end
- [ ] Gate

## Group 3 — `serve`, which listens

- [ ] HTTP for calls, SSE for events; localhost only in tests
- [ ] the run token: short-lived, single-run, carrying scope, principal and lease
- [ ] RED: a client that did not launch it runs and watches; a token scopes one run
- [ ] Gate

## Group 4 — schemas, the version, and the record

- [ ] `all_schemas()` published as files, checked against the code
- [ ] the version prepared for **v0.1.0** — never tagged here
- [ ] records, board, status, and the *Pins* row P2 must read
- [ ] Gate
