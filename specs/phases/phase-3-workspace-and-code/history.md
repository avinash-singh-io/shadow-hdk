---
type: History
phase: 3-workspace-and-code
---

# Phase 3 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 2
Topics: branches, chain

`phase-3-workspace-and-code` is cut from `phase-2-the-spike` at `05000c2`. The chain is Phase 0 →
1 → 2 → 3; nothing merges until the owner lands it.

### [DECISION] 2026-09-10 — `contained` is a deployment fact with no default
Topics: sandbox, contained, effects, governance

`09` §5's third form of "program" is *code in a sandbox — present only on deployments that have
one, absent everywhere else*. The temptation is to make that a policy question answered per call.
It is not: it is a fact about the machine, stated once.

`SubprocessSandbox(root, *, contained, …)` therefore takes `contained` keyword-only **with no
default**, and carries it verbatim into the effect profile. A deployment with no real isolation
constructs it `contained=False`, a mode whose ceiling requires containment then refuses every
invocation, and the component is **absent from the catalogue** rather than refused at call time — so
the model never sees a tool it may not use.

Why no default: a sandbox that claimed containment it did not have would be the most dangerous lie
in this system. There is no safe value to guess, so it is not guessed.

**And the honest label:** a subprocess with a timeout is a *leash*, not a boundary. It stops a
runaway; it does not stop a determined program. That is why the default posture on a laptop is
`contained=False` and why Phase 11 exists.
