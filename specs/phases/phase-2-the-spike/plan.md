---
type: Plan
phase: 2-the-spike
---

# Phase 2 — plan

```
# Sequential:  Group 0 → Group 1 → Group 2
```

A spike is measurement, so there is no parallelism to buy: each group's question depends on the
previous group's answer.

## Group 0 — read the protocol

**Sequential.** Every field in `agent-client-protocol` bearing on refusal or usage, by name and
type, recorded in `history.md`. No claim survives into the record without a field name behind it.

**Commit:** `docs(spike): what ACP provides for refusal and for usage`

## Group 1 — measure it over a pipe

**Sequential.** A minimal conformant agent and client, talking over real stdio:

- the client **denies** a permission request → what does the turn do
- the client selects a **`reject_once`** option → what does the turn do
- the agent itself **refuses** → what stop reason arrives
- a turn reports **usage** → what reaches the client, and what happens when it does not

Every test under a timeout: the failure mode being probed is a hang, and an assertion cannot catch
one.

**Commit:** `test(spike): a refused tool call over a real ACP pipe`

## Group 2 — answer J1

**Sequential.** The board's J1 row: answered, with the part that remains and the command that would
settle it. `specs/status.md` and the phase records.

**Commit:** `docs(spike): J1 answered for the protocol and the transport; the CLIs remain`
