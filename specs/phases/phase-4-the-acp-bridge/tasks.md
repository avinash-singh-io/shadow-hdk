---
type: Tasks
phase: 4-the-acp-bridge
---

# Phase 4 — tasks

## Group 0 — what a child agent is asking for

- [ ] `packages/adapters/acp/pyproject.toml`, depending on `agent-client-protocol`
- [ ] `effects_for(kind, *, contained, network)` covering all ten `ToolCallKind` values
- [ ] `read`, `search` → reads only; `think` → `NOTHING`
- [ ] `edit`, `move` → writes, reversible; `delete` → writes, **not** reversible
- [ ] `execute` → writes, not reversible, `contained` from the deployment, `reaches` per Phase 3's rule
- [ ] `fetch` → reaches
- [ ] `other`, `None`, unknown → `ASSUME_WORST`
- [ ] profiles for `write_text_file`, `read_text_file`, `create_terminal`
- [ ] RED: one test per kind, and one that an unrecognised kind is the worst case
- [ ] Gate

## Group 1 — the client half

- [ ] `_BridgeClient` with all fourteen methods
- [ ] `request_permission` — judge the tool call's effects; never answer blind
- [ ] **`Refuse` → the agent's own `reject_once` option when offered, else `DeniedOutcome`**
- [ ] `reject_once` and not `reject_always`: our governance was not asked about permanence
- [ ] **`Ask` → a rejection naming the question**, with the limitation recorded
- [ ] `write_text_file`, `read_text_file` judged, then performed through a workspace root
- [ ] `create_terminal` judged; the follow-ups (`terminal_output`, `wait_for_terminal_exit`, `kill_terminal`, `release_terminal`) not re-judged, because the grant was at creation
- [ ] `create_elicitation`, `complete_elicitation`, `ext_method` → refused by default, and said
- [ ] `session_update` collects `UsageUpdate` including `cost`
- [ ] RED: each governable method allowed under one mode and refused under another
- [ ] Gate

## Group 2 — the agent as a component

- [ ] `AcpAgent(command, args, *, name, effects, workspace, at)` — start / stop / `async with`
- [ ] resident: one process and one `initialize` for the session, not one per step
- [ ] `registrations()` — one component, labelled `agent`
- [ ] `invoke({"brief": …})` → `session/prompt` → `Completed({text, stop_reason, usage, …})`
- [ ] the clock: `min(configured, lease remaining wall)`; a timeout is `Failed`, and the child is killed
- [ ] `Usage` translated; `Cost` accumulated as `Decimal` and converted **once**
- [ ] a currency the bridge was not configured for → `cost_cents = None`, and the currency reported
- [ ] `TestAcpAgentIsAComponentPort(ComponentPortContract)`
- [ ] Gate

## Group 3 — proof over a real pipe

- [ ] the spike agent extended: writes a file, asks for a terminal, loops on refusal
- [ ] measured: a write allowed under a writing mode, refused under a reading one
- [ ] measured: a looping child stopped by the bridge, with elapsed
- [ ] measured: 200 × `0.004 USD` → 80 cents
- [ ] `[~]` what remains: Codex and Claude Code, with the command
- [ ] records, board, status
- [ ] Gate
