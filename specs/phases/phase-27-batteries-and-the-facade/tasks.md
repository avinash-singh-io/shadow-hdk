---
type: Tasks
phase: 27
---

# Tasks — Phase 27

## Group 1 — a battery is a file
- [x] `Battery`, shipped battery files (`wigolo.toml`, `ddgs.toml`), `BatteryRegistry` with sources incl. `store_batteries`; `McpComponents(only=, aliases=, effects=)`; a battery that cannot start is a reported problem — D70; wigolo surveyed live (ten tools, no annotations); 8 + 1 tests; seven mutants killed

## Group 2 — batteries in the composition
- [x] `[tools] batteries` + `dir` in `harness.toml`; `workshop(batteries=)`; `ServeHost` opens them once per process (held by one task each), `battery_listing`, `aclose`; `a_thread(batteries=, batteries_dir=, agent=)`; `batteries/list` on the wire and in the TS client; **live on wigolo** through the studio in read-only: `web_search` found the npm page, `web_fetch` of npmjs.com blocked by bot protection (reported, not hidden), `web_fetch` of the registry JSON succeeded — 0.2.1, AGPL-3.0-only, sources cited, no files written, 3 tool calls · 27¢; wigolo ended with serve. Found: `serve --http` outlived SIGTERM with a page open (uvicorn's graceful wait) — `timeout_graceful_shutdown=2`, held by a test. Five mutants killed

## Group 3 — the facade
- [ ] `Harness.load` / `Harness(...)`; `turn()` yields parts; `[budget]`; the two invariants

## Group 4 — the examples reduced
- [ ] coder and host on the facade; README three lines run for real

## Group 5 — the optimiser port, specified
- [ ] the `optimiser` architecture document — the port, the locked evaluator, what DSPy would sit behind

## Close
- [ ] decisions; index; status/roadmap/changelog/README; version; landed; board
