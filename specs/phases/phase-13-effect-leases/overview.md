---
type: Phase
phase: 13
name: effect-leases
epic: 0005-the-body
status: complete
topics: [effects, leases, drivers, signatures, revocation, receipts, supply-chain, d27, r9, adr-1]
deps: [phase-12-derivation]
---

# Phase 13 — Leases on effects, and the driver supply chain

## Goal

Roadmap: *`EffectPort` takes a lease; keys, signatures, receipts, revocation.* Serves R9 — *act on
the world … with authority checked at the moment of the act and every effect attributed.* `08` §249
gives the receipt its shape: `ActReceipt{foreign_id, idempotency_key, exit, grounds}`, *the only
place anything happens outside the log*.

## The gate, stated before anything is built

The vision is explicit: **R9 waits on `O2` (ADR-1) — external execution control coverage and effect
leases.** ADR-1 is the owner's and unwritten. So this phase splits, and the split is the first
thing in the file so nobody mistakes the mechanism for the policy:

| the mechanism — buildable here | the policy — waits on ADR-1 |
|---|---|
| a signature over what a driver **declares**, verified when it registers | which effects must be signed at all |
| a revocation list checked at registration, never trusted from memory | who may hold a signing key, and who may revoke one |
| a receipt as the observation of any world-effect, so every effect is attributed | what a warrant's scope is, and who issues one |
| a driver that reads the lease at the moment of the act and refuses when it is spent | which acts need a warrant beyond a lease |

The second column is `[~]`, naming what ADR-1 must settle. **Nothing in it is invented here.**

## D27 — a driver is trusted by a signature over what it declares, checked when it registers

`Provenance` has carried `signed_by` since Phase 0 and nothing has ever read it. The obvious next
step is to trust the name — *this came from a key we know* — and it has the hole every
name-based trust has: a name is a claim, and the thing being trusted is a component that will act
on the world.

**So the signature is over what the driver declares.** What is signed is the registration's
canonical form: its id, its interface, its **effect profile**, its labels, and its provenance minus
the signature itself. That binds the signature to the effects: a driver signed as *reads the
workspace* cannot later present itself as *writes everywhere* under the same signature, and a
driver whose declared effects were edited after signing is refused as forged, not merely re-judged.

**Checked at registration**, in the one funnel every component passes through — `Registry.refresh`
— so a driver that cannot prove itself is *absent from the catalogue* (Phase 3's rule: the model
never sees a tool it may not use) rather than refused per call. The refusal and its reason are
kept on the registry, beside `unreachable`, so a record can say what was left out and why.

**Revocation is a list, checked then.** A key on the list is refused even when its signature
verifies, because revocation exists precisely for the case where the signature is still valid and
the trust is not. Checked at every refresh, never cached from a previous one.

**HMAC-SHA256 over the standard library**, deliberately symmetric. The deployment both mints and
verifies its driver keys, so the trust boundary is *keys this deployment holds*, not *keys the
public verifies* — and asymmetric signing would mean a dependency for a property nobody has asked
for yet. Recorded as the choice it is.

*Rejected:* trusting `signed_by` as a name — a claim, not a proof.
*Rejected:* signing only the provenance — it would let declared effects drift under a valid
signature, which is the one thing the signature is for.
*Rejected:* checking per call — a driver that could not prove itself would still be in the
catalogue, and a model would be offered a tool the deployment had not admitted.
*Rejected:* a dependency for asymmetric keys — the property it buys belongs to a marketplace of
third-party drivers, which is ADR-1's question and is not this deployment's today.

*Overturned by:* that marketplace. A driver signed by somebody the deployment does not share a
secret with wants a public key, and that is a decision about who signs, which is ADR-1.

## What this costs

Two kernel contract changes, so every package moves to **0.7.0** (D9) and the board gets a *Pins*
row: `Provenance.signature` (the proof, beside the claim `signed_by` already made), and `Acted`, a
new observation kind — the receipt of a world-effect, with a foreign id, an idempotency key, an
exit, and grounds.

## Exit criteria

- A registration signed by a trusted key registers; unsigned where a signature is required,
  signed by an unknown key, signed by a revoked key, or signed over different declared effects —
  each is refused **with the reason**, and absent from the catalogue
- A revoked key is refused even when its signature verifies
- A world-effect is observed as an `Acted` receipt carrying foreign id, idempotency key, exit and
  grounds, and it reaches the event stream and the record like any observation
- A driver reads the lease at the moment of the act and refuses when it is spent
- Everything ADR-1 must settle is written down as `[~]`, and nothing in it is decided here
