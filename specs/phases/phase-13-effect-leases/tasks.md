---
type: Tasks
phase: 13-effect-leases
---

# Phase 13 — tasks

## Group 0 — the contract, and the signature
- [ ] `Provenance.signature`, `Acted`; every package to 0.7.0; schemas republished
- [ ] `runtime/trust.py`: `signing_bytes`, `sign`, `verify` over HMAC-SHA256
- [ ] RED: verifies; tampered effects/id/key each refused; canonical bytes stable; round-trip
- [ ] Gate

## Group 1 — trust at the registry
- [ ] `Trust(keys, revoked, must_sign)`
- [ ] `Registry(ports, trust=…)` refuses at refresh, recording reasons
- [ ] RED: each refusal by name; revoked-with-valid-signature; must_sign inside/outside; visible() omits
- [ ] Gate

## Group 2 — the receipt, and the lease at the act
- [ ] a test driver returning `Acted`, reading the lease at act time
- [ ] RED: receipt on the stream with four fields; exhausted lease refuses and performs nothing
- [ ] `[~]` what ADR-1 must settle
- [ ] records, board, *Pins* row, status, roadmap
- [ ] Gate
