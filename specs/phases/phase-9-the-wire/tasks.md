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

- [x] method names, envelope, `initialize` refusing a version mismatch and naming **both**
      versions, because a mismatch is somebody's deployment problem
- [x] four inverted ports — judge, complete, invoke, propose. The **clock and observer do not
      invert**: a clock round-trip per event stamp buys nothing, and the observer already *is*
      the event stream
- [x] the loopback, carrying **JSON text** — a loopback passing live objects would prove the
      plumbing and nothing about the boundary
- [x] RED: each direction, a refused `initialize`, a component the host does not have, and a
      port that raises
- [x] **D21**: a component executes on the *host*, so `current_run()` was `None` and every idiom
      built on it broke — the host now binds a `WireRunContext`
- [~] the in-process suite through the loopback is **not yet the literal thing wire.md asks for**.
      `drive()` has `run()`'s signature so a test moves over by one word, and a representative set
      is proven both ways — but switching all 417 through the wire needs a conftest hook and a
      second pytest pass, and two idioms would have to cross first (`children`, `visible`). Group 4
      or its own group; the mechanism is named so nobody has to rediscover it
- [x] Gate

## Group 2 — `--stdio`

- [x] the protocol over stdin/stdout, newline-delimited
- [x] RED: a real child process drives a composition end to end; the host's policy refuses across
      the pipe; a proposal from a component the host runs lands on the child's record; the child is
      proven a genuinely separate process; a dead peer raises rather than hanging; `--stdio` is a
      mode rather than a default
- [x] Gate

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
