---
type: Tasks
---

# Phase 59 — tasks

> `[ ]` not started · `[/]` in progress · `[x]` done, with fresh gate output (Rule 12)

## G1 — a write and a delete say what changed

- [ ] RED: a `write_file` over an existing file carries a unified diff of the change
- [ ] RED: a `write_file` creating a file is marked `created`, with the whole file as additions
- [ ] RED: a `delete_file` carries what was removed, marked `deleted`
- [ ] RED: added/removed line counts are exact
- [ ] GREEN + mutation-check each assertion
- [ ] the existing result keys (`path`, `bytes`, `deleted`) are untouched — asserted

## G2 — the same shape for an edit and a move

- [ ] RED: `edit_file` carries the same `change` block as `write_file`
- [ ] RED: a refused edit carries no change, because nothing was written
- [ ] RED: `move_file` says what moved without claiming content changed
- [ ] GREEN + mutation-check

## G3 — the cap is honest

- [ ] RED: a diff past the cap is cut and says `truncated`, and the counts stay exact
- [ ] RED: a binary or undecodable prior state is marked, not carried
- [ ] RED: an unreadable prior state does not fail the write (D155)
- [ ] RED: the cap is one named constant, not a number in three places
- [ ] GREEN + mutation-check
- [ ] measured: the change on the record agrees with what the filesystem holds

## G4 — a run's creations reach the product

- [ ] RED: a host that passed its own sink gets the proposal and the kit's store stays empty
- [ ] RED: a host that passed no sink still has a minted skill survive a restart (ENH-011 kept)
- [ ] RED: `keep_proposals=True/False` force it either way
- [ ] RED: a proposal of any kind reaches the host's sink, not only `kind == "skill"`
- [ ] GREEN + mutation-check

## G5 — close out

- [ ] `docs/migrations/0.38.md` — the addition, and D156's named behaviour change
- [ ] version bump to 0.38.0, schemas and the TypeScript client regenerated if the contract moved
- [ ] full gate green, output pasted into the phase history
- [ ] `specs/status.md` row updated (own row only, Rule 15)
