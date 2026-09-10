---
type: Tasks
phase: 9-the-wire
---

# Phase 9 — tasks

## Group 0 — what crosses (D19, D20)

- [ ] `RunState.observations` holds JSON; the runtime loads at its edge
- [ ] RED: a parked-and-resumed run under `LANGGRAPH_STRICT_MSGPACK=true` carries no unregistered type
- [ ] RED: observations still arrive as observations on the event stream
- [ ] `Spent(step, usage)` — the eleventh kind — where the meter is charged
- [ ] RED: `Spent` reaches an observer with a model call's tokens
- [ ] RED: a step that cost nothing emits no `Spent`
- [ ] every package to the next minor (D9); `test_versions.py`; a *Pins* row
- [ ] Gate

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
