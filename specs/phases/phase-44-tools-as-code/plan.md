---
type: Plan
status: in-progress
---

# Phase 44 — tools as code, from any language — Plan

```
# Sequential:  Group 0 → Group 1 → Group 2 → Group 3 → Group 4
```

TDD strict (Rule 13): every group opens RED and no task is marked done without a recorded
red → green. The four-zero gate (`ruff check`, `ruff format --check`, `mypy`, `pytest -m 'not live'`)
runs per group on 3.12; Group 1 and the final gate also on 3.14.

## Reference specs

`specs/architecture/wire.md` (the direction of every call; the thread, crossed), `runtime.md`
(the registry, the governed step, posture), `adapters.md` (the environment, the proof), `testing.md`
(contract suites). `docs/for-a-product.md` §7 is the consumer-facing statement this phase changes.

## Group 0 — RED *(sequential, blocks)*

- **Loopback, host-side components on a thread** (`test_a_hosts_tools_cross_on_the_thread_door.py` under `tests/wire/`): a `ThreadHost` double, a host-side `Ports` whose component port is an in-process double answering `components.registrations` / `components.invoke` on the host peer; `thread/start {host_components: true}` → `tools/list` lists the host's tool with `source: "host"`; a turn whose scripted agent calls it → `Observed` carries the host's output, `Invoked.component` is the host's id, `registered_by` starts with `host:`; a host tool declaring an irreversible effect → posture `observed`; the host peer closed mid-thread → the next refresh lists no host tools and an in-flight invoke ends `Failed` naming the host; a new peer's `thread/resume {host_components: true}` restores them; `thread/start` without the flag adds no port.
- **HTTP** (`tests/wire/test_serve.py` gains a case): the same through `serve --http`, the host's replies up by POST.
- **The proof** (`test_the_proof_reads_stdout.py` under `tests/adapters/environment/`): a fake `LocalSandbox` whose `wrap` runs `python -c "import sys; sys.stderr.write(<the script>); sys.exit(1)"` → `writes_confined=True`, `proven` depends only on stdout; the same root proven on the interpreter running the suite.
- **TypeScript RED** (a `test/` directory under `clients/typescript/`): a tool served with `components.serve`, called by a scripted provider through `serve --http` (the existing harness of `smoke.ts`) and through `HarnessClient.spawn` over stdio; `thread.start({ host_components: true })` typed.
- Verify: collection fails on the absent names; each test fails for its stated reason.

**Commit:** `test: Phase 44 RED — tools as code from any language`

## Group 1 — The proof *(sequential)*

- `adapters/environment/local.py::_prove`: `attempt` returns `(returncode, stdout, stderr)`; every marker leg reads **stdout** and requires `returncode == 0`; the outside-write leg keeps `not outside.exists()`; the hint on `CannotEnforce` unchanged.
- Verify: `tests/adapters/environment` green on 3.12 and on 3.14 (the scratch environment built 2026-09-19 or `uv run --python 3.14`); the mutation (read stdout+stderr again) fails the new test.

**Commit:** `fix(environment): the proof reads stdout, not the traceback (BUG-057)`

## Group 2 — The thread door inverts *(sequential)*

- `wire/threads.py`: `_start` and `_resume` read `host_components`; when true, build `RemoteComponents(self._peer, holder)` for this connection and hand it to the host as `peer_components=(port,)`; the `ThreadHost` protocol gains the keyword; `serve/host.py::open`/`resume` append it to `workshop()`'s components before `Thread.open`/`resume` (the facade's public surface unchanged — the keyword is the wire's, documented as such).
- `wire/remote.py::RemoteComponents`: `registered_by = f"host:{session}"`; registrations tagged `source = "host"` where the registry's `Offered.source` is read; an invoke whose peer is closed → `Failed(f"the host that offered {id!r} is gone")`; `registrations()` on a closed peer → empty with the problem named, so the registry's refresh drops them.
- Posture: a host registration's `Provenance.posture` is `observed` unless the host declares the authority boundary (Phase 33's rule as written in `runtime/effects.py`); the effect transaction path is not entered for a remote irreversible act.
- `thread/resume {host_components: true}` from a new peer replaces the previous peer's port on that thread (one host port per thread).
- Parity: `tests/invariants/test_the_wire_is_at_parity.py` — the new parameter named; `ERROR_KINDS` unchanged; protocol 3 unchanged (additive).
- Verify: `uv run pytest -q tests/wire tests/serve tests/invariants tests/runtime` green; mutations — the port not added → 4 fail; host-gone not named → 1 fails.

**Commit:** `feat(wire): the thread door carries the host's components by inversion (ENH-030)`

## Group 3 — The TypeScript surface *(sequential)*

- `transport/stdio.ts` under `clients/typescript/src/`: `HarnessClient.spawn({ command, args, cwd, env })` — a child process over JSON lines (one `LineBuffer` equivalent), the same frame handling as HTTP; `close()` ends the child and its tree; a child that exits ends the client with a typed error.
- `components.ts` under `clients/typescript/src/`: `tool(id, { description, effects, input }, handler)` → a `Registration` (generated type) with an `Interface` from the JSON-schema `input`; `client.components.serve(tools)` installs the `onRequest` dispatch for `components.registrations` and `components.invoke`, wrapping a thrown error as `{ kind: "failed", reason }` and a handler's `Refused` as `{ kind: "refused" }`.
- `thread.start({ host_components: true, ... })`, `thread.resume(id, { host_components: true })` typed.
- `smoke.ts`: a host tool through HTTP and through stdio; `npm test` drives both against a real `serve`; the Python side's `tests/serve/test_the_typescript_client_talks_to_serve.py` gains the host-tool case.
- README: the sidecar section — the configurable command, the documented default (`uvx --from shadow-hdk==<version> shadow-hdk serve --stdio`, needs `uv`), and the sentence that the pinned binary is Epic 0010 Phase 42's.
- Verify: `npm run generate && npm run check && npm run build && npm test`; the Python serve tests green.

**Commit:** `feat(typescript): tools as code — the host-side ComponentPort and the stdio sidecar (ENH-031)`

## Group 4 — Docs, release *(sequential, last)*

- `0.32.md` under `docs/migrations/`; `docs/packages/wire.md`; `docs/consuming.md` (the four doors: the thread door now takes a host's components from any language); `docs/for-a-product.md` §7 rewritten; `clients/typescript/README.md`.
- Backlog: ENH-030, ENH-031 (amended: the pin is P42's), BUG-057 closed. Epic 0009: the amendment recorded under *Amendments*.
- Version 0.32.0, `tests/test_versions.py` `EXPECTED`, `uv lock`, changelog, status row. `/sync-docs` for the architecture docs (wire.md: the thread, crossed).
- Verify: the four-zero gate on 3.12 and 3.14; `npm run generate && npm run check && npm run build && npm test`; `momentum okf check .`; the fresh-install smoke of the 0.32.0 wheel; then `/complete-phase` and STOP at the merge/release gate.

**Commits:** `docs: 0.32 — tools as code, from any language` · `chore(release): 0.32.0`
