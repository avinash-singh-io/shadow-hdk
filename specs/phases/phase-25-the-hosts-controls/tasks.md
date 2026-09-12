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
- [x] `ThreadStore` port; sqlite and in-memory adapters
- [x] `Thread`: a turn is a run (D62); resume, fork, rollback, list, archive — `steer`/`interrupt` in group 3 with activity
- [x] the provider session and the registry socket held for the thread's lifetime; registry name is the host's
- [x] the coder example's former `session` module gone; coder and studio on `Thread`

## Group 3 — Activity
- [x] survey recorded (LangGraph stream modes)
- [x] `Activity` kernel type; `RunContext.activity`; bounded drop-oldest; never checkpointed
- [x] jsonl deltas from `--include-partial-messages`; the leash's output; `steer`/`interrupt` on the session and the thread (ACP and LangChain chunks: their transports already stream to the caller; wiring them to activity is a one-line follow-up when a host asks)

## Group 4 — Modes
- [x] `Behaviour`, `Mode` as data; `AgentPort.open(behaviour=)`
- [x] provider TOML `behaviour_args`; an unmapped field is reported
- [x] `ModeRegistry` with shipped defaults named as the environment's modes; `set_mode`/`set_option`; `ModeChanged` on the record (modes authored from files: group 6, with the store)

## Group 5 — Approvals and input
- [x] `approve_and_add_rule` → `ActRule` through the sink → `ActRules` (a run handle) → governance after *ask*, live; both answer paths
- [x] `ask_person` → `InputRequested`, answered with text through the handle; over the wire

## Group 6 — the Store
- [x] `Store` port; in-memory and sqlite under one contract; a source of modes, rules, skills, components (`Switched`), providers; read at every judgement / refresh; modes from files too
- [x] the invariant: every registry has a store source (`test_every_registry_has_a_store_source.py`)

## Group 7 — the studio
- [x] collapsed item runs ("Ran N commands, used M tools ›", expandable, thoughts break runs); deltas; the mode selector live; InputRequest item; approve-and-add-rule; the admin surface
- [x] live turns measured: wc.py — 6 tool calls in three folded runs between six thoughts, 44¢; the duplicate final thought found and fixed at the source (record once)

## Close
- [x] D61–D66; index; status/roadmap/changelog/README; 0.22.0; landed; board
