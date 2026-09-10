---
type: History
phase: 20
---

# History — Phase 20, Providers

### [DECISION] 2026-09-11 — D39: inference and agency are two seams, not one interface

Topics: providers, model-port, agent-port, subscription
Affects-phases: phase-20-providers
Affects-specs: architecture/overview.md

An API key sells **inference**: messages and tool schemas in, text and tool calls out, the caller
owning the loop. A subscription sells **an agent**: a prompt in, work done, a stream out, and it
owns its own loop, its own conversation and its own choice of tool. `ModelPort` is the first;
`AgentPort` is the second, under D22's open port set.

The tempting alternative was one interface with a CLI-backed `ModelPort` behind it. It cannot be
built honestly: extracting a single tool call from a coding CLI means defeating its own loop, and
none of them supports that. The reference implementation carries twenty-eight provider definitions
and no `complete(messages, tools) -> tool_calls` seam anywhere — not an oversight, a finding.

*Why:* one interface over two products would have to lie about one of them. *Overturned by:* a CLI
that grows a real single-step completion mode, which would make it an inference provider and it
would arrive at the first seam.

---

### [DECISION] 2026-09-11 — D40: a provider is data, like a pattern

Topics: providers, toml, d17
Affects-phases: phase-20-providers
Affects-specs: architecture/file-structure.md

D17 made agent architectures TOML a team writes without touching Python. A provider is the same kind
of fact — a binary, some probes, some environment rules, a transport — and is stored the same way.
Adding a CLI is adding a file; only a genuinely new transport costs an adapter.

This is taken from the reference **and corrected where it decayed**. Its provider record is data,
but two things leaked back into per-provider code: the spawn environment is a hand-written branch
per agent, and authentication failure is classified by a per-agent function matching English error
text. Both are fields on the record here. Every time provider knowledge leaks into a code path,
adding the next provider costs a phase again.

*Why:* the second provider must cost a file. *Overturned by:* a provider whose quirks genuinely
cannot be expressed as data — which would be evidence the record is missing a field, not that the
rule is wrong.

---

### [DECISION] 2026-09-11 — D41: the harness asks; it never reads a credential and never installs

Topics: providers, auth, subscription
Affects-phases: phase-20-providers

Authentication belongs to the CLI that already has it. This runtime asks a provider its own status
question and reads the answer. **No credential is opened, stored, forwarded or logged** — there is
nothing to leak because nothing is held.

The answer has five shapes and none is a guess: `ready · absent · not-signed-in · too-old ·
unknown`. *Unknown* is honesty, not failure — some CLIs cannot be asked, and a runtime that reported
*not signed in* because it could not tell would send people to fix what is not broken.

A provider that is absent is reported with the command that would fix it. Installing it is not this
library's business, on this machine or anyone's.

*Why:* the smallest credential surface is none. *Overturned by:* nothing foreseeable; a provider
needing us to hold a secret is a provider for the first seam, where the host holds it.

---

### [DECISION] 2026-09-11 — D42: the socket — every effect routes through the run's registry

Topics: providers, governance, injection, effects
Affects-phases: phase-20-providers
Affects-specs: architecture/overview.md

If a subscription-backed agent runs its own loop, what is left of governance? Everything that
matters, provided one invariant holds: **every effect routes through the run's component registry,
whoever decided to call it.**

For a model provider this is already true. For an agent provider it is made true by injection: the
provider is launched with the run's own registry as its tool source and its native tools refused, so
a file it writes, a command it runs and a claim it proposes all arrive as `Invoke` on our graph —
judged on effects rather than names, charged to the parent's lease, stamped with a posture, on the
event stream, and with the sink still deciding what is kept.

This is *govern effects, not names* raised one level: the harness does not govern a provider, it
governs the effects. It is also the difference between this and the reference, which injects tools
where this injects **governed** tools.

*Why:* it is the only claim that makes the two seams equally safe. *Overturned by:* a provider that
cannot be made to take injected tools, which cannot be governed here and must be refused rather
than admitted ungoverned.

---

### [DECISION] 2026-09-11 — D43: the loop stays theirs, and that is the price on the label

Topics: providers, patterns, subscription
Affects-phases: phase-20-providers

When a subscription drives, this runtime's patterns and compositions do not run. We own the tools,
the judgement, the lease and the record; the provider owns the reasoning.

Recorded as a decision rather than left as a gap, because it will be read as one. It is inherent:
you cannot buy an agent and also own its loop. A host that needs this runtime's loop uses
`ModelPort`, which is what it is for, and the choice between them is a real choice a host makes
rather than a limitation to be engineered away.

*Why:* naming the trade is what stops somebody spending a phase trying to have both. *Overturned
by:* nothing — this is a property of what a subscription sells.

---
