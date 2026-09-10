---
type: Plan
phase: 4-the-acp-bridge
---

# Phase 4 — plan

```
# Sequential:  Group 0 → Group 1 → Group 2 → Group 3
```

Each group needs the previous one to exist: the effects vocabulary before the client that uses it,
the client before the component that owns it, the component before the end-to-end proof.

## Group 0 — what a child agent is asking for

**Sequential.** Pure translation, no I/O, so it is cheap to get right first.

- `effects_for(kind, *, contained, network)` — `ToolCallKind` → `EffectProfile`
- `read`/`search` read; `edit`/`move` write reversibly; `delete` writes irreversibly; `execute`
  writes irreversibly and carries the deployment's containment; `fetch` reaches; `think` does nothing
- `other`, `None`, and anything unrecognised → `ASSUME_WORST`
- The same for the client methods that are not tool calls: `write_text_file`, `read_text_file`,
  `create_terminal`

**Commit:** `feat(adapters): what a child agent is asking for, in our own vocabulary`

## Group 1 — the client half, which is a governance surface

**Sequential.**

- `_BridgeClient` — all fourteen methods
- Governable ones judged through the governance port before anything happens
- **`Refuse` is sent as the agent's own `reject_once` option when it offered one**, and as
  `DeniedOutcome` when it did not
- **`Ask` is answered as a rejection that says what would have been asked**, because a child holding
  an open request cannot wait for a human on the other side of an `interrupt()` — recorded as a
  limitation with what would lift it
- `session_update` collects usage and cost; nothing is thrown away silently

**Commit:** `feat(adapters): the client half of ACP, judged rather than answered`

## Group 2 — the agent as a component

**Sequential.**

- `AcpAgent(command, args, *, name, effects, at)` — start, stop, async context manager
- **Resident for the session**: one process and one handshake, not one per step
- `invoke(brief)` → `session/prompt` → `Observation`, with `stop_reason` and accumulated usage
- The bridge's clock: `min(configured timeout, the lease's remaining wall seconds)`

**Commit:** `feat(adapters): another agent, driven as a component`

## Group 3 — proof over a real pipe

**Sequential.**

- The spike agent extended to exercise the client surface: it writes a file, asks to run a terminal, loops
- Measured: a write allowed under one mode and refused under another
- Measured: a looping child stopped by the clock, with elapsed
- Measured: 200 × `0.004 USD` → 80 cents
- Records, board, status

**Commit:** `feat: a child agent governed by the same six fields as everything else`
