# `shadow_hdk.kernel`

Frozen dataclasses and protocols only. No I/O, no clock, no logging, no framework import.
Every type here is published as JSON Schema and round-trips through JSON in CI.

What is in it, and where it is designed (`intent-ecosystem/vision/09-the-agentic-system.md`):

| module | holds | section |
|---|---|---|
| `effects` | `EffectProfile`, `ScopeSet`, the narrowing order and the meet | §2 |
| `components` | `Interface`, `Provenance`, `Component`, `Registration` | §4 |
| `composition` | `Invoke · Sequence · FanOut · Until · Await`, `Composition` | §5 |
| `observations` | `Completed · Refused · Asked · Failed · Pending`, `Proposal` | §6 |
| `leases` | `Lease` with a ceiling and a floor, and `carve` | §7 |
| `capabilities` | provider/environment facts and evidence, host requirements, total compatibility and selection | D96–D98 |
| `events` | `Started · Composed · Invoked · Observed · Proposed · Refused · Asked · Spawned · Ended` and the rest, `PlanAdmitted · PlanRefused` among them | §7 |
| `planning` | `PlanLimits` (narrowing by `meet`), `measure`, `admit`, `PlanMismatch`, `composition_digest` — a plan judged whole, purely (D107–D109) | Epic 0009 |
| `ports` | the six protocols a host or adapter implements | §3, §7 |
| `contracts` | JSON Schema export and the round-trip helpers | §3b |
