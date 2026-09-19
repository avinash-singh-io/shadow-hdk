---
type: Tasks
status: in-progress
---
# Phase 44 — tools as code, from any language — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12).
> **TDD strict:** no task may be marked `[x]` without a recorded red→green.

## Group 0 — RED *(blocks)*
- [ ] `test_a_hosts_tools_cross_on_the_thread_door.py` under `tests/wire/`: `host_components: true` → `source: "host"` in `tools/list`; a turn's call runs on the host side and `Observed` carries its output; `registered_by` starts `host:`; an irreversible host tool → posture `observed`; host gone → no host tools on refresh, in-flight invoke `Failed` naming the host; a new peer's `thread/resume` restores; no flag → no port
- [x] `tests/wire/test_a_hosts_tools_cross_over_http.py` (its own file rather than a case in `test_serve.py`): the same through `serve --http`, and a second host's `thread/resume` replacing the first's tools
- [x] `tests/adapters/environment/test_the_proof_reads_stdout.py`: a fake box echoing the script to stderr and exiting non-zero → `writes_confined=True`; the 3.13+ echo measured; a source guard
- [x] `clients/typescript/src/host-tools-smoke.ts` + `tests/serve/test_a_typescript_host_serves_tools.py` (+ `tests/serve/_stdio_runtime_double.py`): a tool served from TS, called through `serve --http` and through `HarnessClient.spawn` over a spawned stdio runtime
- [x] Verify RED — 2026-09-19: 8 failed for their stated reasons (the host's tool absent from `tools/list`; `RemoteComponents` takes no `session`; the proof reads `WROTE` from stderr; the smoke not built); `tsc` fails on `tool`/`spawn`; 3 measurement guards pass as they should

## Group 1 — The proof
- [ ] `_prove.attempt` returns `(returncode, stdout, stderr)`; markers read from stdout with `returncode == 0`; `not outside.exists()` kept
- [ ] Verify: `uv run pytest -q tests/adapters/environment` green on 3.12 and 3.14; mutation (stdout+stderr) fails the new test

## Group 2 — The thread door inverts
- [ ] `wire/threads.py` `_start`/`_resume` read `host_components`; `RemoteComponents(peer, holder)` handed to the host as `peer_components`; `ThreadHost` protocol + `serve/host.py` append it to `workshop()`'s components
- [ ] `RemoteComponents`: `registered_by = "host:<session>"`; `source = "host"`; closed peer → `Failed` naming the host on invoke, empty-with-problem on registrations
- [ ] Posture `observed` for a remote irreversible act; no effect transaction entered
- [ ] One host port per thread; a new peer's resume replaces the old
- [ ] Parity table names the parameter; protocol 3 unchanged
- [ ] Verify: `uv run pytest -q tests/wire tests/serve tests/invariants tests/runtime` green; mutations bite (port not added → 4 fail; host-gone unnamed → 1 fails)

## Group 3 — The TypeScript surface
- [ ] stdio transport: `HarnessClient.spawn({ command, args, cwd, env })`, JSON lines, `close()` ends the tree, exit → typed error
- [ ] `tool()` + `components.serve()`: registrations from the generated `Registration` type; `components.invoke` dispatch; thrown → `failed`; `Refused` → `refused`
- [ ] `thread.start({ host_components })`, `thread.resume(id, { host_components })` typed
- [ ] `smoke.ts` over HTTP and stdio; `npm test` against a real `serve`; the Python serve test gains the host-tool case
- [ ] README: the sidecar section — configurable command, documented default, the pinned binary is Epic 0010 P42's
- [ ] Verify: `npm run generate && npm run check && npm run build && npm test`; Python serve tests green

## Group 4 — Docs, release
- [ ] `0.32.md` under `docs/migrations/`; `docs/packages/wire.md`; `docs/consuming.md`; `docs/for-a-product.md` §7; `clients/typescript/README.md`
- [ ] Backlog: ENH-030, ENH-031 (amended), BUG-057 closed; Epic 0009 amendment recorded
- [ ] Version 0.32.0, `EXPECTED`, `uv lock`, changelog, status row; `/sync-docs`
- [ ] Verify: four-zero gate on 3.12 and 3.14 · TS generate/check/build/test · `momentum okf check .` · fresh-install smoke of the 0.32.0 wheel · `/complete-phase` → STOP at the gate
