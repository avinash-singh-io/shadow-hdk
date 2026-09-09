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
| `shadow-hdk serve` | JSON-RPC 2.0 over HTTP/2, events over SSE | a host in another process or another language |
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

- **Negotiated at `initialize`**, refusing rather than degrading on a version mismatch.
- **Authentication is a run token**: short-lived, single-run, minted when a run opens, carrying the
  scope, principal and lease. The runtime never holds a host credential.
- **Schemas are published** from `shadow_hdk.kernel.contracts.all_schemas()`; a TypeScript client
  is generated from them and is a *client*, never a port of the runtime (`09` §3b).
- **The same suite runs both ways.** The wire passes the in-process runtime suite through a loopback
  transport, or the wire is not done.
