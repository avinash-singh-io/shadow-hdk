---
type: Tasks
status: in-progress
epic: production-boundary
---
# Phase 31 — A host knows what it can trust — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12).
> **TDD strict:** no task may be marked `[x]` without a recorded red→green.
## Group 0 — The capability algebra *(blocks)*
- [ ] RED: unknown, evidence, ordering, contradictions and JSON round trips
- [ ] Implement/export provider capabilities, environment capabilities, execution requirements, mismatches and total compatibility
- [ ] Verify focused kernel tests, schemas and mutations

## Group 1 — Providers tell the measured truth
- [ ] RED: absent capability is unknown; malformed/contradictory provider records refuse by path; detection carries capabilities
- [ ] Record measured Claude Code, Codex and OpenCode capabilities; cover the API-model seam
- [ ] Verify provider library, surface, resolution and public-export tests

## Group 2 — Environments tell the proven truth
- [ ] RED: strict read/secret requirements fail against local macOS capabilities; fake matrices cover every axis
- [ ] Project `Isolation` into environment capabilities and match stricter requirements without changing existing modes
- [ ] Verify environment contract, confinement and live-proof tests available on this machine

## Group 3 — One selection decision on every door
- [ ] RED: incompatible requirements refuse before provider/environment open; Python and wire details match
- [ ] Wire requirements through `Harness`, `ServeHost` and thread start; expose discovery/compatibility over protocol
- [ ] Regenerate JSON Schemas and TypeScript types; bump the wire protocol for the new meaning
- [ ] Verify serve, wire, generated-client and parity suites

## Group 4 — Evidence, docs and epic checkpoint
- [ ] Publish the capability matrix and 0.29.1 migration note; record known unknowns without overstating confinement
- [ ] Run ruff check, format check, mypy strict, full pytest, document invariants, schema drift and benchmark
- [ ] Append phase evidence/history, mark Phase 31 complete, and derive Phases 32 and 33 without releasing
