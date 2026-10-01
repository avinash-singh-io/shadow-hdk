---
type: Phase
status: in-progress
epic: inner-loop-primitives
tags: [checkpoint, undo, restore, snapshot, git, worktree, isolation, port, lane-p]
deps: [phase-59-a-change-on-the-record]
---

# Phase 61 — undo, and an agent's own workspace

## Goal

Lane P's asks 3 and 7. *"Undo that turn"* is expected of a coding product — Claude Code has
`/rewind`, Codex has undo — and the kit checkpoints the **run** and the **record** while touching
the filesystem not at all. A thread rolled back to turn 3 faces a workspace still carrying turn 7's
files. And several agents working in parallel, each producing its own pull request, need somewhere
of their own to work.

Both are one mechanism: git, where a root is a work tree, which is what lane P narrowed the design
question to.

## Decisions — ADR territory

This phase adds a **port**, so project-rules requires an ADR, a minor bump, and a refuse-not-crash
default. These rows are that record.

| # | Decision | Rationale |
|---|---|---|
| D161 | **A new port, `WorkspaceHistoryPort`: `snapshot`, `restore`, `snapshots`.** Its default refuses rather than crashing | lane P asked whether the kit should ship one mechanism, a port with a git-backed adapter, or only a record of what would be restored. A port is the answer because *cheap where a root is a work tree and expensive where it is not* is exactly the shape a port exists for — a product on a remote or contained root supplies its own, and one on a repository gets git for free. The refuse-not-crash default is what every port default here is: an environment with no history says so, and nothing raises past `run()` |
| D162 | **When to snapshot is the product's, not the kit's.** `checkpoint` and `restore` are operations; nothing snapshots automatically | lane P described "a snapshot before a turn's first write", which is a *policy* — and the boundary rule puts policy on the other side of a port. The kit cannot know whether a turn deserves a checkpoint; a product (or the agent itself, before something risky) can. The mechanism is the kit's and the timing is theirs |
| D163 | **A restore derives as `delete`-class: irreversible, and `ask` stops a person before it** | restoring overwrites work that is on no snapshot, so `reversible=True` would be a claim the mechanism cannot keep. And an undo is precisely the act a person should be asked about — this is one of the few places where the conservative derivation is also the better product. An undo that bypassed governance would be the hole this phase exists not to open |
| D164 | **A snapshot holds what git would track. Ignored files are neither captured nor removed** | `node_modules` and `.venv` in a snapshot make it expensive enough that nobody takes one, which is the mechanism failing by being correct. So a snapshot is a tree of what git tracks plus what git would add, and a restore removes only files git does not ignore. Stated loudly in the migration note, because "my `.env` came back" and "my `node_modules` was deleted" are both surprises worth pre-empting |
| D165 | **The kit never touches the product's git state** — not HEAD, not a branch, not the index, not the stash | a snapshot is written through a temporary index to a commit object under `refs/shadow-hdk/snapshots/*`. A kit that left entries in `git stash list` or commits on the user's branch would be a kit a developer stops trusting with their repository, and rightly |

## Boundary and acceptance

**In:** the port and its git adapter; `checkpoint` and `restore` as governed operations;
`snapshots` for listing; a worktree-per-agent primitive on the **host** side.

**Out:** snapshotting ignored files (D164). A remote or contained history adapter — the port exists
so a product can write one. Automatic snapshots (D162). Restoring across repositories.

**Not an agent tool:** creating a worktree. An agent asking for its own isolated workspace is a
composition decision, so it is a host-side helper, not a registration in the agent's tool list.

## Groups

| | What | Asks |
|---|---|---|
| G1 | the port, and a git adapter that never touches the product's git state | 3 |
| G2 | `checkpoint` and `restore` as acts the mode judges | 3 |
| G3 | a worktree per agent, on the host side | 7 |
| G4 | the ADR, the migration note, the version, the gate | — |

## Verification

TDD strict, every assertion mutation-checked. Three properties measured rather than asserted about:

- **A restore actually restores** — file content, a file created since, and a file deleted since,
  all checked by reading the filesystem.
- **The product's git state is untouched** — `git status`, `git stash list`, `git rev-parse HEAD`
  and the branch list, compared before and after a snapshot and a restore (D165).
- **Ignored files survive a restore** — because D164 is the decision most likely to be got wrong,
  and getting it wrong deletes somebody's `node_modules` or resurrects their `.env`.
