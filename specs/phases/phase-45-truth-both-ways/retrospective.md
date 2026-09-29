---
type: Retrospective
status: complete
---

# Phase 45 — truth both ways — Retrospective

> Six rows from a product's session, admitted under the substrate rule and built generically in
> one day; the first phase run explicitly under *the kit is a substrate*. v0.34.0.

## What was delivered

- **What a turn really cost** (ENH-023, D141): `Usage`/`Spent` cache read and write tokens; each
  dialect names its own fields in its file; LangChain's `input_token_details`; unknown never zero.
- **Why a turn really failed** (ENH-024, D139): `TurnRecord.failure`, `SessionGone` raised after
  the stream, the wire kind `session_gone` with both ids, the TypeScript client typed; how a CLI
  says it is `Dialect.session_gone_matches`, measured on both. Two defects underneath it closed:
  the JSONL session never read stderr (BUG-059) and a provider's failed turn was recorded
  `completed` (BUG-060).
- **A second CLI's behaviour** (ENH-028): `BehaviourArg.template`; `codex.toml` maps `model` and
  `effort`; measured live — the argv and `unmapped == ()`.
- **A host's words per turn** (ENH-037, D140): `turn(attributes=)` and `resume(attributes=)` on
  the thread, the wire and the client; BUG-061 closed on the way (an attribute named `mode`
  switched the policy).
- **A web read under the shipped modes** (ENH-038, D138): `ask` asks before an uncontained reach
  and an `allow` rule stands in — the served product's door; nothing re-vouched.
- **The Python matrix** (ENH-032, D132): CI on 3.12, 3.13 and 3.14; development on 3.14.
- **A provider is a file, by a test**: no vendor's name in the kernel's or the runtime's code.
- **Phase 36's owed half**: the planning proof passed live on Claude Code.
- Docs: the 0.34 migration note; the product doc's two-ports-one-surface statement and §2/§8/§9;
  the OpenAI-compatible endpoints table and the desktop example; the wire, modes and TS guides;
  the architecture synced.

## What went well

- **The admission rule did its job before a line was written.** ENH-039 stayed out; ENH-038 came
  in as a decision rather than the product's patch; ENH-037 came in because the runtime — not the
  product — could not say a fact learnt after open.
- **Measuring first paid twice.** The two CLIs were run on an unknown resume id *before* the plan
  was written; the measured texts became the provider-file values, and measuring Codex found
  BUG-059 (its sentence was on a pipe nobody read). Writing ENH-024's test then found BUG-060
  (nothing read `Turn.failed`). Writing ENH-037's reserved-name test found BUG-061. Three real
  defects, none of them the phase's subject, each caught by a test written for something else.
- **Vendor specifics stayed in files.** Every provider-facing change in this phase is a TOML value
  — `cache_read_tokens_at`, `session_gone_matches`, `failed_text_at`, a `behaviour_args` entry —
  and the new invariant now holds the runtime to that.
- **Four live proofs on the machine's own CLIs**, each recorded with its lines: Claude Code
  planning through the socket; Codex's argv; cache tokens on both; `session_gone` on both.

## What did not

- **D138's first draft narrowed `read-only`** on the argument that an uncontained reach is an
  egress channel. The suite said no within a minute (a `read-only` policy over a `full`
  environment offered nothing, because `contained` is the environment's property stamped on every
  operation), and the architecture's own modes table said `read-only` judges the web by design.
  Reverted before it was committed; D138 amended in the history. The lesson is written there: a
  decision from one file's evidence is checked against the architecture *before* the code moves.
- **CI on the release commit did not run**: every job ended in seconds with *"The job was not
  started because recent account payments have failed or your spending limit needs to be
  increased"* — the GitHub account's billing, not the tree. The previous commit (`aca389d`, the
  same code; the release commit changes versions and docs only) was green on all twelve jobs
  forty minutes earlier. The local gate on 3.14 and 3.12 stands in below; the publish workflow
  will not run either until billing is fixed — named at the gate.
- The docs commit swallowed the version bump once again and had to be split; a habit to fix.

## Lessons

- **A test written for one thing is the cheapest audit of its neighbours.** Three bugs in the
  failure and attribute paths had sat under passing suites because nothing asserted what those
  suites assumed.
- **Check a decision against the architecture before the code, not after the suite.**
- **`contained` is an environment property, not an effect's** — a pure read on a `full`
  environment is "uncontained". Any future decision on that axis has to be read against
  `effects_of` first.
- **The reserved-name set has two layers** (the step's keys and the conversation's); reserving
  the conversation's from the host closed a policy hole nobody had looked for.

## Carried forward

- ENH-039 — a `fetch` battery, now that `ask` has a door.
- ENH-035/036, TD-012/013, ENH-021 (the demo's re-pin, now to 0.34.0), ENH-033/034.
- Phase 34 → 37 (Epic 0009); 42 optional; 43 deferred.

## Verification Evidence

Captured 2026-09-20 on the release commit `3aec06d` (tree identical through the docs-sync commit
that follows), macOS 26, Python 3.14.6 (the development environment) and 3.12.13, Rust 1.98.1.
Exit codes read from each tool's own summary line.

### `uv sync --all-packages --all-extras` (the build command)

```
Installed 1 package in 0.99ms
 + shadow-hdk-linux-sandbox==0.34.0 (from file:///Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
1 file would be reformatted, 526 files already formatted   → docs/packages/adapters-langchain.md's code block; reformatted in the completion commit
Success: no issues found in 471 source files
```

### `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test` (in `native/sandbox`)

```
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.18s
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

### `npm run generate && npm run check && npm run build` (in `clients/typescript`)

```
wrote 28 contracts under …/clients/typescript/src/schemas and …/clients/typescript/src/schemas.ts
generated, checked, built   (no drift: git status clean under clients/typescript/src and schemas/)
```

### `uv run pytest` (the test command; the whole non-live suite, benchmark included) — 3.14

```
1846 passed, 20 skipped, 13 deselected, 85 warnings in 169.14s (0:02:49)
```

### `UV_PROJECT_ENVIRONMENT=.venv312 uv run --python 3.12 pytest` — 3.12

```
1846 passed, 20 skipped, 13 deselected, 86 warnings in 166.61s (0:02:46)
```

### `momentum okf check .`

```
✓ specs/ is an OKF v0.1 conformant bundle (214 markdown file(s))
```

### CI

```
aca389d (G4, the same code as the release commit; only versions and docs changed after it):
  success — https://github.com/avinash-singh-io/shadow-hdk/actions/runs/35469895427
  check (3.12) · check (3.13) · check (3.14) · bubblewrap · macos · native ·
  wheels (four platform wheels, the sdist, the installed x86_64 wheel confining): all success
3aec06d (the release commit): https://github.com/avinash-singh-io/shadow-hdk/actions/runs/35470259560
  every job "not started because recent account payments have failed or your spending limit
  needs to be increased" — the GitHub account's billing; zero steps ran. To re-run once billing
  is fixed: `gh run rerun 35470259560`.
```

### Live, on this machine's signed-in CLIs (recorded in `history.md`)

```
uv run pytest -m live tests/test_a_cli_plans_through_the_socket.py   → 1 passed in 8.57s (Claude Code 2.1.278)
codex 0.154.0, Behaviour(model="gpt-5.6-sol", effort="low"):
  argv … -m gpt-5.6-sol -c model_reasoning_effort="low"; unmapped=(); Usage(input_tokens=17393, output_tokens=5, cache_read_tokens=12032, cache_write_tokens=0)
claude-code 2.1.278: Usage(input_tokens=2, output_tokens=4, cost_cents=3, cache_read_tokens=531, cache_write_tokens=2458)
resume on an unknown id: codex failed=True session_gone=True · claude-code failed=True session_gone=True
```
