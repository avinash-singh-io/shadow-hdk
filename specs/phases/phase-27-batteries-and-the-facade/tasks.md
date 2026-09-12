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
- [x] `Harness.load` / `Harness(...)`; `turn()` yields parts in order, the record last; `[budget]` → `Lease`; `governance=`/`sink=`/`observer=`/`agent=` one step deeper; the two invariants (`test_the_facade_reaches_only_public_apis`, `test_every_harness_toml_key_maps_to_a_port_or_a_profile`) — D71; five tests + six; four mutants against the invariants killed

## Group 4 — the examples reduced
- [x] the coder on the facade (its own `thread` module gone); the host example kept as the deep demonstration (D71); README `harness.toml` + three lines, run for real by a test (a wrong line measured to fail it)

## Group 5 — the optimiser port, specified
- [x] `specs/architecture/optimiser.md` — programs are documents with slots; `improve(program, evaluator, budget) → Improved` as a proposal through the sink; the evaluator locked first (Rule 11) over the recorded model port; DSPy mapped, a `HillClimb` for the contract suite; not built (D72)

## Close
- [ ] decisions; index; status/roadmap/changelog/README; version; landed; board
