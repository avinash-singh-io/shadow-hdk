# `shadow_hdk.wire`

The runtime, reachable from another process or another language.

`specs/architecture/wire.md` fixes the shape: the host **drives**, the runtime **calls back**.
`run` and `resume` are host → runtime; the ports invert.
