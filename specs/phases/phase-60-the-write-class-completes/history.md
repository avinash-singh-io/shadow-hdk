---
type: History
---

# Phase 60 — history

> Append-only. One entry per meaningful change, logged when the decision was fresh (Rule 8).

### [DECISION] 2026-10-01 — the environment owns a background job, not the step
Topics: background, process, leash, ownership
Affects-phases: phase-61-undo-and-an-agents-own-workspace
Affects-specs: docs/migrations/0.39.md, specs/architecture/adapters.md
Detail: D157, and the decision the whole background half turned on. D35 says a step owns the
process tree it starts and nothing survives the step — `run_leashed` ends the group in a `finally`
precisely for that. A background job outlives its step by definition, so D35 cannot apply to it
unchanged. What carries over is the principle *nothing outlives the thing that owns it*, one level
up: the environment owns a job and `close()` ends every one. That is the same move BUG-019 forced
for provider sessions ("a session the host holds across steps is the same obligation one level
up"), and BUG-019 is what dropping it looks like — two children alive ten hours after their
sessions ended.

---

### [DECISION] 2026-10-01 — a patch is `{path, edits}`, not a diff format
Topics: patch, atomic, vocabulary
Affects-phases: none
Affects-specs: docs/migrations/0.39.md
Detail: D158. A diff format is a parser, and `Dialect`'s own docstring already refuses to become a
query language for the same reason. `{old, new}` is what `edit_file` established; reusing it means
every refusal a caller has already learnt carries over, and the validation is **literally the same
function** — `edited_by`, extracted so the two cannot drift. Codex's own patch is diff-shaped, but
what the kit owes a product is a primitive, and its primitive for *change this region* existed.

---

### [DECISION] 2026-10-01 — atomic means validate everything before writing anything
Topics: patch, atomic, record
Affects-phases: none
Affects-specs: docs/migrations/0.39.md
Detail: D159. Read all, validate all, write all. A patch that wrote three files and then refused
the fourth would leave a workspace no record describes — the failure `edit_file` already refuses
within one file, multiplied by the batch. Atomicity is the whole of what makes this different from
a loop, so it is the property the tests measure from the filesystem rather than trust from the
refusal.

---

### [DECISION] 2026-10-01 — three background operations, not four
Topics: background, tools, cost
Affects-phases: none
Affects-specs: docs/migrations/0.39.md
Detail: D160. Lane P asked for "start, status, output, kill" and the field ships three. `job_output`
carries `running` and `exit_code` beside the output, because polling twice to learn one thing is a
turn a model wasted, and a model's tool list is a cost too. The output is **new since the last
read** rather than the whole buffer: re-reading it on every poll bills a product for the same bytes
repeatedly, which on a long build is the cost they would actually feel. The trade is that
`job_output` is not idempotent, which the migration note says out loud.

---

### [DISCOVERY] 2026-10-01 — the background path's confinement was a docstring, not a test
Topics: background, confinement, sandbox, verification
Affects-phases: none
Affects-specs: docs/migrations/0.39.md
Detail: **Found by the mutation pass, not by design.** `_start_job`'s docstring claimed a job goes
through the same box as a foreground command "because a job that escaped confinement by being
long-lived would be a hole a mode never admitted" — and removing the wrap entirely broke **no
test**. The same was true of the narrow environment: handing a job `env=None` (the whole ambient
environment, credentials included) also broke nothing. Two tests added, one per property, and both
fail when their line is removed. Worth recording as a discovery rather than a note: the lesson is
that a safety claim written in prose beside code is not evidence, and the mutation pass is what
turns the difference up. No backlog item — the gap is closed — but it is the second time this epic
that a mutation found something a green suite did not.

---

### [NOTE] 2026-10-01 — no test here sleeps for a fixed time
Topics: background, tests, flakes
Affects-phases: none
Affects-specs: none
Detail: TD-015 closed four timing flakes in this suite and the fix was to wait for the condition
rather than the clock. A background-job test is the easiest place in the codebase to reintroduce
that, so every wait goes through one `until()` helper that polls a condition to a deadline and
fails naming what never happened. The `_alive` helper has its own test — a process killed with
SIGKILL must read as dead — because if `_alive` could never say no, every ownership assertion in
the file would pass for the wrong reason (BUG-007's shape).

---

### [NOTE] 2026-10-01 — `kill_job` asks under `ask`, deliberately
Topics: background, modes, governance
Affects-phases: none
Affects-specs: docs/migrations/0.39.md
Detail: `kill_job` derives as `run`, so the shipped `ask` mode stops a person before it. That may
annoy — the agent started the job, so killing it needs no wider clearance than starting it did —
but the derivation is per-operation and not per-history, and a kill is irreversible with side
effects (a killed process leaves partial state). A product that disagrees grants an `allow` rule,
which is the designed door and D138's precedent.

---

### [NOTE] 2026-10-01 — gate green
Topics: verification, release
Affects-phases: none
Affects-specs: specs/status.md
Detail: `ruff check` clean, `ruff format --check` 544 files, `mypy` strict 485 source files,
`pytest` **1957 passed, 20 skipped, 21 deselected**, exit code read directly. Phase 59 left it at
1936. Eleven mutations bite across the phase — four in G1, five in G2, two in G3 (the two that
found the untested confinement claims).

---
