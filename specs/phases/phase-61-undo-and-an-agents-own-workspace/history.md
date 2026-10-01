---
type: History
---

# Phase 61 — history

> Append-only. One entry per meaningful change, logged when the decision was fresh (Rule 8).

### [DECISION] 2026-10-01 — a port, because the cost of a snapshot depends on the root
Topics: checkpoint, undo, port, git
Affects-phases: none
Affects-specs: docs/migrations/0.40.md, specs/architecture/adapters.md
Detail: D161. Lane P asked whether the kit should ship one mechanism, a port with a git-backed
adapter, or only a record of what would be restored. *Cheap where a root is a work tree and
expensive where it is not* is the shape a port exists for, so: `WorkspaceHistoryPort` with
`GitHistory` shipped, and a refuse-not-crash default. **On the ADR requirement** — project-rules
says a new port goes by ADR. This repository records decisions in `specs/decisions/index.md`
pointing at the document that declares them (its own note says the numbered ADR files are the
owner's and none is written); D161–D165 are recorded that way, which is the convention the
decisions-index invariant enforces.

---

### [DECISION] 2026-10-01 — when to snapshot is the product's, not the kit's
Topics: checkpoint, policy, product-boundary
Affects-phases: none
Affects-specs: docs/migrations/0.40.md
Detail: D162. Lane P described "a snapshot before a turn's first write", which is a policy — the
kit cannot know whether a turn deserves one. So a product's per-turn checkpoint goes through
`environment.history` directly, as its own act, judged by nobody; the agent's `checkpoint`
operation is judged like any act. This is also what makes automatic checkpointing viable: a
`write`-class act before every turn would ask a person every turn.

---

### [DECISION] 2026-10-01 — an undo is irreversible and `ask` stops a person before it
Topics: undo, restore, governance, effects
Affects-phases: none
Affects-specs: docs/migrations/0.40.md
Detail: D163. A restore overwrites work that may be on no snapshot, so `reversible=True` would be a
claim the mechanism cannot keep. Deriving it `delete`-class means the shipped `ask` mode stops a
person before an undo — one of the few places where the conservative derivation is also the better
product. "An undo that bypasses governance is a hole" was our own answer to lane P; this is it kept.
`checkpoint` derives `write` for the same honesty: it writes objects into the repository, and
calling it a read to spare a person the question is the under-claim `ASSUME_WORST` refuses.

---

### [DECISION] 2026-10-01 — a snapshot holds what git would track, in both directions
Topics: checkpoint, gitignore, cost
Affects-phases: none
Affects-specs: docs/migrations/0.40.md
Detail: D164. `node_modules` in a snapshot makes it expensive enough that nobody takes one — the
mechanism failing by being thorough. So `.gitignore` decides, and the consequence is honest both
ways with a test each: a restore does not delete an ignored file (an undo that ate `node_modules`
is an undo nobody dares use) and does not resurrect one either (bringing back a rotated `.env` is
its own bug).

---

### [DECISION] 2026-10-01 — the kit never touches the product's git state
Topics: git, trust, refs
Affects-phases: none
Affects-specs: docs/migrations/0.40.md
Detail: D165, and the constraint the adapter's whole shape follows from. A scratch `GIT_INDEX_FILE`
→ `write-tree` → `commit-tree` (parentless, so nothing walking commits mistakes it for project
history) → `update-ref refs/shadow-hdk/snapshots/*`. Never HEAD, a branch, the index or the stash.
A kit that left entries in `git stash list` is a kit a developer stops trusting with their
repository. Asserted by comparing HEAD, branch, branch list, stash list, staged names and log
before and after both a snapshot and a restore.

---

### [DISCOVERY] 2026-10-01 — git cannot order two snapshots taken in the same second
Topics: checkpoint, ordering, git
Affects-phases: none
Affects-specs: docs/migrations/0.40.md
Detail: Found by a test taking two snapshots in a row. A commit's date is second-resolution, so
`--sort=-creatordate` ties and "newest first" becomes whatever git felt like — and taking two
checkpoints within a second is exactly what a product checkpointing every turn does. The id now
carries the order (`<time_ns>-<random>`) and the listing sorts by name. Worth recording because the
first fix attempt was to trust the date sort, and the test that caught it would have passed by luck
on most runs.

---

### [NOTE] 2026-10-01 — two assertions were weaker than they looked, and the mutation pass said so
Topics: verification, tdd
Affects-phases: none
Affects-specs: none
Detail: Third time this epic. (1) `test_a_root_that_is_not_a_repository_refuses_rather_than_crashing`
accepted any message mentioning git, so deleting the guard still passed — a raw `git add` failure
refuses too, just uselessly. Now it asserts the guard's actual words, including that it names what
to supply instead. (2) `test_a_restore_is_withheld_in_a_read_only_environment` used a made-up
snapshot name, so it was refused for the wrong reason and passed with the mode guard deleted; it now
takes a real snapshot first, leaving the mode as the only thing that can refuse. The general lesson
is the same each time: a test that cannot say *why* it passed is not testing what its name claims.

---

### [NOTE] 2026-10-01 — G3's tests followed its implementation
Topics: tdd
Affects-phases: none
Affects-specs: none
Detail: Same honest deviation as phase 59's G2/G3 — the worktree module was written before its
tests, so all nine passed first run. RED-first held for G1 (no module) and G2 (three operations
absent). Five mutations carry G3.

---

### [NOTE] 2026-10-01 — gate green
Topics: verification, release
Affects-phases: none
Affects-specs: specs/status.md
Detail: `ruff check` clean, `ruff format --check` 550 files, `mypy` strict 490 source files,
`pytest` **1986 passed, 20 skipped, 21 deselected**, exit code read directly. Phase 60 left it at
1957. Eighteen mutations bite across the phase. Schemas and the TypeScript client regenerated with
no drift: `WorkspaceHistoryPort` is a Protocol, not a published contract, so nothing on the wire
moved.

---
