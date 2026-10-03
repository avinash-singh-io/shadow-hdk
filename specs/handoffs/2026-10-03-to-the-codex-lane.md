---
type: Handoff
to: the Codex lane
from: the Claude session that built phases 65 and 66
date: 2026-10-03
---

# Handoff — shadow-hdk, from cold

You own HDK's work from here. Two jobs, in this order: **0.44.1 first**, because a product release is
blocked on it, then **0.45.x**, which is half built on a branch.

Everything here is checkable in the repository. Nothing depends on a conversation.

## Orient first (Rule 1)

```bash
cd /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk
cat specs/status.md                      # always first
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q
```

Released: **v0.44.0** (`ff1a877`), published to PyPI — `shadow-hdk` and
`shadow-hdk-linux-sandbox`, 7 files between them.
In flight: branch `phase-66-the-short-list`, pushed, clean, ahead of `main`.

Read `CLAUDE.md` and `specs/project-rules.md` before writing anything. The rules that actually bite
are listed under *Traps* below.

---

# JOB 1 — BUG-237, released as 0.44.1

**A product release is blocked on this. It is the first thing you do.**

**Branch from the `v0.44.0` tag, not from `phase-66-the-short-list`.** 0.44.1 must carry nothing from
0.45.x.

```bash
git checkout -b fix/BUG-237-postgres-ddl-at-runtime v0.44.0
```

## The defect, confirmed against the source

`Pooled.pool()` in `src/shadow_hdk/adapters/postgres/connection.py` executes its schema on first use
**and again after every `aclose()`**, because `aclose` sets `_ready = False`. A restricted runtime
role with no DDL rights fails with SQLSTATE 42501. Four adapters are affected:

| adapter | tables |
|---|---|
| `postgres/store.py` | `shadow_hdk_rows`, `shadow_hdk_versions` |
| `postgres/threads.py` | `shadow_hdk_threads`, `shadow_hdk_holds` |
| `postgres/effects.py` | `shadow_hdk_effect_journal` |
| `postgres/checkpoints.py` | LangGraph's four, via `AsyncPostgresSaver.setup()` |

**The thing not to get wrong:** `CREATE TABLE IF NOT EXISTS` is **not** DDL-free. PostgreSQL checks
the CREATE privilege on the schema *before* it checks whether the table exists, so the statement
fails against a table that is already there. That is why lane P's pre-provisioning did not help, and
it means the fix cannot be *make the DDL conditional* — it must be **do not execute the schema at
runtime at all**.

**And `shadow_hdk_versions` is not a schema version.** It is a data table holding a per-collection
row version for the store's optimistic concurrency. The kit has no schema version anywhere, which is
why item 2 below exists.

## What to build — all of this was agreed with lane P

1. **A trusted `prepare`** — a function and a CLI entry point. Idempotent. Run by the host's
   migration step under an **owner** role, before the app starts. It creates every table, index and
   extension the PostgreSQL adapters use **and calls LangGraph's `AsyncPostgresSaver.setup()`**,
   because that is third-party and cannot be made DDL-free from here.
2. **A one-row schema-version table**, written by `prepare` with the version it applied. Without it
   *"migrates"* has nothing to migrate from and *"behind"* has nothing to compare against — shipping
   either as a claim with nothing behind it is the category of defect phases 65 and 66 existed to
   remove. With it, *migrate* honestly means create-if-absent plus a recorded version, and real
   migrations become possible later rather than claimed now.
3. **A DDL-free runtime path, opt-in in 0.44.1** — a flag or a separate constructor. It executes no
   schema. **`aclose()` must not re-arm the schema execution on reopen**; that reopen path is the
   half lane P actually measured, and it is easy to fix the first-use path and miss it. Today's
   self-preparing behaviour stays the **default** in 0.44.1: a patch release must not invert
   behaviour for users who are not lane P, and lane P opts in explicitly. **The default flips to
   DDL-free in 0.45.0**, with the named behaviour change in that release's notes.
4. **A schema check per adapter open** — one catalogue query, no DDL. It fails with a **clear named
   error** when the schema is **missing** *or* **behind**, rather than attempting DDL.
5. **A runtime-grants manifest**, as data a host can read and not prose alone: the ten tables, their
   sequences and privileges — with **SELECT only** on the schema-version table.
6. **A two-role test in CI on `postgres:16`** (already in `.github/workflows/ci.yml`; the URL comes
   from `SHADOW_HDK_TEST_POSTGRES_URL`). Prepare as an owner role, then exercise every adapter's
   **open, reopen and ordinary operations** as a role holding only the manifest's grants. **The
   reopen leg is the one that would have caught this**, so do not leave it out.
7. **The migration note** (`0.44.1` under `docs/migrations/`) must say three things in as many words,
   because lane P asked for each: `prepare` is **not optional even on an already-provisioned
   database**; it is **re-run on every HDK *or LangGraph* upgrade**, not only ours; and **"behind"
   fails named at startup**.

`specs/backlog/backlog.md`'s **BUG-237** row carries all of the above plus the confirmation detail.
It is the spec; this section is its summary.

## Then

Write the ready-to-publish note for lane P (see *Reaching lane P*), and the owner runs the two pushes
and the release. See *Releasing* below.

---

# JOB 2 — 0.45.x, half built

Branch `phase-66-the-short-list`. Its own
[`handover.md`](/phases/phase-66-the-short-list/handover.md) is the detailed version of this section —
read it. Short form:

**Done, gated:** H10 (D184), H11 confirmed, H20 (D185/D186), H23 (D187), H11-A, H11-B (D188, at
`731ad85`).

**To do, in this order** — the design for each is already approved in
[`evidence/g2-h11-gaps.md`](/phases/phase-66-the-short-list/evidence/g2-h11-gaps.md), so build it
rather than redesign it:

- **E** — `skill` on the agent row. One open question in the handover to settle first.
- **C** — `plan` on the agent row (add to `loader.KEYS` with parsing). **Do not** add `absorb` or
  `offload_over` by symmetry.
- **D** — `description` on the agent row, falling back to today's derivation from `system`.
- **H6, H7, H8** — **confirm each against the source and report before fixing.** Of phase 65's five
  items three needed a different fix than the audit assumed; of H11's six, two were already partly
  built; H23 closed by reading `--help`. An hour of reading has changed the shape of the work every
  single time. Write the confirmation into `evidence/` as G2 did.
- **F is deliberately not built.** `model` and `effort` stay on the mode. If asked to revisit, read
  G2's section F first.

**Three things Intent Studio needs told, in the 0.45.0 migration note:**

1. **`tools_offered` now refuses a name nothing answers to.** It used to parse and do nothing, so a
   stale or misspelled name was harmless; it now refuses the turn. Any mode document setting it needs
   its names checked before pinning.
2. **Set `model` explicitly on Codex modes.** `--ignore-user-config` drops the whole user config, so
   a governed run whose mode names no `model` gets the CLI's built-in default rather than the
   person's.
3. **`agent_unhonoured`** is a new field on the thread, the record and `thread/start`'s reply. Exactly
   one of it and `agent` is ever set. Where a product shows which agent is running, this is the
   difference between *no agent* and *you asked for one and this provider cannot run it*.

---

# Standing rules

These are the owner's, relayed through lane P on 2026-10-03. Treat them as settled and do not
re-open them from inside this repository.

- **HDK is maintenance only** — bugs and the product's pins. Lane P records this as their roadmap's
  **D-D**. A short list was agreed (H10, H11, H20, H23, H6–H8) and after it there is no new
  capability work here.
- **Nothing from Shadow's capability map gets built in HDK.** Named so absence does not read as
  oversight: **H12–H17, H21, H22, H29, H30, H41–H43**. If something seems to need one, stop and ask —
  that is a signal, not a licence to extend scope.
- **HDK is Intent Studio's rollback for one release after the switch to Shadow, then retires** once
  Shadow runs on Windows. (Relayed; the Windows condition is lane P's wording and this repository has
  no independent record of it.)
- **Prefer open-source software where it does the job, and follow open standards rather than
  inventing a format.** This kit already does where it matters: MCP for tools, ACP for editors,
  `SKILL.md` and `AGENTS.md` for instructions, OpenTelemetry's GenAI conventions, unified diff from
  the standard library's `difflib`.
- **D184 is a standing requirement.** Every bridge phase adds its contracts to
  [`what-moves-to-shadow.md`](/planning/what-moves-to-shadow.md) **before closing**. Seven phases
  skipping that is why H10 existed; phase 66 nearly shipped the same omission and it was caught in a
  pre-handover audit.

---

# Reaching lane P

**You cannot message other sessions, and they know.** So:

- **Status goes in `specs/status.md`.** Keep it current; lane P reads it from git.
- **Replies and release notes go in `specs/epics/`**, as before — the last one is
  `0011-reply-to-lane-p-2.md`. Write the next as a new file, commit and push it.
- **They are waiting on two things specifically:** a note when a release is ready to publish, and a
  note whenever `what-moves-to-shadow.md` changes.

---

# Releasing

The mechanics, and the part that is not yours.

1. Version in **four** places: `pyproject.toml` (twice — the version, and the
   `shadow-hdk-linux-sandbox==` pin), `native/sandbox/Cargo.toml`,
   `native/sandbox/pyproject.toml`. `tests/test_versions.py::EXPECTED` must match and carries the
   release's summary prose.
2. The migration note under `docs/migrations/`, `specs/changelog/2026-10.md`, `specs/status.md`, the
   phase or ad-hoc record's `history.md`, and a `retrospective.md` with a **non-empty
   `## Verification Evidence`** section — **the release-tag hook refuses a tag without one.**
3. Full gate green, with the output **read from a file**.
4. **Only the owner can land it.** `staging` and `main` are protected: the `pre-push` hook needs the
   single-use `.momentum/merge-approved` sentinel, and an agent session here was repeatedly refused
   permission to create one. Prepare everything, verify the merged trees are identical to the gated
   one, then hand the owner:

```bash
touch .momentum/merge-approved && git push origin staging
touch .momentum/merge-approved && git push origin main
git push origin v0.44.1
```

5. Then a **GitHub Release** must be cut — `publish.yml` fires on `release: [published]`, **not** on
   the tag push. Verify afterwards from a clean virtualenv **outside CI**: both distributions,
   **7 files total**. The PyPI JSON API lags a publish, so a fresh install resolving is what settles
   it — this pair has shipped half-published before.

---

# Traps

Each of these cost real time in phases 65 or 66.

- **TD-019 — a failing test that stands up a `ServeHost` hangs** instead of failing. Extract the
  decision into a pure function, mutation-check that, keep the host test as behavioural coverage.
- **TD-018 — a wall-clock margin is something a loaded machine can eat.** One test flaked **four
  times**; widening its margin twice did not fix it. The pattern that did: **where a property is
  countable, count it.** Keep at most one wall-clock test, with a margin no load can plausibly eat.
- **D14 — growing a port must break no adapter.** Widening one callable's return broke four doubles
  in phase 66; phase 64 broke twenty-two the same way. Read a new element where it is offered and
  default it where it is not.
- **Three invariants will catch you, and they are right.** A D-number must be in
  `specs/decisions/index.md` **and** stated in the document the index points at. A new public
  `Thread` property must be accounted for in `tests/invariants/test_the_wire_is_at_parity.py`. And
  `test_no_document_names_a_path_that_is_not_there` reads any path-shaped string as a local file — so
  name a not-yet-written file, or a sibling repository's file, **in prose**.
- **Never read `pytest` through `tail`** — it swallows the exit code. A run once reported `exit=0`
  over two failures. Redirect to a file and read both.
- **Backticks in `git commit -m` are shell-expanded.** Two words vanished from a commit message in
  phase 66. Write the message to a file and use `-F`.
- **Regenerate the contracts after a kernel dataclass changes**:
  `uv run python -m shadow_hdk.wire.schemas` then `node clients/typescript/generate.mjs`, and check
  `git status` for drift.
- **Scoped test runs per group; the full suite before a release gate and after core changes.** The
  full suite is ~3½ minutes; a scoped run is seconds and has caught failures a full run would not
  have caught sooner.

# Tools in the repository

- `scripts/mutate-one.py` — one anchored mutation, a test selection, restore. **Exits non-zero on a
  missing or ambiguous anchor**, which is the property three earlier hand-rolled attempts lacked (one
  was vacuous and reported seven successes having mutated nothing). `BITES` is good;
  `*** SURVIVED ***` means the assertion does not bite — and if the mutant is *equivalent*, delete the
  code rather than invent a test that cannot tell the difference.
- `scripts/reflow-long-lines.py` — re-wraps over-long prose from ruff's own E501 output.

# Open, and not yours to decide

- **TD-020 / H37** — Codex's instruction fold has never been measured end to end; this machine's
  Codex refuses every model offered it. Needs an account where Codex accepts one. The two live tests
  in `tests/test_instructions_reach_a_live_model.py` skip with a message naming exactly what they
  need. The Claude Code half of that measurement passes live, so the mechanism is proven and the
  provider it exists for is not.
- **D-M** — who builds the five file-and-shell tools, Shadow's phase 59 or the product's own adapter.
- **D-N** — whether Shadow adds a Proposal port. `what-moves-to-shadow.md` records the recommendation
  to build it, with the reason: the gap is a governance boundary rather than a feature, and two
  Shadow phases would otherwise journal what a product expects to be proposed.
