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
- [x] `_prove.attempt(script, marker) -> bool`: the marker read from stdout with `returncode == 0`, never stderr; `not outside.exists()` kept; the reason in the docstring
- [x] Verify — 2026-09-19: `tests/adapters/environment` 69 passed on 3.12; on 3.14 the 25 that failed yesterday pass (81 passed) and the whole non-live suite is 1,774 passed with only this phase's own RED (the TS invariants) failing; mutation (stdout+stderr) → 2 fail; BUG-058 found (a test's identity comparison 3.14 no longer honours) and closed inline

## Group 2 — The thread door inverts
- [x] `wire/threads.py` `_start`/`_resume` read `host_components`; `RemoteComponents(peer, holder, session=)` handed to the host as `peer_components` (only when asked); `ThreadHost` protocol + `serve/host.py::_handed` append it to `workshop()`'s components — never Python objects of a product's
- [x] `RemoteComponents`: declares `source = "host"` (the runtime asks the port, never parses a spelling); the host's registration crosses **untouched** — the `registered_by` stamp was withdrawn in review because `signing_bytes` covers provenance (TD-013); a gone peer is the wire's typed `GONE` code, never its wording: `registrations()` raises naming the host so the registry lists the port unreachable, `invoke` returns `Failed` naming tool and host
- [x] Posture `observed` for a remote irreversible act (the existing `_observed_if_remote_effect`, tested on the thread door); its rewrite of a signed registration is the same class as the withdrawn stamp — TD-013
- [x] One host port per thread; a new connection's `thread/resume {host_components: true}` brings its own tools and the old host's are gone — proven over HTTP with two connections; the connection's id is the transport's own (`RuntimeSide(session=)`, HTTP's real id, `"this"` over a pipe — D77), nothing mints a second
- [x] The parity invariants pass unchanged (the parameter is additive; `ERROR_KINDS` untouched; protocol 3)
- [x] Verify — 2026-09-19: `tests/wire tests/serve tests/invariants tests/runtime` 781 passed with only the two TypeScript invariants RED (the smoke does not compile until G3); mypy 457 files clean; ruff clean; mutations — port never added → 3 fail; gone unnamed → 1 fails; gone never typed → 1 fails

## Group 3 — The TypeScript surface
- [x] The client refactored onto a `Transport` (`transport.ts`: `HttpTransport` carries the SSE session, reattach and silence detection unchanged; the invariants that drive them pass); `node.ts` — `StdioTransport` and `spawnHarness({ command, args, cwd, env })` over JSON lines, `close()` ends stdin then SIGTERM then SIGKILL, an exit fails what is waiting with its reason; exported as `shadow-hdk-client/node` so the browser build never sees `node:child_process`
- [x] `components.ts`: `tool(id, { description, effects, input, output, name, labels }, handler)` → the generated `Registration` (effects in the battery document's vocabulary); `client.components.serve(tools)` installs `components.registrations` / `components.invoke`; a thrown error → `failed`, a thrown `Refusal` → `refused`, an unknown id → `failed` naming it; installed handlers answer before `onRequest`
- [x] `thread.start({ host_components })`; `thread.resume(id, { plan_limits, host_components })` — an options object now (0.31.0 took a bare `PlanLimits`; the migration note says so)
- [x] `host-tools-smoke.ts` over HTTP and over a spawned stdio runtime (`tests/serve/_stdio_runtime_double.py`), driven by `tests/serve/test_a_typescript_host_serves_tools.py` — the Python suite is the runner, as for the README smoke; no separate node test runner was added
- [x] README: *Tools as code* and *The sidecar* — the configurable command, the `uvx` default that needs `uv` today, and the sentence that the pinned binary is Epic 0010 Phase 42's
- [x] Verify — 2026-09-19: `npm run generate && npm run check && npm run build` clean (no `npm test` script exists; the Python suite is the runner); `tests/serve tests/invariants tests/wire` 309 passed — the TS host tool called back over HTTP and over stdio, the README smoke, the client invariants including the silence-reattach over the refactored transport

## Group 4 — Docs, release
- [x] `docs/migrations/0.32.md`; `docs/packages/wire.md`; `docs/consuming.md` (a fifth row: `serve` + your tools as code, any language); `docs/for-a-product.md` §7 rewritten (three code doors, the first from any language); `clients/typescript/README.md` (*Tools as code*, *The sidecar* — done in G3)
- [x] Backlog: ENH-030, ENH-031 (amended — the pin is Epic 0010 P42's), BUG-057 closed; BUG-058 and TD-013 filed on the way; ENH-032's row says its blocker is gone; Epic 0009's amendment recorded (ENH-030/031 ahead of Phase 34)
- [x] Version 0.32.0, `EXPECTED` with its docstring entry, `uv lock`, README's release status and docs link, changelog, status row; `/sync-docs` next
- [x] Verify — 2026-09-19: ruff check + format clean · mypy 457 files clean · **`uv run pytest -q -m 'not live'` 1,784 passed on 3.12 and 1,784 passed on 3.14**, nothing deselected · `npm run generate && npm run check && npm run build` clean, schemas without drift · `momentum okf check .` conformant (202 files) · the 0.32.0 wheel built, installed into a clean venv, imported and answered `initialize` on protocol 3 · `/complete-phase` → STOP at the gate
