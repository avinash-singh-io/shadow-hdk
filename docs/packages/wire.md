# `shadow_hdk.wire`

The runtime, reachable from another process or another language.

`specs/architecture/wire.md` fixes the shape: the host **drives**, the runtime **calls back**.
`run` and `resume` are host → runtime; the ports invert.

Protocol 2 publishes the Phase 31 capability boundary: requirements on `thread/start`, the accepted
selection on start/resume, provider discovery through `providers/list`, dry selection through
`capabilities/check`, and complete typed `capability_mismatch` refusals. JSON Schemas and the
TypeScript client are generated from the same kernel contracts.

Phase 32 adds `Item.inputs` to that generated contract, with an explicit marker when canonical JSON
exceeds the 64 KiB projection bound. HTTP/SSE now consumes `runtime.StreamSession`: bounded replay,
one attachment, typed cursor/grace expiry, and an ephemeral 15-second heartbeat. The TypeScript
client defaults to a 45-second silence deadline and reattaches with its last event id; heartbeats
are link frames and never become durable events.

Phase 36 adds `unmapped_behaviour` to the results of `thread/start`, `thread/resume` and
`thread/set_mode`: the behaviour fields the thread's mode set that the provider could not take. A
host in any language hides those controls for that provider.

Phase 36 keeps protocol `3` and adds: `plan_admitted` / `plan_refused` on the stream, `plan_refused`
in `ERROR_KINDS`, `plan_limits` in and out of `thread/start` and `thread/resume` (and out of
`thread/set_mode`), `plan` on every `modes/list` row, and `thread/amend` for a parked plan continued
on a different composition. A crossed `context.children.spawn` carries `limits`, `proposed_by` and
`step`, and a refusal crosses as `plan_refused` with its mismatches. See `docs/migrations/0.31.md`.

Phase 44 (0.32) keeps protocol `3` and opens the thread door to a host's own components:
`thread/start` and `thread/resume {host_components: true}` add the calling connection's
`RemoteComponents` port to the thread's registry — `components.registrations` and
`components.invoke` called back, as `run` has always done — with `source: "host"` in `tools/list`,
a gone host named by the transport's session id, and an irreversible host tool recorded `observed`.
The TypeScript client gained a `Transport` (HTTP as before; a spawned runtime's stdio from
`shadow-hdk-client/node`), `tool()` and `components.serve`. See `docs/migrations/0.32.md`.
