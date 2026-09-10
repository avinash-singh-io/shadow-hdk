---
type: History
phase: 13-effect-leases
---

# Phase 13 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D27: a driver is trusted by a signature over what it declares
Topics: drivers, signatures, revocation, registry, d27
Affects-phases: none
Affects-specs: specs/architecture/decisions.md, specs/architecture/adapters.md

`signed_by` has been on `Provenance` since Phase 0 and nothing has read it. Trusting it as a name
has the hole every name-based trust has. So the signature is over the registration's canonical
form — id, interface, **effect profile**, labels, provenance minus the signature — which binds it to
the declared effects: a driver cannot present narrower effects than it signed for, and one whose
effects were edited after signing is refused as forged.

Checked at registration in the one funnel, so a driver that cannot prove itself is absent from the
catalogue rather than refused per call. Revocation is a list checked at every refresh, and a
revoked key is refused even with a valid signature, because that is what revocation is for.
HMAC-SHA256 from the standard library, symmetric on purpose: the boundary is keys this deployment
holds. *Overturned by* a marketplace of third-party drivers, which is ADR-1's question.

### [NOTE] 2026-09-10 — the gate, stated first
Topics: adr-1, r9, scope
Affects-phases: none
Affects-specs: none

R9 waits on ADR-1. The mechanism is built here; which effects must be signed, who holds a key, what
a warrant's scope is, and which acts need one are ADR-1's and are recorded as `[~]`, not decided.

---

### [NOTE] 2026-09-10 — Group 1: three survivors, three tests
Topics: mutation, trust, registry
Affects-phases: none
Affects-specs: none

Fifteen RED-first tests; fourteen mutations bit at once and three survived. None was a test bug in
the usual sense — each was an untested claim. (1) The signature-without-key guard was shadowed:
`None not in keys` refuses anyway, so its distinct reason was never exercised; the reason is more
honest than "unknown key None", so it got a test rather than being deleted. (2) `refused` had no
two-refresh test, so `+=` survived; now it is asserted to be this refresh's list, like
`unreachable`. (3) "Revocation before verification" was a docstring claim: the revoked test used a
valid signature, which refuses in either order. Now a revoked, unknown, forged key is refused as
*revoked* — revocation is a fact about the key, and the actionable reason wins.

Also: a mutation pass whose backups silently failed stacks mutations and reports nonsense. The
scratch path must be set explicitly in the shell that runs the pass.

---
