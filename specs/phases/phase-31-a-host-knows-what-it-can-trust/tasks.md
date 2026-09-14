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
- [x] RED: unknown, evidence, ordering, contradictions and JSON round trips
- [x] Implement/export provider capabilities, environment capabilities, execution requirements, mismatches and total compatibility
- [x] Verify focused kernel tests, schemas and mutations

## Group 1 — Providers tell the measured truth
- [x] RED: absent capability is unknown; malformed/contradictory provider records refuse by path; detection carries capabilities
- [x] Record measured Claude Code, Codex and OpenCode capabilities; cover the API-model seam
- [x] Verify provider library, surface, resolution and public-export tests

## Group 2 — Environments tell the proven truth
- [x] RED: strict read/secret requirements fail against local macOS capabilities; fake matrices cover every axis
- [x] Project `Isolation` into environment capabilities and match stricter requirements without changing existing modes
- [x] Verify environment contract, confinement and live-proof tests available on this machine

## Group 3 — One selection decision on every door
- [x] RED: incompatible requirements refuse before provider/environment open; Python and wire details match
- [x] Wire requirements through `Harness`, `ServeHost` and thread start; expose discovery/compatibility over protocol
- [x] Regenerate JSON Schemas and TypeScript types; bump the wire protocol for the new meaning
- [x] Verify serve, wire, generated-client and parity suites

## Group 4 — Evidence, docs and epic checkpoint
- [/] Publish the capability matrix and 0.29.1 migration note; record known unknowns without overstating confinement
- [ ] Run ruff check, format check, mypy strict, full pytest, document invariants, schema drift and benchmark
- [ ] Append phase evidence/history, mark Phase 31 complete, and derive Phases 32 and 33 without releasing
