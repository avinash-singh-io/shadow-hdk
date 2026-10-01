---
type: History
---

# Phase 62 — history

> Append-only. One entry per meaningful change, logged when the decision was fresh (Rule 8).

### [DISCOVERY] 2026-10-01 — BUG-229: a key-backed model was never instructed, and the thread said it was
Topics: behaviour, instructions, key-backed, unmapped, reporting
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: Found while planning ask 4's remainder, against lane P's sentence *"a key-backed model takes
instructions and skills directly."* It did not. `ModelSession.__init__` stored `behaviour` and
nothing read it, so a mode's `system`, `append_system`, `model`, `effort` and `temperature` all
vanished. Worse: `conversation.py:483` reads `unmapped` off the session by name, a `_ModelSession`
had no such attribute, so `thread.unmapped_behaviour` answered `()` — which a host reads as
*honoured in full*. Codex at least named what it dropped (ENH-020); this dropped silently **and
reported the opposite**, which is what makes it a defect rather than a gap. Filed P1 and fixed in
this phase.

---

### [DECISION] 2026-10-01 — one vocabulary for everything a run carries
Topics: context, fragments, behaviour
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: D166. A named `Fragment` (`name`, `text`, `source`) for a mode's instructions, a root's
`AGENTS.md`, a product's house style and a team convention alike. Four mechanisms for four kinds of
context would be four ways to be wrong, and a model that has learnt to read one block has learnt to
read all of them. Q1's bare `<instructions>` became one of these, which was the replacement Q1's own
record said to expect.

---

### [DECISION] 2026-10-01 — one assembler, for both provider kinds
Topics: context, fragments, cli, key-backed
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: D167. The two paths had already diverged — Q1 folded into a CLI's turn while a key-backed
model got nothing at all. One pure derivation (`carried_by` + `framed`) is what makes "identically
for a CLI and a key-backed model", lane P's own words, a property rather than an intention.

---

### [DECISION] 2026-10-01 — a mode's system layers on the pattern's, never replacing it
Topics: behaviour, pattern, key-backed
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: D168. `pattern.system` carries the loop's own mechanics — how to call a tool, when to stop —
so a `Behaviour.system` that replaced it would remove the instructions that make the loop work. A CLI
is the other case and keeps `--system-prompt`'s replacing semantics, because there the CLI owns its
own loop. Pinned by a test asserting the pattern's words come first.

---

### [DECISION] 2026-10-01 — a root's instruction files are a reader, not a default
Topics: agents-md, instructions, product-boundary
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: D169, ENH-047. The ENH-012 default stays: a governed CLI does not read a folder's
instruction files, because a run's instructions should be the mode's behaviour. What was missing is
that the kit never offered them either. `root_instructions` returns fragments a product composes, so
nothing is decided for anybody — which is what makes the convention refusable rather than obeyed.

---

### [DISCOVERY] 2026-10-01 — a live measurement found a bug every unit test missed
Topics: fragments, cli, verification
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: **The most useful thing that happened this phase.** `instructions_in_prompt` and *carries
fragments* were written as one gate, so Claude Code — which has `--system-prompt`, and therefore
does not fold — received **no fragments at all**. All fourteen unit tests passed, because every one
of them used a dialect that folds. The sentinel measurement caught it: Claude Code answered by
summarising its own system prompt with the offered fragment nowhere in it. They are two gates now —
instructions travel only where a CLI takes them that way and no flag delivers them; fragments travel
always, because no CLI has a flag for a product's named context. A test for a CLI that *has* the
flag was added. The general lesson matches Q1's: a green unit suite proves bytes reached a pipe.

---

### [EVALUATOR] 2026-10-01 — the sentinel, re-measured on the version lane P ships
Topics: measurement, claude-code, instructions
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: Lane P asked for this by name rather than accepting an inference across a CLI version gap,
and BUG-031 is why they were right to. Measured against **claude-code 2.1.284** (the original was
2.1.235, 2026-09-12): a sentinel `CLAUDE.md` in the workspace is still **not read** by a governed
Claude Code, and the same convention passed as a `Fragment` **is** followed. Both live tests, each
printing the version it measured — a measurement whose version nobody recorded is the thing BUG-031
was about. The pair matters: without the positive, the negative would also pass if the model simply
never answered the question.

---

### [NOTE] 2026-10-01 — not a YAML parser, deliberately
Topics: skills, markdown, parsing
Affects-phases: none
Affects-specs: docs/migrations/0.41.md
Detail: `SKILL.md` front matter in practice is flat `key: value` lines. Pulling a YAML dependency in
to read three of them is the same trade D158 refused for the patch format — a parser is a phase. A
file needing more is one a product reads itself, and the docstring says so rather than leaving the
limit to be discovered.

---

### [NOTE] 2026-10-01 — gate green
Topics: verification, release
Affects-phases: none
Affects-specs: specs/status.md
Detail: `ruff check` clean, `ruff format --check` 555 files, `mypy` strict 494 source files,
`pytest` **2011 passed, 20 skipped, 23 deselected**, exit code read directly. Phase 61 left it at
1986. Nineteen mutations bite. No published schema moved — `Behaviour` is referenced by `Provider`'s
contract but not embedded in it, so `fragments` changed nothing on the wire.

---
