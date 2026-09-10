---
type: Plan
phase: 20
---

# Plan — Phase 20, Providers

## The layering, and why there is a new package

```
kernel        AgentPort · Provider · ProviderStatus            pure types, no I/O
runtime       depends on kernel                                 the loop, the leash
providers     depends on kernel; discovers adapters at runtime  detection and selection
adapters/*    depend on kernel and runtime; import no sibling   the transports
provider TOML data; depends on nothing                          one file per provider
```

**The selection surface cannot import an adapter.** A module that opens either a `ModelPort` from
the LangChain adapter or an `AgentPort` from the ACP adapter would, written naively, import both —
and rule 4 of `tests/invariants/test_stands_alone.py` fails the build for it. That rule is an AST
walk over every `import` node in the file, so deferring the import inside a function does not evade
it and should not.

The answer is the one Python already has for dependency inversion: **entry points**. An adapter
*declares* itself in its own distribution metadata; `providers` looks the declaration up and loads
it by name. No adapter's name appears in `providers`' source, the arrow points from detail to
abstraction, and a third party can ship a provider adapter we have never heard of.

A host that would rather wire it by hand keeps that option — registering an implementation directly
is the escape hatch, and it is the same mechanism with the discovery step skipped.

**The rule gains a fifth clause**: `providers` imports no adapter, guarded the same way, with the
synthetic breaking case that keeps it from being vacuous.

## Group 1 — the abstraction (kernel; contract 0.13.1 → 0.14.0)

`AgentPort`, the second provider seam, under D22's open port set. A provider that owns its own loop:
open a session, take a turn, stream what happened, close. `AgentSession` is the resident handle —
the residency Phase 4 already argued for, lifted from one adapter into the contract.

The provider record itself is a **pure frozen dataclass in the kernel**, because it is data and the
kernel is where data with no I/O lives. It carries what must be measured rather than assumed:
identity, the binary and its fallbacks, the version probe, the auth probe and how to read its
answer, the environment to set, strip and backfill, the transport, and how our tools reach it.

`ProviderStatus` has **five** answers and none of them is a guess: `ready · absent · not-signed-in ·
too-old · unknown`. *Unknown* is not a failure state, it is honesty — some CLIs cannot be asked.

D14 applies to the new port exactly as it applied to `stream`: a method added later gets a
refuse-not-crash default, so growing this port breaks no adapter.

## Group 2 — discovery, and never a credential (`packages/providers`)

Everything here is a measurement, and each one is a lesson the reference paid for:

* **Resolution yields every candidate in order**, not the winner, because a wrapper left by a
  half-finished install cannot be told from a working CLI without spawning it.
* **The search path is `PATH` plus the user toolchain directories**, and the *spawn* path carries
  the same directories, or a binary resolves and then fails to execute because its interpreter is
  not where the child can see it.
* **A launcher that never reached its program is not a program that failed**, and the two get
  different remedies.
* **Authentication is asked, never read.** No credential is opened, stored, forwarded or logged. A
  provider is asked its own status question; the answer is matched against patterns *on the record*;
  anything unmatched is `unknown`.
* **Nothing is installed, ever.** An absent provider is reported with the command that would fix it.

Plus the TOML library loader, and the entry-point selection surface.

## Group 3 — the socket (`adapters/acp`, and the runtime's leash)

The invariant that makes an agent provider as governed as a model provider: **every effect routes
through the run's registry.**

* `session/new` carries the run's own registry as an MCP server — `RecordingServer` already exists
  and already routes a child's call back through the parent's run; nothing passes it today.
* The provider's native tools are refused, so ours are the only ones it has.
* **`create_terminal` is granted, backed by the runtime's leash.** It refuses outright today
  (`client.py:317`), which leaves an agent asked to run code either unable to, or running it
  unobserved in its own process.

Note what this does *not* require: the ACP adapter does not import the sandbox adapter. The leash
moved into the runtime in Phase 11 for exactly this reason, and the device contract followed it in
Phase 16. The socket closes without bending rule 4, which is a sign the layering was right.

## Group 4 — the library, as data

One TOML per provider, shipped the way patterns are (D17). Claude Code first, because it is the one
that can be measured here; Codex second, as the proof that the second provider costs a file. Every
field that encodes a quirk carries the measurement that found it, in the file, beside the field.

## Group 5 — proof against a real subscription

The end-to-end claim, run against a real CLI and a real subscription: a brief goes in, the provider
reasons, **our** tools act, our governance refuses what the mode forbids, our lease bounds it, and
the record shows every effect.

Marked `live` and deselected by default, like every other test that spends money or needs somebody
else's software — and it must **skip**, not fail, where the CLI is absent.
