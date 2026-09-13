---
type: Ad-hoc Record
---

# Ad-hoc Work Record: harden-to-24

> **Type**: hardening round — everything open up to Phase 24, and a visual host
> **Created**: 2026-09-11
> **Branch**: `harden-to-24`
> **Backlog**: BUG-020 (P1), BUG-019 (row), Codex signed-in measurement; ENH-002/003 stay deferred
> **Status**: shipped as v0.19.0

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
- 2026-09-12 — closed: D57/D58 on the record, 0.19.0, landed.

## Verification Evidence

Fresh, 2026-09-12, this session, on `main` at `b906f21`.

**The four zeros:**

```
ruff=0
format=0
Success: no issues found in 210 source files
1185 passed, 2 skipped, 12 deselected, 86 warnings in 72.52s (0:01:12)
```

**BUG-020 reproduced first (RED), the agent-level test against the unfixed adapter:**

```
E       AssertionError: the question must be the top run's to answer
E       assert 'id-0001' == 'host'
```

— the `Asked` event was the child run's; the top run never parked. After D57: 6 passed
(park at the top; allow runs the tool and the model hears it; refuse is told; the transcript
survives the park; two levels down; a plan that asks twice parks twice). Seven mutants killed.

**BUG-021 reproduced first (RED), the recording test against the unfixed server:**

```
ImportError: cannot import name 'Questions' from 'shadow_hdk.runtime'
```

then, with the handle in place and the server unfixed, the CLI was told
`the call produced no observation`. After D58: 4 passed. Five mutants killed. **Live, the coder
on the owner's subscription in `full` mode:**

```
? mode 'open' asks before this: it writes more than usual
allow? [y/N]   · write_file
    → Completed(output={'path': 'hello.txt', 'bytes': 6}, kind='completed')
agent › Created `hello.txt` containing `hello`.
```

**BUG-022 reproduced first (RED), with a `FixedClock` straddling a second boundary:**

```
E           ValueError: a child lease cannot exceed its parent's ceiling
1 failed, 1 passed
```

After the clamp: 2 passed; the recording suite 30 passed.

**The studio, in the browser, on the owner's subscription (`full` mode):** Claude Code called
`write_file` → the page showed *? mode 'open' asks before this* with Allow/Refuse → Allow →
`✓ write_file {"path":"primes.py","bytes":364}` and `primes.py` in the files pane → it called
`run_shell` → asked → Allow → `✓ run_shell {"exit_code":0,"stdout":"2\n3\n5\n7\n11\n13\n17\n19\n23\n29\n"}` →
the agent reported the primes; the file opened in the page.

**Codex, the live relay proof (skips truthfully):**

```
SKIPPED [1] tests/test_the_coder_on_codex.py:31: codex is out of quota: You've hit your usage limit. Upgrade to Plus to continue using Codex (https://ch
```

## Decisions taken in this round

### [DECISION] 2026-09-12 — D57: a component may ask for itself, and the run parks on it

Topics: ask, park, resume, agent, bug-020
Affects-phases: phase-24-the-skill-registry
Affects-specs: architecture/runtime.md#the-governed-step, architecture/wire.md

`Asked` has been an observation kind since Phase 0 — *the step paused; whoever implements
governance decides what asking means* — and nothing ever produced one. BUG-020 is why it must: an
agent whose tool call was asked about holds a question that is not the policy's and not its own to
answer. It answers `Asked(question, handle)` and the executor parks the run on it exactly as if
governance had asked. On resume the component is invoked again and finds, through `resumed()`,
the host's answer and whatever it `kept` before parking — both carried in the interrupt payload
the checkpointer already holds, and so is what the step was holding (a child spawned and parked
in the same step is not in the state's channel, because the node never returned). The runtime
keeps nothing durable; a process may end between the question and the answer.

The step is charged on the leg that completes, as a governance Ask already is: the first leg's
charge never reaches the checkpoint. Measured — the "obvious" fix, not charging the second leg,
reported one step for two.

The agent adapter uses it: a held child that asked becomes the agent's own question; on resume it
restores its transcript, sends the judgement into the held child, and continues the turn it was
on. Nested agents get it for free, each level using the same mechanism. `keep` and `resumed`
cross the wire.

*Why:* consent-before-effect is what an Ask is for, and inside an agent it was a silent no.
*Overturned by:* a checkpointer that cannot carry an interrupt payload — LangGraph's all can.

---

### [DECISION] 2026-09-12 — D58: a step that cannot park asks the host live

Topics: ask, questions, recording, provider, bug-021
Affects-phases: phase-24-the-skill-registry
Affects-specs: architecture/runtime.md#modules, architecture/adapters.md#the-map, architecture/wire.md

D57 parks. A step holding a **provider's session** open cannot: it is what keeps the provider
alive, and a tool call the provider is blocked on cannot wait for a process that has ended. So a
second shape, the same in every other respect: `ctx.ask(question)` puts `Asked` on the record where
it was raised and waits on a `Questions` handle the host keeps — the same kind of thing as
`Cancellation` (D15), not a port: the host reaching in. The host sees `pending()`, answers by
handle. With no handle the answer is a `Refuse` that says nobody was there — consent nobody gave
is not consent (D38). A child inherits its parent's handle; the runtime side of the wire owns one.

The RecordingServer uses it: a CLI's tool call that the policy asks about runs as a held child
(D51), the question is put to the host live, and the child is sent the answer while the CLI waits
on the call. The coder answers at the terminal; the studio with a button.

*Why:* the person must be in the loop for a provider's act the same as for an agent's.
*Overturned by:* a provider whose session can be parked and resumed by the harness — none is.

---
