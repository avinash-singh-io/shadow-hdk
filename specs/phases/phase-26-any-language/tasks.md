---
type: Tasks
phase: 26
---

# Tasks — Phase 26

## Group 1 — threads over the wire
- [ ] `ThreadHost` port on the runtime side; `thread/start`, `turn/start` streaming events, items, activity
- [ ] `thread/resume`, `list`, `fork`, `rollback`, `archive`, `set_mode`, `set_option`; `turn/steer`, `turn/interrupt`

## Group 2 — handles over the wire
- [ ] `approvals/pending`, `approvals/answer` (three answers, and text), withdrawn as a notification; `run/cancel`
- [ ] the parity invariant extended to handles and thread operations

## Group 3 — the store over the wire
- [ ] `store/put|get|delete|list|version`; `modes/list`, `rules/list`; a crossed row is live

## Group 4 — serve
- [ ] `shadow-hdk-serve`: the composition moved out of the coder example; `serve harness.toml --stdio|--http`
- [ ] the coder and the studio import the composition from the package

## Group 5 — TypeScript
- [ ] survey recorded; generation from the schemas; a thin client; the drift invariant

## Group 6 — the studio on the wire
- [ ] the studio consumes the wire and nothing local; driven live

## Close
- [ ] decisions; index; status/roadmap/changelog/README; 0.23.0; landed; board
