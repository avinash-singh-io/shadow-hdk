---
type: History
phase: 2-the-spike
---

# Phase 2 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 1
Topics: branches, chain

`phase-2-the-spike` is cut from `phase-1-real-adapters` at `4d2a8dc`. Nothing merges, so the chain
of phase branches carries the code: Phase 0 → Phase 1 → Phase 2.

### [DECISION] 2026-09-10 — what this machine can measure, and what it will not do to measure more
Topics: acp, codex, claude-code, spike

Checked rather than assumed:

| | |
|---|---|
| `codex` | **not installed** |
| `claude` | **installed, 2.1.235** — but no native ACP mode; `--help` carries no `--acp`, no `--stdio` |
| Zed's `claude-code-acp` bridge | **not installed** (npm global is empty of it) |
| `zed` | not installed |
| `agent-client-protocol` (PyPI) | **0.12.1**, installed as a dev dependency for this spike |

Claude Code speaks ACP *through* the npm bridge, not natively. Making the implementation half of J1
answerable here would mean installing a global npm package on the owner's machine and then spending
their Claude subscription — two side effects, unasked, while they are asleep. Neither is this
session's to take.

So the spike answers what it honestly can — **the protocol** and **the transport** — and writes the
third part down as unmeasured with the command that would settle it. A spike that guesses is worse
than a spike that stops.
