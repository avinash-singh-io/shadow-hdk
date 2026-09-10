---
type: History
phase: 4-the-acp-bridge
---

# Phase 4 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 3
Topics: branches, chain

`phase-4-the-acp-bridge` is cut from `phase-3-workspace-and-code` at `13bc074`. The chain is
Phase 0 → 1 → 2 → 3 → 4; nothing merges until the owner lands it.

### [DECISION] 2026-09-10 — a child agent's request is judged, not answered
Topics: acp, governance, effects, bridge

The bridge could answer ACP's client calls itself — allow a `write_text_file` because it looks
harmless, run a `create_terminal` because the child asked nicely. It does not. **A child asking to
write a file or open a terminal is asking to do something our effect vocabulary already has words
for**, so each request becomes an `EffectProfile` and goes to the governance port, exactly like a
step of the runtime's own.

That makes the bridge a **governance surface with fourteen doors** rather than a wrapper around
`prompt`, and it means a mode written for the harness governs a child agent without knowing that
child exists. ACP's `ToolCallKind` maps onto the six fields; `other`, absent, and anything
unrecognised are `ASSUME_WORST` — the same rule Phase 1 applied to MCP annotations, which is the
rule that lets the registry stay open.

### [ARCH_CHANGE] 2026-09-10 — Groups 0 and 1: fourteen doors, and each governable one judged
Topics: acp, kinds, effects, governance, bridge, g0, g1

`effects_for(kind, contained=, network=)` maps ACP's ten `ToolCallKind` values onto the six fields:
`read`/`search` read, `think` is `NOTHING`, `edit`/`move` write reversibly, `delete` writes
irreversibly, `fetch` reaches, and `execute` carries the deployment's containment under Phase 3's
rule. `other`, an absent kind, `switch_mode`, and **a kind invented after this was written** all
come out `ASSUME_WORST` — there is a test with a made-up kind, because a protocol gains values and a
system treating an unrecognised one as harmless gains a hole the day it does.

A guard checks the mapping against ACP's own declared list, so if the protocol adds a kind the suite
says so rather than silently widening.

`BridgeClient` implements all fourteen methods, and the governable ones are **judged, never answered
blind**. The consequence worth stating: *a mode written for the harness governs a child agent
without knowing that child exists.* Nobody enumerated Codex's tools.

### [DECISION] 2026-09-10 — a refusal is sent in the agent's own vocabulary
Topics: acp, permission, refusal

Phase 2 measured two ways to say no. The bridge prefers **the agent's own `reject_once` option**
when it offered one, and falls back to `DeniedOutcome` when it did not.

Choosing an option the agent itself listed is *answering* in its vocabulary — it can tell "not this
time" from "never" and adapt. `DeniedOutcome` is the blunter "I will not answer".

`reject_once` and not `reject_always`: our governance was asked about **this call**, not every
future one. Claiming permanence would assert a policy nobody wrote — and a mutation preferring
`reject_always` fails the suite.

### [DECISION] 2026-09-10 — an `Ask` becomes a refusal that says what would have been asked
Topics: acp, ask, limitation

Our `Ask` is an `interrupt()` that ends the parent's step. A child agent is holding an **open
JSON-RPC request** at that moment, and abandoning it mid-flight is not something the protocol has a
word for. So the bridge cannot suspend the parent and keep the child waiting.

The honest answer is therefore **no**, with the question recorded and the reason saying so: *"this
needs a person to allow it first: …"*. A host that wants a person in the loop for a child agent
pre-authorises through a mode instead of being asked mid-turn.

**What would lift this**, written down rather than papered over: ACP gaining a hold or deferral, or
the bridge gaining a permission cache a host can fill ahead of time. Neither is invented here to
make a limitation disappear.

### [DECISION] 2026-09-10 — money is accumulated as `Decimal` and converted once
Topics: acp, cost, usage, rounding

`Cost.amount` is a float and our `cost_cents` is an integer. Converting per call would round
`0.004 USD` to **zero**, and a thousand such charges would still be zero — the meter would never
tick. So the bridge accumulates in `Decimal` across the whole session and converts **once**: two
hundred charges of 0.004 come out as **80 cents**, and there is a test that says so.

**A currency the bridge was not configured for is not converted.** An exchange rate is policy about
a tenant's contract; guessing one would be inventing money. Mixed currencies yield `cost_cents =
None` — *unknown* — with the foreign amounts reported so a host can do the sum itself.

*If this bites*: the honest fix is `cost_cents` becoming micros in the kernel, which is a contract
change under D9 and belongs to whichever phase needs it. It is not needed yet, because accumulating
before converting is enough.

### [DISCOVERY] 2026-09-10 — two mutations survived, and both meant a test that could not tell
Topics: mutation-check, tests

**The extension test.** `ext_method` judges `ASSUME_WORST` and then, if allowed, falls through to
*"no extension method"* — so a test that only asserted `RequestError` passed whether or not the
judgement happened. It now asserts the reason names the **mode** that refused, which the fallback
never does.

**The currency test.** With only a euro charge, `amount` is zero either way, so `cents` is `None`
whether or not the foreign check exists. The shape that has a wrong answer available is **a dollar
and a euro**: 100 cents, ignoring the euro. That test exists now, and the mutation fails.

Also worth recording: an edit script silently did nothing because ruff had reformatted its target
onto one line, and the test kept its old body while the report said it had been fixed. Every edit
script in this session asserts its target now — the third time that has cost time.

**Group 1 was written code-first**, contrary to Rule 13, and the eleven mutation checks stand in for
the red step. That is a weaker guarantee than red-first and is recorded as such rather than glossed.

### [DISCOVERY] 2026-09-10 — the ambient contextvar does not cross into a library's own task
Topics: d2, contextvars, acp, bridge

The most interesting thing this phase found, and it is an **edge of D2 rather than a bug in it**.

A child agent's `write_text_file` arrived and `current_run()` was `None`, so the bridge refused a
write a writing mode plainly permitted. The reason: a contextvar is copied **when a task is
created**, and the ACP SDK creates its reader task inside `connect_to_agent` — which happens when
the *session opens*, not when a *turn runs*. Every callback the child makes therefore arrives on a
task whose context was captured before any run existed.

D2 says a run started inside a step finds its parent ambiently, and that holds for everything the
runtime creates. It does not hold across a task somebody else made earlier. So the bridge **tells**
the client which run governs it — `client.governed_by(current_run())` around the prompt — rather
than hoping a contextvar propagates through a foreign event loop.

Any adapter whose callbacks are driven by a library's own task has this problem and needs this
answer. Worth stating in `09` if a second one appears.

### [ARCH_CHANGE] 2026-09-10 — Groups 2 and 3: another agent, governed by the same six fields
Topics: acp, bridge, residency, clock, usage, g2, g3

`AcpAgent` is a `ComponentPort`. 51 tests in this adapter, 302 in the suite, all four gates zero.
Everything below is measured against `spikes/acp/agent.py` — a real conformant agent in its own
process, over a real stdio pipe.

**Residency.** One process and one handshake for the session, asserted by `sessions_opened == 1`
across two invocations. A child agent is expensive to start; a five-step composition should not be
five cold starts.

**Coarse at the door, fine inside.** A component's declared effects are judged *before* it is
invoked, so a child claiming only to read is admitted by a reading mode — and when it then asks to
write, the **inner** judgement refuses. A promise at the door is not a permission inside, and the
test that says so is the one that made this design explicit rather than accidental.

**Our clock over their runaway.** A looping child is stopped at `min(configured timeout, what the
lease has left)`, measured with elapsed. An adapter constructed with a 600-second timeout cannot
outlive a run whose lease has two seconds left.

**What the child spent** comes back in the shape `_usage_of` reads, so the parent's meter charges it
without knowing ACP exists.

### [DISCOVERY] 2026-09-10 — two tests about a clock, with no clock over them
Topics: tests, hangs, timeout, tooling

Phase 2 wrote down that *a hang is a worse test than a failure*, and then this phase wrote two tests
whose subject **is** the bridge's clock and gave them no outer bound. A mutation that broke the
clock did not fail them — it stalled the suite for ten minutes, and the mutation script reported
`INCONCLUSIVE` while a killed run left a mutated file on disk.

Both are fixed and both fixes generalise. The tests take an `asyncio.wait_for` backstop, so a broken
clock fails in thirty seconds. And **`pytest-timeout` is now a dev dependency with a 60-second
global limit**: this suite drives MCP servers, sandboxes and ACP agents, several of them precisely
to prove that something *stops*, and no test in it may hang. The whole suite runs in under twenty
seconds, so sixty is far above anything healthy and far below "nobody noticed".

A third finding, recorded because it recurred: a mutation script's `.replace()` silently did nothing
when ruff had reformatted its target onto one line, and the report said a test was fixed when its
old body was still there. Every edit and mutation script in this session asserts its target now.

### [DISCOVERY] 2026-09-10 — three mutations, three tests that could not tell
Topics: mutation-check

*The extension test* could not distinguish a governance refusal from the "no such method" fallback.
*The currency test* used one currency, where the total is zero either way — a dollar **and** a euro
is the shape with a wrong answer available. *And nothing checked that a timed-out child is actually
dead*: every test read the observation, none looked at the machine, so removing the kill left the
suite green while leaking a process holding a subscription seat.

Twenty-four mutations across this phase. Three found missing tests; the rest bit.
