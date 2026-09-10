---
type: Tasks
phase: 2-the-spike
---

# Phase 2 — tasks

## Group 0 — read the protocol

- [x] `PromptResponse` — every field and type
- [x] `StopReason` — every value a turn can end with
- [x] `RequestPermissionRequest` / `RequestPermissionResponse` — the refusal path both ways
- [x] `PermissionOption.kind` — what a client may offer
- [x] `Usage` — every field, and which are required
- [x] a search of the whole schema for any field mentioning token, usage, cost, spend or credit
- [x] recorded in `history.md` with names and types, no claim from prose alone

## Group 1 — measure it over a pipe

- [x] `spikes/acp/agent.py` — a minimal conformant ACP agent that requests permission before a tool call
- [x] `spikes/acp/drive.py` — a client that answers a chosen way and records what came back
- [x] RED first, each under `asyncio.wait_for`, because the failure being probed is a hang
- [x] measured: permission **denied** → the turn ends, with which stop reason, in what time
- [x] measured: a **`reject_once`** option selected → the turn ends, with which stop reason
- [x] measured: the agent's own **refusal** → `stop_reason`
- [x] measured: usage present → what the client receives; usage absent → what the client receives
- [x] Gate

## Group 2 — answer J1

- [ ] `history.md` — the answer, the numbers, and what is still unmeasured
- [ ] the board's J1 row — answered for protocol and transport, open for the CLIs, with the command
- [ ] `specs/status.md`
- [ ] Gate
