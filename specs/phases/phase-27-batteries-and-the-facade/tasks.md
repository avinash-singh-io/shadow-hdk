---
type: Tasks
phase: 27
---

# Tasks — Phase 27

## Group 1 — a battery is a file
- [x] `Battery`, shipped battery files (`wigolo.toml`, `ddgs.toml`), `BatteryRegistry` with sources incl. `store_batteries`; `McpComponents(only=, aliases=, effects=)`; a battery that cannot start is a reported problem — D70; wigolo surveyed live (ten tools, no annotations); 8 + 1 tests; seven mutants killed

## Group 2 — batteries in the composition
- [ ] `[tools] batteries` in `harness.toml`; `workshop(batteries=)`; `ServeHost`/`a_thread` carry them; live: wigolo (scratchpad install) or `ddgs`, recorded honestly

## Group 3 — the facade
- [ ] `Harness.load` / `Harness(...)`; `turn()` yields parts; `[budget]`; the two invariants

## Group 4 — the examples reduced
- [ ] coder and host on the facade; README three lines run for real

## Group 5 — the optimiser port, specified
- [ ] the `optimiser` architecture document — the port, the locked evaluator, what DSPy would sit behind

## Close
- [ ] decisions; index; status/roadmap/changelog/README; version; landed; board
