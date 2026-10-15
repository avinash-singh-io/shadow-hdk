# Phase 70 history

Append only. Entry types as phase 68's log sets out.

---

### [NOTE] 2026-10-16 — The debt this closes was recorded as it was created
Topics: lease, token-ceiling, context-window
Affects-phases: phase-70-the-token-ceiling
Affects-specs: none
Detail: Phase 65 made a thread carry its transcript between turns, and filed ENH-052 in the same
change — naming the risk at the moment it was introduced rather than leaving it to be discovered.
Three things existed that would have bounded it and none was wired: the compact meta-tool is enabled
by no shipped pattern, the lease caps steps and seconds and cents but not tokens, and there is no
per-fragment count. This phase does the first two. The third stays with H33.

---

### [ARCH_CHANGE] 2026-10-16 — A token ceiling on the lease
Topics: lease, token-ceiling, context-window, kernel-contract
Affects-phases: phase-70-the-token-ceiling
Affects-specs: specs/architecture/runtime.md#the-governed-step
Detail: `Ceiling` gains `max_tokens`, enforced inside the predicate that already stops a run out of
money rather than beside it, and reported by `remaining` so a product can see what is left. A
kernel contract addition: additive, a minor bump with a Pins row under D9.
Three decisions. **Unknown is unknown**: the meter already tracks when a provider reported nothing,
and a ceiling enforced through that would exhaust a run for arithmetic nobody did — worse than no
ceiling, since it stops work that was within budget. **A carve clamps rather than raises**, like the
clock and unlike money: a parent near its token limit would otherwise refuse every child for asking
a round number, which is BUG-022's shape, and nothing is lost because the parent's own meter counts
the child's tokens and its ceiling still stops the run. **Cache tokens count**, since D141's tokens
are tokens and a budget ignoring them would let a thread with a warm cache run past what its product
was charged for — the one mutation that survived the first pass, because the controls had only spent
input and output.

---
