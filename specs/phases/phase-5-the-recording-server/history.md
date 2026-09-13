---
type: History
phase: 5-the-recording-server
---

# Phase 5 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 4
Topics: branches, chain

`phase-5-the-recording-server` is cut from `phase-4-the-acp-bridge` at `4a92c9a`. The chain is
Phase 0 → 1 → 2 → 3 → 4 → 5.

### [CORRECTION] 2026-09-10 — a routed tool call is **controlled**, not observed
Topics: posture, controlled, observed, r9

`08` §4.6 says the recording server's calls carry *"posture: observed"*, and the instruction for this
phase repeated it. Building it makes the shorthand wrong, and the distinction `08` §9 R9 actually
draws says so:

> **Controlled versus observed** on every run and every act; only controlled satisfies
> consent-before-effect; observed renders as a degraded posture.

*Controlled* means **we gated it before it happened**. A call routed through the RecordingServer is
judged by our governance port and executed by our runtime — that is controlled in the strictest
sense available. Calling it observed would understate our own guarantee and, worse, would make a
gated call indistinguishable from an ungated one.

What is genuinely **observed** is the other thing a child agent does: its own unmediated work, which
we learn about from an ACP `session_update` *after* it happened. We did not consent to it; we found
out. That is the degraded posture R9 means.

So the line is not *parent versus child*. It is **gated versus merely reported**, and it happens to
cut through the middle of a child agent's behaviour: what it routes through us is controlled, what
it does natively is observed.

### [DECISION] 2026-09-10 — posture lives on `Provenance`, and only needs saying when it is `observed`
Topics: posture, provenance, kernel, d9

Three places it could live: an event field, the observation payload, or provenance.

The observation payload is untyped and ad-hoc. An event field would have to be added to several
events and would say the same thing repeatedly. **Provenance already answers "how did this come to
be here"**, which is exactly the question, and it already travels with every `Proposal` — the
carrier for *something happened and we are telling the host*.

`Provenance.posture` defaults to **`controlled`**, because everything the runtime invokes, it gated.
The exception is explicit: the ACP bridge stamps `observed` on a tool call it only heard about. A
default of controlled is the safe way round — an adapter that forgets to say produces a claim that
is true of everything the runtime does.

A kernel field is a contract change: every package takes a minor bump under D9, and it earns a row
under *Pins* on the board.

### [ARCH_CHANGE] 2026-09-10 — Group 0: posture ships, and every package moves to 0.3.0
Topics: posture, provenance, kernel, acp, d9, g0

`Provenance.posture` exists, defaulting to `controlled`. The ACP bridge stamps `observed` on a
`tool_call` notification — work the child did on its own and told us about afterwards, which we
could not have refused.

Both halves are tested against each other, because either alone says nothing: a permission request
we judged comes out **not** overheard, and an unmediated call comes out `observed`. If both landed
in the same bucket the field would be decoration.

Every package to **0.3.0** (D9), and a *Pins* row on the board.

### [DISCOVERY] 2026-09-10 — a helper that always passes an argument cannot test its default
Topics: mutation-check, tests

A mutation flipping the default posture to `observed` **left the suite green**. The cause was a test
helper I had just written: `a_provenance(posture="controlled")` passed the value explicitly every
time, so the one test named *"the default is controlled"* never exercised a default at all.

It now constructs a bare `Provenance` with no `posture` argument. Fourteenth vacuous test a mutation
has found here, and the first caused by a *convenience helper* rather than by a missing case —
worth the entry because the helper looked like it made the test clearer.

Also caught: `from __future__ import annotations` makes an undefined name in a type annotation a
**lint** error and not a runtime one, so a missing import passed 308 tests and only ruff objected.

### [FEATURE] 2026-09-10 — Group 1: the registry, offered to a child as an MCP server
Topics: recording, mcp, routing, g1
Affects-phases: none
Affects-specs: none

`shadow_hdk.adapters.recording.RecordingServer`. `09` §8 taken literally: `call` does not judge,
or emit, or meter. It runs a one-step composition as a child of the parent run, and governance, the
parent's event stream and the carved lease all arrive because that is what a run already does. What
the child is offered is `RunContext.visible()` — the same computation the model sees.

Ten tests drive it directly; four more drive it over a real `ClientSession` through a stream pair,
because `attach` hands two request handlers to somebody else's server naming their parameter models
and a mistake there is invisible to a direct call and total over a wire. That wire test is what
caught the SDK's model fields being snake_case (`input_schema`, `is_error`), which a direct call
never touches.

### [DISCOVERY] 2026-09-10 — two corrections a new adapter has to inherit
Topics: langgraph, events, refusal, step-ids
Affects-phases: none
Affects-specs: none

Both are in the code as comments, because both are the sort of thing the next adapter will get
wrong the same way.

**The step id joins with `__`, not `:`.** LangGraph reserves the colon for checkpoint namespaces, so
a step id carrying one fails at graph construction. The compiler learned this in Phase 0; an adapter
minting its own step ids has to know it too.

**A refusal emits one event, not two.** `Refused` *is* the record of what happened to that step, and
a second `Observed` saying the same thing is how two narrations come to disagree. So a reader
watching only for `Observed` misses every refusal — which is what the first version of this did.

### [ARCH_CHANGE] 2026-09-10 — the MCP topology is inverted, and that is why `pipes.py` exists
Topics: recording, mcp, transport, subprocess, phase-9
Affects-phases: phase-9
Affects-specs: none

Planned as `[~] serving a subprocess child needs a listening transport`. Chasing it found the real
shape, which is not about listening: **in the SDK's stdio convenience the client spawns the server**,
and that cannot be us. `RecordingServer` holds a live `RunContext`, the parent's lease and the
parent's event stream, none of which survive being launched fresh in another process. So the parent
spawns the *child* and serves MCP over the child's own stdin and stdout — we write to its stdin, we
read from its stdout, and the child runs an ordinary `ClientSession` believing it was started by
somebody.

The framing is the same newline-delimited JSON-RPC the stdio transport already uses; the SDK does
not expose it for streams other than this process's fd 0 and 1, so `serve_over_pipes` is twenty
lines rather than an import.

**Measured** (`tests/adapters/recording/test_over_a_process.py`, against `spikes/mcp/child.py`): a
real OS subprocess lists exactly the run's visible registry, calls `look` and receives the
component's output, and the parent's stream carries `invoked` and `observed` under the child's run
id. Under a reading mode the same child cannot see `wipe` and is refused when it asks anyway.

**Still unproven, now stated precisely:** a child on another *machine* needs a transport where the
server is already listening (streamable HTTP), because this server can only be connected to, never
launched. Phase 9's wire starts from that, not from stdio.

### [DISCOVERY] 2026-09-10 — a test whose subject is a process owns a deadline
Topics: tests, mutation-check, timeouts
Affects-phases: none
Affects-specs: none

Mutating `serve_over_pipes` to write a message without its trailing newline is a real defect: the
child never sees a complete frame and waits forever. The mutation was caught in 47s by the test's
own `anyio.fail_after(45)` rather than by the global 60s pytest timeout killing the session — the
same lesson the clock tests taught in Phase 3, now applying to processes.

Nine mutations across Group 2, all bite: the catalogue unfiltered by governance, the child unlinked
from its parent, the child reusing the parent run id, a refusal reported as success, a refusal
indistinguishable from a failure, the component's output replaced, the child ceiling ignoring what
the parent has left, and the framing without its newline.

One bug found by a test going red first, as intended: `governance` was dropped on the way into the
child helper, so the narrowing test saw an unnarrowed registry and said so.

---
