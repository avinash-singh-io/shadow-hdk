---
type: Phase
phase: 11
name: contained-sandboxes
epic: 0005-the-body
status: complete
topics: [sandbox, contained, gvisor, firecracker, isolation, proof, d25, r9]
deps: [phase-10-effect-rules]
---

# Phase 11 — Contained sandboxes

## Goal

Roadmap: *gVisor, Firecracker as `contained: true` components.* Serves R9 — *act on the world … with
authority checked at the moment of the act.*

Phase 3 made `contained` a deployment fact with no default and said why: **a sandbox that claimed
containment it did not have would be the most dangerous lie in this system.** It then trusted the
deployment's word. This phase stops trusting it.

## What this machine can and cannot do — decided first

This is macOS with no gVisor, no Firecracker, no container runtime, and a standing rule against
installing any of them. So the phase splits, and the split is written here before anything is
built so nobody mistakes the buildable half for the whole:

| buildable here | needs a Linux host |
|---|---|
| the contract: a sandbox that says `contained: true` **only after proving it** | running `runsc` and observing the proof it gives |
| the backend seam, and a fake backend that can be told to pass or fail its proof | running Firecracker and observing its proof |
| the decision about what a proof *is* (D25) | measuring the overhead either adds to a step |
| the gVisor and Firecracker backends **as code**, with live tests that skip when the binary is absent | those live tests going green |

The second column is recorded as `[~]` with the exact command that settles each. **A backend that has
never been run is not done, and is not called done.**

## D25 — containment is proven at construction, and refused if it cannot be

The obvious design is a flag: `ContainedSandbox(backend=GVisor())` sets `contained: true` because
the caller said gVisor. That is Phase 3's design with a nicer name, and it has the same hole — the
caller's word is the only evidence.

**So a backend has to prove itself, and the sandbox refuses to exist until it does.** Each backend
knows one thing that is true inside it and false on the host — gVisor's kernel announces itself,
a Firecracker guest's hardware does — and the sandbox runs that probe *through the backend* before
it registers anything. A probe that fails, or a binary that is absent, raises at construction with
the reason. It does **not** fall back to an uncontained subprocess, because the person who asked for
containment must be told, not quietly handed a leash.

Why construction and not call time: `09` §3's refuse-not-crash rule is about a *port* answering a
*call*. This is earlier — it is whether the component may claim what it claims in the catalogue at
all. A mode requiring containment reads that claim to decide what the model is shown (Phase 3), so
the claim has to be true before the first catalogue is computed, not discovered on the first call.

*Rejected:* trusting the backend name. It is what Phase 3 did, and Phase 3 said why it was a
stopgap.

*Rejected:* falling back to `contained=False` with a warning. A warning is a log line; a false
`contained` is a governance input. The two are not the same severity and must not be traded.

*Rejected:* a probe at every call. It costs a sandbox launch per step to re-learn a fact about the
machine, and a machine that loses its sandbox between two steps has bigger problems than this.

*Overturned by:* a backend whose proof cannot be observed from inside — a hardware enclave with no
attestation path, say. That backend would need an attestation port rather than a probe, which is
D22's kind of seam and its own decision.

## What is NOT in this phase

- **Sandbox escape testing against this host.** Forbidden by the loop's rules and not what a probe
  is: a probe proves the sandbox is *present*, not that it is *unbreakable*. That is the backend
  author's claim and the deployment's audit.
- **Resource limits beyond the timeout.** CPU, memory and disk caps belong to the backend's own
  configuration and are per deployment.

## Exit criteria

- A sandbox given a backend that proves itself registers `contained: true`, and one given a backend
  that cannot **refuses to construct**, naming why
- The subprocess sandbox from Phase 3 keeps working unchanged
- A run through the contained sandbox carries the proof on its provenance
- The gVisor and Firecracker backends exist as code with live tests, and the tests **skip here**
  rather than pass or fail — with the command that would run them recorded
