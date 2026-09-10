---
type: Tasks
phase: 4-the-acp-bridge
---

# Phase 4 — tasks

## Group 0 — what a child agent is asking for

- [x] `packages/adapters/acp/pyproject.toml`, depending on `agent-client-protocol`
- [x] `effects_for(kind, *, contained, network)` covering all ten `ToolCallKind` values
- [x] `read`, `search` → reads only; `think` → `NOTHING`
- [x] `edit`, `move` → writes, reversible; `delete` → writes, **not** reversible
- [x] `execute` → writes, not reversible, `contained` from the deployment, `reaches` per Phase 3's rule
- [x] `fetch` → reaches
- [x] `other`, `None`, unknown → `ASSUME_WORST`
- [x] profiles for `write_text_file`, `read_text_file`, `create_terminal`
- [x] RED: one test per kind, and one that an unrecognised kind is the worst case
- [x] Gate

## Group 1 — the client half

- [x] `_BridgeClient` with all fourteen methods
- [x] `request_permission` — judge the tool call's effects; never answer blind
- [x] **`Refuse` → the agent's own `reject_once` option when offered, else `DeniedOutcome`**
- [x] `reject_once` and not `reject_always`: our governance was not asked about permanence
- [x] **`Ask` → a rejection naming the question**, with the limitation recorded
- [x] `write_text_file`, `read_text_file` judged, then performed through a workspace root
- [x] `create_terminal` judged; the follow-ups (`terminal_output`, `wait_for_terminal_exit`, `kill_terminal`, `release_terminal`) not re-judged, because the grant was at creation
- [x] `create_elicitation`, `complete_elicitation`, `ext_method` → refused by default, and said
- [x] `session_update` collects `UsageUpdate` including `cost`
- [x] RED: each governable method allowed under one mode and refused under another
- [x] Gate

## Group 2 — the agent as a component

- [x] `AcpAgent(command, args, *, name, effects, workspace, at)` — start / stop / `async with`
- [x] resident: one process and one `initialize` for the session, not one per step
- [x] `registrations()` — one component, labelled `agent`
- [x] `invoke({"brief": …})` → `session/prompt` → `Completed({text, stop_reason, usage, …})`
- [x] the clock: `min(configured, lease remaining wall)`; a timeout is `Failed`, and the child is killed
- [x] `Usage` translated; `Cost` accumulated as `Decimal` and converted **once**
- [x] a currency the bridge was not configured for → `cost_cents = None`, and the currency reported
- [x] `TestAcpAgentIsAComponentPort(ComponentPortContract)`
- [x] Gate

## Group 3 — proof over a real pipe

- [x] the spike agent extended: writes a file, asks for a terminal, loops on refusal
- [x] measured: a write allowed under a writing mode, refused under a reading one
- [x] measured: a looping child stopped by the bridge, with elapsed
- [x] measured: 200 × `0.004 USD` → 80 cents
- [~] **what remains: Codex and Claude Code.** Neither speaks ACP on this machine without a
      global npm install and a paid turn, which this session will not take. `spikes/acp/drive_real.py`
      is the script; the commands are in `specs/phases/phase-2-the-spike/history.md`
- [x] records, board, status
- [x] Gate
