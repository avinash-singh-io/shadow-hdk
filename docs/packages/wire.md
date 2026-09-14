# `shadow_hdk.wire`

The runtime, reachable from another process or another language.

`specs/architecture/wire.md` fixes the shape: the host **drives**, the runtime **calls back**.
`run` and `resume` are host → runtime; the ports invert.

Protocol 2 publishes the Phase 31 capability boundary: requirements on `thread/start`, the accepted
selection on start/resume, provider discovery through `providers/list`, dry selection through
`capabilities/check`, and complete typed `capability_mismatch` refusals. JSON Schemas and the
TypeScript client are generated from the same kernel contracts.
