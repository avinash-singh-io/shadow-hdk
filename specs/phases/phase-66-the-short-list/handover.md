---
type: Handover
phase: phase-66-the-short-list
written: 2026-10-03
---

# Handover — phase 66, the short list

Written for whoever picks this up next (the hand-off is to Codex). Everything here is checkable in
the repository; nothing relies on a session transcript.

## Start here

```bash
cd /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk
git checkout phase-66-the-short-list     # clean, pushed to origin; see `git log` for the head
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q
```

That gate was green when this was written: ruff 0, format 0, mypy strict 0 over 511 source files,
**2200 passed, 20 skipped**. If it is not green for you, that is the first thing to fix and it is
not something this phase left behind knowingly.

**Nothing is owed.** Before this was written the phase's tracking was audited and three debts
cleared: the changelog had no line for six commits of work (Rule 2), H11-A's defect was filed as
BUG-236 after its fix rather than when found (Rule 3, and the row says so), and
`what-moves-to-shadow.md` did not carry this phase's own contracts — which would have meant handing
over a file violating the decision stated inside it. See the last `[NOTE]` in
[`history.md`](history.md).

Read, in this order: `specs/status.md` (Rule 1), this phase's
[`overview.md`](overview.md) and [`tasks.md`](tasks.md), then
[`evidence/g2-h11-gaps.md`](evidence/g2-h11-gaps.md) — that last one is the design for everything
still to do and it was already agreed by lane P and the owner.

**Released state:** `main` is v0.44.0, published. This branch is unreleased work toward **0.45.x**.
`pyproject.toml` still says `0.44.0`; the version bump belongs to G7.

## The scope, and who set it

The owner's decision of 2026-10-03, after lane P's cross-repo plan: **HDK takes six items and then
goes to maintenance only** (bugs and the product's pins). Lane P coordinates directly.

**Do not build any of H12–H17, H21, H22, H29, H30 or H41–H43.** Those belong to Shadow. They are
named in the overview's *Out* so nobody reads their absence as an oversight. If something seems to
need them, that is a signal to stop and ask, not to extend scope.

Two standing constraints from the owner: **prefer open-source software where it does the job, and
follow open standards rather than inventing a format.** This kit already does where it matters —
MCP for tools, ACP for editors, `SKILL.md` and `AGENTS.md` for instructions, OpenTelemetry's GenAI
conventions, unified diff (stdlib `difflib`) for changes. Keep it that way.

## Done (6 commits, all gated)

| | what | decisions |
|---|---|---|
| G1 | **H10** — [`specs/planning/what-moves-to-shadow.md`](/planning/what-moves-to-shadow.md), revised once from Shadow's own row-by-row answer | D184 |
| G2 | **H11 confirmed** — the gap list, reported before building | — |
| G3 | **H20** — host-set diff cap, and a governed door to fetch a cut diff whole | D185, D186 |
| G4 | **H23** — a governed Codex carries only what it was given | D187 |
| G5-A | the agent name resolved on **every** path, and a dropped agent named | — |
| G5-B | the agent's role and tool list composed into a CLI's behaviour | D188 |

## Next: G5-E, then C, then D

The order is lane P's and the owner's. The design below is from G2 and is **already approved** — build
it, do not redesign it.

### E — `skill` on the agent row

`ModelAgent(..., skill=...)` already exists and `AgentSession` reads `self.agent.skill`, checking its
declared needs **before the first turn** (D17, BUG-012). So the runtime supports an agent bound to a
skill; what is missing is that a *stored row* cannot name one.

- Add an optional `skill` (a name) to `Pattern` and to `loader.KEYS`.
- Resolve it against the skill registry when the agent is built, **with the same refusal-by-name as
  an unknown agent** (D176's cut: name it, and say what there is).
- **Open question to settle before building:** the audit says a CLI gets *"its own skills only"*. So
  decide whether a row's `skill` applies on a CLI path at all, and write the answer down. If it does
  not, `Carried` is the place to say so. Ask lane P if it is not obvious from their use.

### C — `plan` on the agent row

`Pattern.plan` (`PlanLimits`) exists and `loader.KEYS` excludes it, so H11's "sub-agent limits" cannot
be set as data. Add `plan` to `KEYS` with parsing (there is a `load(json.dumps(...), PlanLimits)`
pattern beside `ceiling` already).

**Do not** add `absorb` or `offload_over` by symmetry. G2's recommendation, approved: they are
loop-tuning knobs nobody has asked for. Say so rather than adding them.

### D — `description` on the agent row

`agents/list` returns a `description` derived from `system` — a test pins
`reviewer["description"].startswith("REVIEWER-ROLE")` — so a product showing a person an agent
chooser shows the opening of a prompt written for a model. Add one optional `description` field,
**falling back to today's derivation when absent** so nothing that works changes.

### F — not built, deliberately

`model` and `effort` stay on the mode. G2 recommended against moving them; lane P and the owner
agreed. The product composes a mode from the agent's default and the conversation's choice through
its own port. **If asked to revisit, read G2's section F first** — the reasons are two sources of
truth for one field, and a stored row being able to change what a run bills without passing the
governed door.

## Then G6 — H6, H7, H8

**Confirm against the source and report before fixing. This is not optional ceremony.** Of phase 65's
five items, three needed a different fix than the audit assumed; of H11's six, two were already
partly built; and H23 closed by reading `--help` rather than building anything. An hour of reading has
changed the shape of the work every single time.

The audit's claims, unverified by anyone here:

- **H6** — fragments in a mode document crash the assembler; the wire has no path for them.
- **H7** — Claude Code's record claims a native interrupt but sets no interrupt line, so the session
  is closed instead.
- **H8** — the model adapter reports cache tokens and the key-backed loop drops them.

Write the confirmation into `evidence/`, as G2 did, and report it before building.

## Then G7 — the release

1. The release's migration note, as `0.45.md` under `docs/migrations/` (named in prose
   because the invariant below reads a path-shaped string as a file that must exist).
2. Version to `0.45.0` in **four** places: `pyproject.toml` (twice — the version and the
   `shadow-hdk-linux-sandbox==` pin), `native/sandbox/Cargo.toml`, `native/sandbox/pyproject.toml`.
   `tests/test_versions.py::EXPECTED` must match and carries the release's summary prose.
3. `specs/changelog/2026-10.md`, `specs/status.md`, this phase's `history.md`, and a
   `retrospective.md` with a non-empty `## Verification Evidence` section — **the release-tag hook
   refuses a tag without one**.
4. **Update [`what-moves-to-shadow.md`](/planning/what-moves-to-shadow.md)** with anything you add.
   It already carries G1–G5B's contracts under *Added by phase 66*, including the row for **E, C and
   D that says you update it**. D184 makes this a standing requirement of every bridge phase, and
   seven phases skipping it is why H10 existed at all.
5. The reply to lane P in `specs/epics/` (the previous one is `0011-reply-to-lane-p-2.md`).
6. Full gate green, **output read from a file**.

**Only the owner can land it.** `staging` and `main` are protected: the `pre-push` hook needs the
single-use `.momentum/merge-approved` sentinel, and this session was repeatedly refused permission to
create one. Prepare everything, verify the trees are identical, and hand the owner these three:

```bash
touch .momentum/merge-approved && git push origin staging
touch .momentum/merge-approved && git push origin main
git push origin v0.45.0
```

Then cut a **GitHub Release** — `publish.yml` fires on `release: [published]`, *not* on the tag push —
and verify from a clean virtualenv outside CI. Both distributions, **7 files total**. The PyPI JSON
API lags behind a publish; a fresh install resolving is what settles it.

## Traps this phase and the last one hit

- **TD-019 — a failing test that stands up a `ServeHost` hangs** rather than failing. It cost real
  time twice. Extract the decision into a pure function, mutation-check that, and keep the host test
  as behavioural coverage. Every group here did it that way.
- **TD-018 — a wall-clock margin is something a loaded machine can eat.** My own silence test flaked
  **four times**, and widening its margin twice did not fix it. The pattern, now recorded: *where a
  property is countable, count it* (`JsonlSession.rearmed`); keep at most one wall-clock test with a
  margin no load can plausibly eat, and accept that it is slow.
- **D14 — growing a port must break no adapter.** Widening the agent chooser's return broke four
  doubles this phase; phase 64 broke twenty-two the same way. Read a new element where it is offered
  and default it where it is not.
- **Three invariants will catch you, and they are right.** A D-number must be in
  `specs/decisions/index.md` **and** stated in the document the index points at. A new public
  `Thread` property must be accounted for in `tests/invariants/test_the_wire_is_at_parity.py`. And
  `test_no_document_names_a_path_that_is_not_there` reads any path-shaped string as a local path —
  name a sibling repository's file in prose, not as a path.
- **Never read `pytest` through `tail`.** It swallows the exit code; a run once reported `exit=0` over
  two failures. Redirect to a file and read both the code and the content.
- **Backticks in a `git commit -m` get shell-expanded.** Two words vanished from a commit message
  here. Write the message to a file and use `-F`.
- **Scoped test runs per group, the full suite before the release gate and after core changes.** The
  full suite is ~3½ minutes; a scoped run is seconds and caught two real failures a full run would
  not have caught any better.

## Tools now in the repository

- `scripts/mutate-one.py` — one anchored mutation, a test selection, restore. **Exits non-zero on a
  missing or ambiguous anchor**, which is the property phase 64's three bad passes lacked. `BITES`
  good; `*** SURVIVED ***` means the assertion does not bite — and if the mutant is *equivalent*,
  delete the code rather than invent a test that cannot tell the difference. Three equivalent mutants
  were resolved that way this phase.
- `scripts/reflow-long-lines.py` — re-wraps over-long prose from ruff's own E501 output.

## Waiting on other people

- **The owner:** the protected pushes for 0.45.x; the HDK support window after the switch (lane P has
  put it as a decision: rollback for one release, then retire); **D-M** — who builds the five
  file-and-shell tools, Shadow's phase 59 or the product's adapter; **D-N** — whether Shadow adds a
  Proposal port.
- **Lane P:** a ChatGPT or OpenAI account on which Codex accepts a model. That closes **TD-020** /
  H37 — the one Wave 1 item that could not be closed here. The two live tests in
  `tests/test_instructions_reach_a_live_model.py` skip with a message naming exactly what they need.
  The Claude Code half of that measurement passes live, so the mechanism is proven; the provider it
  exists for is not.
- **Lane P expects** a short note when 0.45.x is ready to publish, and whenever
  `what-moves-to-shadow.md` changes.
