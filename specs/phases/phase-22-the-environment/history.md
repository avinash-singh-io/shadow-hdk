---
type: History
phase: 22
---

# History — Phase 22, The environment

### [DECISION] 2026-09-11 — D48: an environment is where effects land, and it has a mode

Topics: environment, mode, isolation, bug-018
Affects-phases: phase-22-the-environment
Affects-specs: architecture/adapters.md#environment, architecture/runtime.md#modules

Three adapters each held an opinion about the same boundary and one lied (BUG-018). There is one
concept now: an **environment** with a **mode** — `read-only` · `workspace-write` · `full`, Codex's
three — and every operation in it (read, write, delete, list, run) gets its effect profile from
**one derivation**, `effects_of(isolation, mode, operation)`, and nowhere else.

Three parts, in this order: `Isolation` is what is *true* — writes confined, reads confined,
network denied, proven — set by a watched denial or an honest no, never by a wrapper's claim.
`Mode` is what is *wanted*. The derivation is over both, and the profile is true because the
environment makes it true; there is exactly one place to be wrong.

**A mode is enforced or refused.** A mode the isolation cannot make true raises `CannotEnforce` at
construction, naming the gap: a host that asked for confinement and cannot have it must know, not
find out. `full` asks for nothing and always works. A write in `read-only` is refused by the
environment itself before any policy is consulted — a mode is the environment's own promise.

The base lives in the runtime, below every adapter, the way the leash and the device contract do,
so a second environment never imports the first.

*Why:* BUG-018's class, closed by shape rather than by the invariant that caught it. *Overturned
by:* a fourth mode anyone can name that is not a refinement of these three.

---

### [DECISION] 2026-09-11 — D49: local execution is confined by the operating system, and proven first

Topics: environment, seatbelt, bubblewrap, d36, principle-5
Affects-phases: phase-22-the-environment

`LocalEnvironment` wraps every command in the OS sandbox — `sandbox-exec` on macOS, bubblewrap on
Linux — which is Codex's model, consumed rather than rebuilt (principle 5). Files go by path under
the root, confined by `inside()` as the workspace adapter did; commands go through the box, on the
runtime's leash, so a command is confined *and* on a timeout with a capped output and the
operator's environment withheld.

**Proven before it exists (D36).** A write outside the root is attempted and must fail; a socket
must fail; a write inside must succeed. What the environment declares is what the proof found.
A sandbox that claims to confine and does not — a broken install, a future macOS that ignores the
profile — is refused at construction; a test with a pretending sandbox holds that, because without
it a proof that returned `proven=True` unwatched would pass every other test.

Measured 2026-09-11 on macOS 26 with `sandbox-exec`, through the example on a real subscription:
`inside.txt: OK`; the write to `$HOME` — `PermissionError: [Errno 1] Operation not permitted` —
and the agent itself pointed out that `EPERM` rather than `EACCES` is the sandbox's signature.
Nothing escaped. Reads stay open on purpose — the interpreter has to read its own installation —
and the derived profile says `reads: everything` for exactly that reason.

*Why:* the OS already ships a sandbox; building another is the mistake principle 5 names.
*Overturned by:* Landlock as a Python binding, which would be a third `LocalSandbox` in this file
and no change anywhere else.

---

### [DECISION] 2026-09-11 — D50: an isolated environment sits behind a Box, proven by two denials

Topics: environment, opensandbox, backends, d36
Affects-phases: phase-22-the-environment

What this runtime needs from an isolation platform fits on a screen: open a **box** for a root and
a mode; run, read, write, delete, list in it; close it. `SandboxEnvironment` sits behind that seam
and everything about governance — mode, derivation, proof — is the same as for the local one.

**The proof grows a second denial.** Phase 11 proved a box by watching it refuse a socket. The
boundary BUG-018 was about is a write outside the root, so a box is proven only if it denies both.
A box that keeps the network out and lets a write escape the mount is the BUG-018 shape one level
up. Reads are taken as confined in a box — the process cannot see the host — which is the one
thing a box gives that the OS sandbox around a local process does not.

OpenSandbox is the first backend, chosen from the survey: self-hosts with Docker, four isolation
runtimes on a cluster, a Python SDK, MCP, Apache-2, CNCF. Translated and no more. It needs a
server and says so with the fix (D41); its live proof skips here. A refused environment closes its
box on the way out.

**The hand-rolled gVisor and Firecracker wrappers are deleted**, and with them the `trusting`
escape hatch Phase 11 kept for a backend that could not be tested: `requires` does not accept a
claim for a confined mode, and a deployment that wants to trust a box it cannot prove asks for
`full` and says so. E2B, Daytona and CubeSandbox (E2B-compatible) are the same seam, one adapter
each, and are the next files.

*Why:* consume the platform, keep the proof. *Overturned by:* a platform whose box cannot be asked
to attempt a write — which cannot be proven and is refused rather than trusted.

---

### [NOTE] 2026-09-11 — what the migration found in the record

Topics: documents, invariants
Affects-phases: phase-22-the-environment

Twenty-one landed phases still said `status: not-started` in their own frontmatter. The documents
invariant needed to know which phases are finished — their records are history, like the
changelog, and Phase 3's overview naming the adapters Phase 22 deleted is a true statement about
2026-09-10 — and could not tell. All corrected, and a rule holds each phase's frontmatter to
`status.md`'s Completed table.

The narrow-scope walk's anti-vacuity guard named `sandbox_subprocess`, which no longer exists; it
names `runtime:environment` now, where BUG-018's class lives, and its threshold dropped from four
to three because fewer places narrow a scope — which is what the phase was for.

---
