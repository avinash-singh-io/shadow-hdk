---
type: Plan
phase: 25
---

# Plan — Phase 25

## Group 1 — the terminology, one contract change (0.21.0)

- Kernel events: `Reasoned` → `Reasoning` (kind `reasoning`), `Spent` → `Usage` (kind `usage`),
  `Asked` → `ApprovalRequested` (kind `approval_requested`, component + inputs kept from D59);
  a new `InputRequested` (kind `input_requested`). Observations: `Asked` → `ApprovalRequest`;
  a new `InputRequest`.
- Runtime projection `Step` → `Item` (`items()`, `run_items()`, `as_json`), with a turn's items
  nested under it. `RunContext.reasoned` → `reasoning`; `Questions` → `Approvals` with
  `ApprovalAnswer(approve | deny | approve_and_add_rule)`.
- Schemas republished; the wire's constants renamed; every package 0.21.0; the invariants that
  walk event kinds updated; `tests/test_versions.py` says why.

## Group 2 — Thread and Turn

- `ThreadStore` port: `create`, `get`, `list`, `fork`, `rollback(to_turn)`, `archive`; sqlite and
  in-memory adapters. A thread record: id, root, mode id, provider, created, turns (id, prompt,
  run step id, at).
- `Thread` in `shadow_hdk.runtime.thread`: holds a provider session across steps; `turn(text)`
  runs one **step** of the thread's run and streams its items; `steer(text)`, `interrupt()`;
  `resume`, `fork`, `rollback`. The registry socket served for the thread's lifetime. The
  registry's name is the host's (`name=`, default `"tools"`).
- the coder example's former `session` module deleted; the coder and the studio use `Thread`.

## Group 3 — Activity

- Survey LangGraph's stream modes (`messages`, `custom`, `updates`) before deciding; record it.
- Kernel `Activity(run_id, step, kind, text, at)`; runtime `RunContext.activity(kind, text)` into a
  bounded, drop-oldest queue read by `run(..., activity=)` or the observer's `on_activity`.
- jsonl: `--include-partial-messages` → `thinking`/`text` deltas; ACP: chunks; LangChain:
  `ModelChunk`; leash: `output` at an interval while a command runs.

## Group 4 — Modes = policy + behaviour + presentation

- Kernel `Behaviour(system, append_system, model, effort, temperature, tools_offered)`;
  `Mode(id, name, description, policy, behaviour)`; `AgentPort.open(..., behaviour=)`.
- Provider TOML: `behaviour_args` mapping fields to flags; a field the provider lacks is reported
  on the record (`Refused`? no — an `Unmapped` note in the `Started` lease? decide: a warning
  observation on the turn) and never dropped silently.
- `ModeRegistry` (shipped `looking`/`confined`/`open` from the environment's mode — moved out of
  the example; files `modes/*.toml|*.md`; store). `Thread.set_mode(id)` / `set_option(k, v)` →
  the run's context at the next step; `ModeChanged` event? — survey ACP (`current_mode_update`)
  and decide the name; record it.

## Group 5 — Approvals and input

- `Approvals` handle: `next()`, `answer(handle, ApprovalAnswer)`; `approve_and_add_rule` proposes a
  `Rule` through the sink and the `RuleRegistry` (live) feeds `ModeGovernance`'s ask line.
- `ask_person` component (offered where the host allows; `writes: {record}`): `InputRequested` on
  the record, answered with text through the same handle.

## Group 6 — the Store

- `Store` port: `put/get/delete/list` per collection + `changed()` notification; sqlite adapter.
- Every registry (modes, behaviours, rules, skills, components-on, providers) gains a store
  source and is refreshed at step boundaries; the invariant walks them.

## Group 7 — the studio

- Collapsed item runs, streamed deltas, a mode selector, an InputRequest item, "approve and don't
  ask again". Consumes only the harness. One or two live turns.

## Close

- D61–D6n in history; index; status, roadmap, changelog, README; land; board with a Pins row.
