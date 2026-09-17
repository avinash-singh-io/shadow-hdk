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
