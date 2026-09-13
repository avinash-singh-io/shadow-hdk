---
type: Architecture
---

# The wire — the out-of-process form (Phase 9)

> Sketched at founding so nothing built before it makes it impossible; designed when it is built.

The runtime is embeddable first: a plain async function a host imports. The wire is a **composition
root over the same package**, not a redesign — which is only true because every port argument and
return already round-trips through JSON (`tests/kernel/test_contracts_round_trip.py`).

## Two forms

| form | transport | for |
|---|---|---|
| `shadow-hdk serve` | JSON-RPC 2.0 over **HTTP/1.1** (uvicorn; HTTP/2 was the design's word and is not what is served), events over SSE | a host in another process or another language |
| `shadow-hdk --stdio` | JSON-RPC 2.0 over stdio | a child process; the same shape MCP and ACP use |

## The direction of every call

The host **drives**; the runtime **calls back**. `run` and `resume` are host → runtime. The six ports
invert: when the runtime needs a judgement, a model completion, a component invocation or a sink
write, it issues a request the host answers. Events stream host-ward continuously.

```
host ──► runtime   run(composition, options)
host ◄── runtime   judge(effects, context)      → Allow | Ask | Refuse
host ◄── runtime   complete(request)            → response
host ◄── runtime   invoke(registration, inputs) → observation
host ◄── runtime   propose(proposal)            → ack
host ◄── runtime   event…                       (SSE / notification)
host ──► runtime   resume(run_id, answer)       answer: a judgement, or {step id: judgement}
```

> **Corrected 2026-09-10 (BUG-010, D38).** `answer` is a **judgement**, sent as its JSON —
> `{"kind": "allow"}` or `{"kind": "refuse", "reason": …}` — and loaded at the runtime's edge like
> everything else that crosses (D19). It used to be anything at all, harmlessly, because the
> runtime re-judged on resume and threw the answer away; now the answer decides, so a value that is
> not a judgement is refused rather than read as consent nobody gave. One judgement settles every
> step parked in that superstep; a map keyed by step id answers them one at a time.

## The second shape — threads served (Phase 26, D67, D69)

The direction above inverts the ports. The other shape keeps them **runtime-side**: the process
serving the wire hands in a `ThreadHost` (`shadow_hdk.serve.ServeHost` — the shipped
composition, a store, the provider signed in there), and the host across the wire drives *threads*
by method, the way Codex's app server is driven. Both shapes are served on one peer; a host uses
whichever it is.

```
host ──► runtime   thread/start {root | roots: [{name, path}…], mode, provider, name}
                       → thread_id · root (the primary) · roots · environment (the sandbox's mode) · mode · modes
host ──► runtime   thread/resume → … · turns · pending  (the questions the last host left — D80)
host ──► runtime   thread/close · list · fork · rollback · archive
host ──► runtime   thread/set_mode → events · environment      (the sandbox follows the mode — D76)
host ──► runtime   thread/add_root {name, path} → events · roots  (added live, re-proven — D76)
host ──► runtime   thread/set_option · remaining
host ──► runtime   turn/start                    → the turn's record, when it ends
host ──► runtime   turn/steer · turn/interrupt · run/cancel
host ──► runtime   approvals/pending · approvals/answer  (approve · deny · approve_and_add_rule · {text})
                       a left question (D80) is settled by its thread: the parked act runs from its
                       checkpoint and the answer carries its events
host ──► runtime   store/put · get · delete · list · version · modes/list · rules/list · batteries/list
host ──► runtime   tools/list {thread_id}        what the agent is offered now, each with the mode's
                                                 judgement (allow · ask · refuse) and its source (D73)
host ──► runtime   skills/list                   the composition's skills, with their sources (D73)
host ──► runtime   files/list · files/read {root, path}   under the thread's roots only (D69, D76)
host ◄── runtime   event · item · activity       (tagged with the thread; one fold, runtime-side — D46)
host ◄── runtime   approval_request · input_request · request_withdrawn
```

Rules: every public method of `Thread`, `Approvals` and `Store` crosses under a `protocol.py`
name or is named in the parity test's `HANDLES_NOT_CROSSING` with a reason; a session that ends
closes every thread it opened; every session and every served thread runs on the host's
checkpointer (D80) — a run parked in one session is there for the next, and outlives the process
when the store's url is a file or a database (D79); a thread's offer is held by one task for its lifetime, so any
method may be called from any task; a change between turns (`set_mode`, `add_root`) is on the
record and goes down the stream as an `event` like any other, and comes back in the result for
the one that asked; a page the server serves (`--page`) is a client of these methods and nothing
else — the studio is that page. A resident provider is told the catalogue changed
(`notifications/tools/list_changed`) and, because Claude Code was measured to keep its list
anyway (BUG-032), is reopened on its own session after a mode change or a root added — its list
fresh, its memory kept (`AgentPort.open(resume=)`).

## Rules already fixed

> **Corrected 2026-09-10 (BUG-006).** This section listed the run token as fixed; it is **not
> built**. Until it is, `served_over_http` is **loopback-only by default** and refuses to bind
> anything else without a `token=` — a deployment-wide stop-gap, not the per-run credential below.
> Two more corrections: `initialize` is now **required** before `run` or `resume`, and an omitted
> protocol version is a **mismatch**, not a match (it used to default to this build's own, so a
> peer that said nothing counted as agreeing). Every runtime→host callback carries a **timeout**,
> because the lease bounds a run and a run waiting on a peer is not running.

- **Authentication is a run token**: short-lived, single-run, minted when a run opens, carrying the
  scope, principal and lease. The runtime never holds a host credential.
- **Schemas are published** from `shadow_hdk.kernel.contracts.all_schemas()`; a TypeScript client
  is generated from them and is a *client*, never a port of the runtime (`09` §3b). The client is a
  package a product installs (`clients/typescript`, by path until it is on npm), and it runs in a
  browser: `fetch` is never called with the client as `this` (BUG-039).
- **The stream opens with a frame** (BUG-038). `GET /rpc` answers the session id in a header and an
  SSE comment frame at once, before anything is asked — a Node front (a dev proxy, a product's
  backend) holds a response's headers until its first body byte, and the first frame used to be a
  reply to a call the client cannot make without the id. A client ignores a line that is not `data:`.
- **The same suite runs both ways.** The wire passes the in-process runtime suite through a loopback
  transport, or the wire is not done.
- **Parity is an invariant, not a promise** (Phase 23, D51). Every `RunContext` method either
  crosses — `visible`, `floor_met_now`, `spawn_options_now`, `reasoned` with its step, the
  children's `spawn`/`send`/`release`/`is_held` through `WireChildren` — or is named in the parity
  test's `NOT_CROSSING` table with a reason; and every kernel event kind, `Reasoning` and the `Step`
  projection included, is in the published schemas. The agent adapter spawns the plans its model
  authors *through the runtime*, so a sub-agent runs where the record is, whichever side the agent
  is on; the pattern's ceiling crosses as data and is applied there as a second gate (`Narrowed`).
- **Approvals cross** (D57, D58): `context.keep` and `context.resumed` carry a parked component's state and answer; `context.ask` carries a live question to the `Approvals` handle the runtime side owns.
- **The registry socket is authenticated** (D52): a per-serve token from `secrets` in the relay's
  environment, sent as the first line before MCP; the run token above is still the wire's own debt.
