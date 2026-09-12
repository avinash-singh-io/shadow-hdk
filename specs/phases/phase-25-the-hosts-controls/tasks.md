---
type: Tasks
phase: 25
---

# Tasks — Phase 25

## Group 1 — the terminology
- [x] kernel events renamed: `reasoning`, `usage`, `approval_requested`; `input_requested` added
- [x] observations: `ApprovalRequest`, `InputRequest`
- [x] projection `Item`; `Approvals` handle with `ApprovalAnswer`
- [x] schemas republished; wire constants; invariants; 0.21.0 everywhere; `test_versions.py` says why

## Group 2 — Thread and Turn
- [ ] `ThreadStore` port; sqlite and in-memory adapters
- [ ] `Thread`: `turn()` is a step; `steer`, `interrupt`; resume, fork, rollback, list, archive
- [ ] the provider session and the registry socket held for the thread's lifetime; registry name is the host's
- [ ] `examples/coder/session.py` gone; coder and studio on `Thread`

## Group 3 — Activity
- [ ] survey recorded (LangGraph stream modes)
- [ ] `Activity` kernel type; `RunContext.activity`; bounded drop-oldest; never checkpointed
- [ ] jsonl deltas from `--include-partial-messages`; ACP; LangChain; the leash's output

## Group 4 — Modes
- [ ] `Behaviour`, `Mode` as data; `AgentPort.open(behaviour=)`
- [ ] provider TOML `behaviour_args`; an unmapped field is reported
- [ ] `ModeRegistry` with shipped defaults from the environment's mode; files; `set_mode`/`set_option`; the change on the record

## Group 5 — Approvals and input
- [ ] `approve_and_add_rule` → a rule through the sink → `RuleRegistry` → governance, live
- [ ] `ask_person` → `InputRequested`, answered through the handle

## Group 6 — the Store
- [ ] `Store` port; sqlite adapter; a source of every registry; refreshed at step boundaries
- [ ] the invariant: every registry has a store source

## Group 7 — the studio
- [ ] collapsed item runs; deltas; mode selector; InputRequest item; approve-and-add-rule
- [ ] live turns measured

## Close
- [ ] decisions; index; status/roadmap/changelog/README; landed; board
