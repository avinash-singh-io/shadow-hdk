---
type: Retrospective
status: complete
---

# Phase 59 — a change is legible on the record — Retrospective

> Lane P's asks 1 and 6, and Epic 0011's Q1 quick-task carried with it. v0.38.0.

## What was delivered

- **A change on the record** (ENH-044, D154): `write_file`, `edit_file` and `delete_file` carry a
  bounded unified diff — `truncated` when cut, exact `added`/`removed` counted over the whole diff
  *before* cutting, and `created`/`deleted`/`before_unreadable` markers. So a host shows what an
  agent changed without reading the environment's root, which raced the agent and could not work at
  all for a contained or remote environment.
- **Capturing it never fails the write** (D155): an unreadable prior state is marked, and the counts
  are `null` rather than `0` — unknown, never zero, the rule `Usage` keeps for cache tokens (D141).
- **`move_file` carries no change, deliberately**: no content delta, and `from`/`to` are the whole
  story. Pinned by a test, because "every write-class op carries a change" is the obvious
  generalisation and it is wrong here.
- **A run's creations reach the product** (D156, ask 6): the kit keeps proposals only when nobody
  else is listening — a host passing its own `sink=` gets them and the kit's store stays empty.
  `keep_proposals` forces either; nothing narrows to `kind == "skill"` any more.
- **Q1, carried here** (ENH-051): a CLI mapping no system-prompt flag is handed its instructions in
  the turn, framed, first turn only. `codex.toml` switches it on.

## What went well

- **No kernel change was needed and we proved it rather than assuming it.** The plan said to settle
  whether `EffectRecorded.detail` could carry this before writing code; it could, so no ADR, no new
  event field, and no published schema moved.
- **Lane P's own answer decided the design.** Their "content to a cap, `truncated` beyond it, no
  per-file history" settled the question ENH-044 had carried open, and a diff is what survives that
  cap usefully.
- **The property tested is agreement with the filesystem**, not with itself: the diff's own claims
  are replayed against the bytes on disk.

## What did not

- **G2 and G3 were not written RED first.** G1's implementation already covered them, so both went
  green on their first run. The mutation pass is what establishes those assertions can fail, and
  the ordering was a mistake rather than a shortcut worth keeping.
- **Two existing tests asserted a whole result dict**, so an addition broke a test about *roots*.
  Narrowed to what they are actually about.

## Verification Evidence

Captured 2026-10-01 on `staging` with phase 59 merged (the release tree for **v0.38.0**), macOS 26
(Darwin 27.0.0), Python 3.14.6. Exit codes read from each tool's own summary line, and `pytest`'s
read directly rather than through a pipe — the first run of this session showed why, when `tail`
swallowed a real failure and reported success.

### `uv sync --all-packages --all-extras` (the build command)

```
 + shadow-hdk==0.38.0 (from file:///Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk)
 + shadow-hdk-linux-sandbox==0.38.0 (from file:///…/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
542 files already formatted
Success: no issues found in 483 source files
```

### `uv run pytest`

```
1936 passed, 20 skipped, 21 deselected, 85 warnings in 172.93s (0:02:52)
pytest exit=0
```

The epic entered at 1897 passing; this phase adds 39 (25 its own, 14 Q1's).

### Mutation checks — sixteen, all biting

Every assertion was changed so it should fail, confirmed failing, and reverted (project-rules: an
assertion that cannot fail is deleted). Six in G1, six in G2/G3, four in G4. One needed retrying
against the right test: the first attempt mutated a branch that was dead code for the tests the
`-k` filter selected, which is its own small lesson about mutation passes.

### Live measurement (ENH-051, carried here)

```
uv run pytest tests/test_instructions_reach_a_live_model.py -m live -q
2 passed, 2 skipped in 15.43s
```

Passed on **claude-code 2.1.284** with `--system-prompt` removed from its record, so the fold was
the only way in, plus its paired negative. **Unmeasured and said so:** both Codex legs skip — a
ChatGPT-account `codex-cli 0.154.0` on this machine refuses every model tried, so the turn never
reached a model and nothing about the fold was measured there.
