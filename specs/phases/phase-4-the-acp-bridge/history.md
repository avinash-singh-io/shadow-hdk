---
type: History
phase: 4-the-acp-bridge
---

# Phase 4 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 3
Topics: branches, chain

`phase-4-the-acp-bridge` is cut from `phase-3-workspace-and-code` at `13bc074`. The chain is
Phase 0 → 1 → 2 → 3 → 4; nothing merges until the owner lands it.

### [DECISION] 2026-09-10 — a child agent's request is judged, not answered
Topics: acp, governance, effects, bridge

The bridge could answer ACP's client calls itself — allow a `write_text_file` because it looks
harmless, run a `create_terminal` because the child asked nicely. It does not. **A child asking to
write a file or open a terminal is asking to do something our effect vocabulary already has words
for**, so each request becomes an `EffectProfile` and goes to the governance port, exactly like a
step of the runtime's own.

That makes the bridge a **governance surface with fourteen doors** rather than a wrapper around
`prompt`, and it means a mode written for the harness governs a child agent without knowing that
child exists. ACP's `ToolCallKind` maps onto the six fields; `other`, absent, and anything
unrecognised are `ASSUME_WORST` — the same rule Phase 1 applied to MCP annotations, which is the
rule that lets the registry stay open.
