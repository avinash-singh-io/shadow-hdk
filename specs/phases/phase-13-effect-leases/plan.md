---
type: Plan
phase: 13-effect-leases
---

# Phase 13 — plan

```
# Sequential: Group 0 → 1 → 2. Group 0 is the contract change; 1 is the mechanism; 2 the receipt.
```

## Group 0 — the contract, and the signature

- `Provenance.signature: str | None` — the proof beside the claim; `Acted` as an observation kind
- Every package to **0.7.0** (D9); `test_versions`; schemas republished and their test green
- `runtime/trust.py`: `signing_bytes(registration)` — canonical, minus the signature;
  `sign(registration, key_id, secret) -> Registration`; `verify(registration, secret) -> bool`;
  HMAC-SHA256, `hmac.compare_digest`
- RED: a signed registration verifies; a tampered effect profile does not; a tampered id does not;
  a wrong key does not; `signing_bytes` is identical with and without the signature present; a
  contract round-trip carries the signature

**Commit:** `feat(kernel)!: a driver signs what it declares, and an act leaves a receipt`

## Group 1 — trust at the registry

- `Trust(keys, revoked, must_sign)`: keys by id; a revocation set; `must_sign` an `EffectProfile`
  ceiling — anything not narrowing it must be signed; `None` verifies only what claims a signature
- `Registry(ports, trust=…)`: on refresh, a registration that claims a signature is verified, and
  one that must be signed and is not, or is signed by an unknown or revoked key, or does not
  verify, is **refused** — absent from the catalogue, recorded in `registry.refused` with the reason
- RED: each refusal by name; a revoked key refused **with a valid signature**; an unsigned
  registration inside `must_sign` admitted; one outside it refused; `RunContext.visible()` omits a
  refused driver; refusal reasons survive to the registry

**Commit:** `feat(runtime): a driver that cannot prove itself is absent, and says why`

## Group 2 — the receipt, and the lease at the act

- A test driver (test-local) that performs a fake effect, reads `current_run().remaining()` at the
  moment of the act, refuses when spent, and returns `Acted`
- RED: through a real run, `Acted` is on the event stream with all four fields; a driver invoked
  on an exhausted lease returns `Refused` and performs nothing; the receipt's `grounds` carry what
  it was performed under
- `[~]` everything ADR-1 must settle, named
- records, board, *Pins* row, status, roadmap

**Commit:** `feat(runtime): every effect is attributed, and checked at the moment of the act`
