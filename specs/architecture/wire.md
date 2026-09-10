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
host ──► runtime   resume(run_id, answer)
```

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
  is generated from them and is a *client*, never a port of the runtime (`09` §3b).
- **The same suite runs both ways.** The wire passes the in-process runtime suite through a loopback
  transport, or the wire is not done.
