---
type: Phase
status: in-progress
epic: inner-loop-primitives
tags: [environment, patch, atomic, background, shell, process, leash, lane-p]
deps: [phase-59-a-change-on-the-record]
---

# Phase 60 — the write-class toolset completes

## Goal

The rest of ENH-042, which lane P confirmed both halves of: **a cross-file atomic patch**, because
refactors touch many files at once, and **a background shell**, because a developer runs a dev
server, a watcher or a long test suite while working — and Claude Code and Codex both have one.

The bar is theirs and it is the right one: *a governed CLI is not weaker than the same CLI on its
own.* Today it is.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D157 | **The environment owns a background job, and `close()` ends every one of them.** D35 — a step owns the process tree it starts — is kept, one level up | a background job outlives the step that started it by definition, so D35 cannot apply to it unchanged. But the principle behind D35 is that *nothing outlives the thing that owns it*, and the environment lives for the thread. This is exactly the reasoning BUG-019 used one level up for provider sessions: "a session the host holds across steps is the same obligation one level up". A job nobody owns is the ten-hour orphan BUG-019 found |
| D158 | **A patch is a list of `{path, edits}`, reusing `edit_file`'s vocabulary — not a diff format the kit parses** | `Dialect` already refuses to become a query language for the same reason: a patch format is a parser, and a parser is a phase. `{old, new}` is the vocabulary `edit_file` established, every refusal it already has carries over unchanged, and a model that can use one can use the other. Codex's own patch is diff-shaped, but the kit owes a product a *primitive*, and its primitive for "change this region" already exists |
| D159 | **Atomic means every file is validated before any file is written** | the record is the reason this is hard, not the edit. A patch that wrote three files and then refused the fourth would leave a workspace no record describes — the failure `edit_file` already refuses within one file, multiplied. So: read all, validate all, write all. Nothing is written until every edit in the batch is known to apply |
| D160 | **Status and output arrive together.** Three operations, not four: `run_background`, `job_output`, `kill_job` | lane P asked for "start, status, output, kill", and the field ships three — Claude Code's `Bash(run_in_background)`, `BashOutput`, `KillShell`. Polling twice to learn one thing is a turn a model wasted, so `job_output` carries `running` and `exit_code` beside the new output. A model's tool list is a cost too |

## Boundary and acceptance

**In:** `apply_patch`, `run_background`, `job_output`, `kill_job`. Each with a profile from the one
derivation, so every mode judges them as it judges the nine that exist. Every job ended when the
environment closes.

**Out:** a diff-format parser (D158). Scheduling, retries or job persistence across a restart — a
job is a process this environment started, not a durable record. Streaming output as an event: the
activity path already exists for a foreground run and extending it is not what lane P asked for.

**Unchanged:** `run_shell` behaves exactly as it does, including its leash and its timeout.
`edit_file` is untouched — `apply_patch` reuses its validation rather than replacing it. Protocol 3
unchanged; contract additions only, so a minor and a *Pins* row.

## Groups

| | What | Asks |
|---|---|---|
| G1 | a patch applies across files, or not at all | 2 |
| G2 | a background job starts, reports and is killed | 2 |
| G3 | no job outlives the environment that owns it (D157) | 2 |
| G4 | the migration note, the version, and the gate | — |

## Verification

TDD strict, every assertion mutation-checked. Beyond the gate, two properties this phase has to
measure rather than assert about itself:

- **Atomicity, from the filesystem.** A patch refused on its last file must leave every earlier
  file byte-for-byte as it was — checked by reading them, not by trusting the refusal.
- **No orphan.** After an environment closes, a job it started is gone — checked against the
  operating system, because BUG-019 found two children alive ten hours after their session ended
  and no test had noticed.
