---
type: Ad-hoc Record
---
# ENH-041 — the read-class file tools: `glob`, `grep`, a ranged read

> **Type**: quick-task
> **Created**: 2026-09-30
> **Branch**: feat/ENH-041-the-read-class-tools
> **Backlog**: ENH-041
> **Status**: shipped — v0.35.0

Lane P's first pick from the desktop walk's item 4, taken as a quick-task because it is the
cheap half: three operations, no adapter changes, no kernel change, no new `Operation` kind.
The write-class half (ENH-042) stays a phase.

## Current Behavior

`runtime/environment.py::OPERATIONS` offered six operations, and a governed CLI runs with its own
built-ins off — so those six were the whole of what it could do. Two consequences lane P measured
inside the installed app:

- **Every search was a `run_shell`**, which under the shipped `ask` mode stops a person for
  approval. A search that asks permission is a search nobody runs, so the agent either reached for
  the shell and waited on a person, or did not search.
- **Every read of a large file arrived whole**, because `read_file` had no line range. The context
  floods, and the model has no way to ask for less.

The result was a governed Claude Code that is visibly weaker than the same CLI on its own — against
an owner's bar that says it should not be.

## Expected Behavior

- `glob(pattern, path?, limit?)` — files by path pattern, `**` crossing separators and `*` not,
  sorted, root-relative, files only; the pattern matched relative to `path`.
- `grep(pattern, path?, glob?, limit?)` — a regular expression over contents, each match
  `{"path", "line", "text"}` with a 1-based line; an unreadable file skipped rather than fatal; a
  bad pattern refused naming it.
- `read_file(path, offset?, limit?)` — `offset` the first line counting from 1, `limit` how many.
- All three **read-class**: `glob` derives from `list`, `grep` and `read_file` from `read`, so their
  profiles carry no writes, no reach and no cost, and `ask` does not stop them.
- Caps announced, never silent: over its limit `glob` returns
  `{"paths", "truncated": true, "found": N}` and `grep` `{"matches", "truncated": true}`.
- A range past the end **refused, naming the line count** — an empty string reads to a model as an
  empty file, and it stops looking.

## Unchanged Behavior

`read_file(path)` with no range is byte-for-byte the whole-file string it always was. No kernel
change: `Operation` is the same five literals, and `effects_of` is untouched — `glob` is a `list`
and `grep` is a `read`. **No adapter implements anything**: both are built on `_list` and `_read` in
the base, so a local directory, a sandbox and a remote root gain them together (an adapter with
something faster may override `_glob`/`_grep`; none has to). The six existing operations, the
read-only withholding of `write`/`delete`, protocol 3 and every port are unchanged.

## Verification Evidence

RED first (Rule 13): `tests/adapters/environment/test_the_read_class_tools.py` — **15 failed, 1
passed**, the one pass being the whole-file read that must not change. Green after: 16 passed.

The authoritative gate is **CI**, because this laptop could not give a clean one (see TD-015):
run `36683781588` on `feat/ENH-041-the-read-class-tools`, every job green —

```
macos · native (Landlock) · bubblewrap · check 3.12 · check 3.13 · check 3.14
wheels: x86_64/aarch64 × manylinux_2_17/musllinux_1_2 · sdist · installed
```

and run `36684850419` on `main` at the 0.35.0 bump, green after a re-run.

Locally: `ruff check` clean, `ruff format --check` clean over 533 files, `mypy` strict clean over
476 source files, and the new tests green.

**Stated honestly:** no local full-suite run of this change was clean. Four distinct
timing-sensitive tests failed across the runs — two on a laptop at load average 5–8 with
`syspolicyd` at 96% CPU, two on CI runners — each one green on a re-run of the same commit, and
none of them reachable from this change, which touches only the environment component. That is
filed as TD-015 rather than waved away: a suite whose red runs mean nothing is a suite with no gate.
