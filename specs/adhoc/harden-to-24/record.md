---
type: Ad-hoc Record
---

# Ad-hoc Work Record: harden-to-24

> **Type**: hardening round — everything open up to Phase 24, and a visual host
> **Created**: 2026-09-11
> **Branch**: `harden-to-24`
> **Backlog**: BUG-020 (P1), BUG-019 (row), Codex signed-in measurement; ENH-002/003 stay deferred
> **Status**: in progress

The owner's directive: no new phase; resolve everything open up to Phase 24 that a host like
Intent Studio needs, make Codex work (the owner signs in), and add a host with a page — the
conversation, the agent's steps and reasoning as they happen, its acts in the sandbox and on
files, and an Allow/Refuse when the policy asks — so all of it can be *seen*.

## What is in the round

1. **BUG-020 — an Ask inside an agent's tool call reaches the host.** Design D57: a component
   may answer `Asked(question, handle)` and the run parks on it exactly as if governance had
   asked; on resume the component is invoked again with the answer and what it `kept` before
   parking, both riding the interrupt payload the checkpointer already holds. The agent adapter
   uses it: a held child that asked becomes the agent's own question; on resume the agent restores
   its transcript, sends the judgement into the held child, and continues its turn. Nested agents
   get it for free — each level uses the same mechanism. Crosses the wire (`keep`, `resumed`).
2. **Codex** — signed-in shapes measured on the owner's login; `codex.toml` fully measured; the
   coder and the host run on it.
3. **BUG-019's row** closed (fixed in v0.17.0).
4. **A visual host** — `examples/studio/`: the wire's own HTTP server plus a page.
5. ENH-002 (a TLS broker) and ENH-003 (a second protocol adapter) are device-world and not
   buildable here; they stay deferred and say so.

## Current Behavior (BUG-020, measured)

An agent's tool call is a child run (D51). When the policy answers `Ask` for it, the child parks,
`carry_out` sees no `observed` for the call, and the model is told *"that step did not run"* — the
scripted worker went on to `propose` and `done` claiming it had written a file it never wrote,
and the run ended `completed`. The parent run never parks; a host watching for `Asked` at the top
sees nothing to answer; the parked child is released with the run.

## Log

- 2026-09-11 — opened; BUG-020 first.
- 2026-09-11 — **BUG-020 closed** (D57): the runtime lets a component ask for itself; the agent uses it; the wire carries `keep`/`resumed`; BUG-019's row closed.
- 2026-09-12 — **Codex measured signed in**: the sub-type on every item, usage, the override spelling, the pre-permit, the failure shape; `codex.toml` says what is measured and what one thing still is not (a reasoning item). The end-to-end proof through the relay skips on the owner's free-tier quota, which these measurements exhausted; it is a live test now. ENH-005 filed (no strict MCP mode).
- 2026-09-12 — **BUG-021 found and closed** (D58): a CLI's tool call the policy asks about is answered live by the person while the CLI waits; measured with Claude Code. The coder's `full` mode now asks before every write.
- 2026-09-12 — **`examples/studio/`**: the visual host — conversation, the record as agent steps with Allow/Refuse on a live question, the workspace's files. Driven in the browser on the owner's subscription: Claude Code wrote `primes.py` (asked, allowed), ran it (asked, allowed), reported the primes; the file opened in the page. **BUG-022 found and closed** on the first question answered there (the wall-clock carve at a second boundary).
