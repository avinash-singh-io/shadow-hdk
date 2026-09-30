---
type: History
---

# Phase 59 — history

> Append-only. One entry per meaningful change, logged when the decision was fresh (Rule 8).

### [DECISION] 2026-10-01 — a change is a bounded diff, not before-and-after content
Topics: record, diff, write, cap
Affects-phases: phase-61-undo-and-an-agents-own-workspace
Affects-specs: docs/migrations/0.38.md
Detail: D154. Lane P settled the open question ENH-044 carried — content to a cap, `truncated`
past it, and no per-file version history because git keeps that for a repository. Given a cap, a
diff is what survives it usefully: before-and-after cut at 4 KB of a 1 MB file shows nothing of a
three-line change, while a diff of the same change shows all of it. The line counts are computed
over the whole diff *before* it is cut, so a truncated diff still reports the true size of what
happened.

---

### [DECISION] 2026-10-01 — capturing the change never fails the write
Topics: record, diff, write, failure
Affects-phases: none
Affects-specs: docs/migrations/0.38.md
Detail: D155. `_prior` swallows everything: a missing file is `existed=False`, and anything else —
a binary file, a denied read — comes back marked `before_unreadable` rather than raised. A write
that failed because the record-keeping failed would be the tail wagging the dog; the act the mode
admitted and the person approved still happens. `OutsideTheRoot` is swallowed here too and safely,
because `_prior` runs before the write and `_write` raises it a moment later, so the act is refused
by the handler that always refused it.

---

### [DECISION] 2026-10-01 — the kit keeps a run's proposals only when nobody else is listening
Topics: proposals, sink, keeping, product-boundary
Affects-phases: none
Affects-specs: docs/migrations/0.38.md
Detail: D156, lane P's ask 6. `KeepingSink` states the rule in its own docstring — *whoever holds
the sink decides* — and then the shipped composition decided for everyone, keeping a minted skill
as a `skills` row in the kit's store. That is the kit taking the product's decision. But never
keeping would re-break ENH-011: with no host sink, a store row is the only way a minted skill
survives a restart, and losing them was found by the demo. So `keep_proposals=None` (the default)
keeps only where no `sink=` was handed in, and `True`/`False` force it. A named behaviour change
for any host that passes a sink, which is why it is in the migration note rather than only here.

---

### [NOTE] 2026-10-01 — a move carries no change, and that is the decision
Topics: record, diff, move
Affects-phases: none
Affects-specs: docs/migrations/0.38.md
Detail: A move is the one write-class act with no content delta. `from`/`to` already say the whole
of what happened, and a zero diff beside them reads as *nothing happened* — so `move_file` carries
no `change` block and a mutation that gives it one fails a test. Pinned rather than left implicit,
because "every write-class operation carries a change" is the obvious generalisation and it is
wrong here.

---

### [NOTE] 2026-10-01 — G2 and G3 were not written RED first, and the mutation checks carry them
Topics: tdd, verification
Affects-phases: none
Affects-specs: none
Detail: Honest deviation from Rule 13. G1's implementation (the `changed` builder, the cap, and the
`_prior` capture) covered what G2 and G3 then tested, so both groups' tests went green on their
first run rather than failing first. The RED-first discipline was kept for G1 (`TypeError: no
change block`) and for G4 (`keep_proposals` absent, and the kit keeping regardless). For G2 and G3
the evidence that the assertions can fail is the six mutations below, each of which bites. Worth
recording rather than papering over: the ordering was a mistake, and the mutation pass is what
makes the tests worth having anyway.

---

### [DISCOVERY] 2026-10-01 — two existing tests asserted the whole result dict
Topics: record, tests
Affects-phases: none
Affects-specs: none
Detail: `test_a_relative_root_is_resolved_before_the_proof` compared a `write_file` observation to
a whole `Completed({...})`, so an addition to the result broke a test about *roots*. Narrowed to
the keys it is actually about, plus an assertion that the bytes landed under the right root — which
is what it meant to check. The same shape in `test_a_behaviour_becomes_flags.py` was updated during
Q1. No backlog item: two instances is not yet a class, but a third would be.

---

### [EVALUATOR] 2026-10-01 — the property is agreement with the filesystem, not with itself
Topics: record, diff, verification
Affects-phases: none
Affects-specs: none
Detail: `test_the_change_agrees_with_what_the_filesystem_actually_holds` replays the diff's own
claims against the bytes on disk — every `+` line must be in the file and every `-` line must not.
A record agreeing with itself proves nothing, which is the failure mode a diff test falls into by
default.

---

### [NOTE] 2026-10-01 — gate green, and the numbers
Topics: verification, release
Affects-phases: none
Affects-specs: specs/status.md
Detail: `ruff check` clean, `ruff format --check` 542 files, `mypy` strict 483 source files,
`pytest` **1936 passed, 20 skipped, 21 deselected** (exit code read directly, not through a pipe).
Baseline entering the epic was 1897; Q1 took it to 1911; this phase adds 25. Sixteen mutations bite
across the phase's four groups — six in G1, six in G2/G3, four in G4 (one of which needed retrying
against the right test: the first attempt mutated a branch that was dead code for the tests
selected, which is its own small lesson about `-k` filters in a mutation pass).

---
