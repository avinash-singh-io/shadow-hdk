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

### [FEATURE] 2026-10-16 — Compaction fires on the ceiling, and a shipped pattern offers it
Topics: compaction, token-ceiling, patterns, context-window
Affects-phases: phase-70-the-token-ceiling
Affects-specs: specs/architecture/adapters.md#the-agent-adapter
Detail: The loop folds its own transcript when the token budget is nearly gone, **before** the
request is built, since afterwards there is no room left to send what the fold produced. The
threshold rides on the pattern beside the other sizes a product chooses, and defaults to never:
folding is lossy, and a kit doing it uninvited would discard a thread's past on a number nobody
picked. Never fired on an unknown count either, which is the same rule the ceiling itself follows.
H34 closed with it: `compact` was in no shipped pattern's meta tools, so the one way compaction
could ever happen was unavailable everywhere a product starts from. Offered now by `reflect-until`,
which is the pattern whose transcript actually grows — it iterates until satisfied — rather than
everywhere indiscriminately.
**The call site was written and left uncalled**, and every control passed because each invoked the
method directly. Third time in this release train: a wait in 0.48.0, a hand-over in 0.49.0, and this.
The control that catches it reads the turn loop's own source, because a control that calls the method
cannot tell the difference. Five mutations bite.

---
