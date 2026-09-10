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
- [x] `Trust(keys, revoked, must_sign)` — `runtime/trust.py`; `Ports.trust`, `None` checks nothing
- [x] `Registry(ports, trust=…)` refuses at refresh, recording reasons in `registry.refused`
- [x] RED: each refusal by name; revoked-with-valid-signature; must_sign inside/outside; visible() omits — 15 tests, `tests/runtime/test_registry_trust.py`
- [x] Gate — ruff 0 / format 0 / mypy 0 (99 files) / pytest 596 passed, 9 deselected; 17 mutations bite

## Group 2 — the receipt, and the lease at the act
- [x] a test driver returning `Acted`, reading the lease at act time — `runtime/acting.py` (`exhausted`, `grounds`); `RunContext.step`, `RunContext.idempotency_key()` = `run/step`; the executor opens the scope around the invoke only
- [x] RED: receipt on the stream with four fields; exhausted lease refuses and performs nothing — 10 runtime tests (`tests/runtime/test_acting.py`) incl. the clock moved between admission and act, and the retry key through `Await`+`resume`; 2 agent tests (the model is told the receipt, never the grounds)
- [x] `[~]` what ADR-1 must settle — the four rows below
- [x] records, board, *Pins* row (0.6.0 → 0.7.0), status, roadmap
- [x] Gate — ruff 0 / format 0 / mypy 0 (101 files) / pytest 608 passed, 9 deselected; 23 mutations bite

## `[~]` — the policy, which waits on ADR-1 (nothing here is decided in this phase)
- [~] **which effects must be signed at all.** Today `Trust.must_sign` is `None`: only what claims a signature is verified. Settled by ADR-1 naming the ceiling; verified by `tests/runtime/test_registry_trust.py` (inside/outside `must_sign`) against that ceiling, unchanged
- [~] **who may hold a signing key, and who may revoke one.** Today `Trust.keys` and `Trust.revoked` are whatever the deployment constructs; every key in this repo is a test fixture minted in the test. Settled by ADR-1's issuance and revocation process; the mechanism does not change
- [~] **what a warrant's scope is, and who issues one.** Today `grounds(warrant=)` carries whatever the driver was handed, opaque, and it is `None` in every test — recorded, never judged. Settled by ADR-1 naming the warrant's shape; `grounds` keeps carrying it
- [~] **which acts need a warrant beyond a lease.** Today `exhausted` checks time and money only, and no act is refused for want of a warrant. Settled by ADR-1; the check belongs beside `exhausted`, and until then it would be a rule nobody wrote
