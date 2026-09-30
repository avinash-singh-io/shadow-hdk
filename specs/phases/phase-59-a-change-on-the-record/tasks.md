---
type: Tasks
---

# Phase 59 — tasks

> `[ ]` not started · `[/]` in progress · `[x]` done, with fresh gate output (Rule 12)

## G1 — a write and a delete say what changed

- [x] RED: a `write_file` over an existing file carries a unified diff of the change
- [x] RED: a `write_file` creating a file is marked `created`, with the whole file as additions
- [x] RED: a `delete_file` carries what was removed, marked `deleted`
- [x] RED: added/removed line counts are exact
- [x] GREEN + mutation-check each assertion
- [x] the existing result keys (`path`, `bytes`, `deleted`) are untouched — asserted

## G2 — the same shape for an edit and a move

- [x] RED: `edit_file` carries the same `change` block as `write_file`
- [x] RED: a refused edit carries no change, because nothing was written
- [x] RED: `move_file` says what moved without claiming content changed
- [x] GREEN + mutation-check

## G3 — the cap is honest

- [x] RED: a diff past the cap is cut and says `truncated`, and the counts stay exact
- [x] RED: a binary or undecodable prior state is marked, not carried
- [x] RED: an unreadable prior state does not fail the write (D155)
- [x] RED: the cap is one named constant, not a number in three places
- [x] GREEN + mutation-check
- [x] measured: the change on the record agrees with what the filesystem holds

## G4 — a run's creations reach the product

- [x] RED: a host that passed its own sink gets the proposal and the kit's store stays empty
- [x] RED: a host that passed no sink still has a minted skill survive a restart (ENH-011 kept)
- [x] RED: `keep_proposals=True/False` force it either way
- [x] RED: a proposal of any kind reaches the host's sink, not only `kind == "skill"`
- [x] GREEN + mutation-check

## G5 — close out

- [x] `docs/migrations/0.38.md` — the addition, and D156's named behaviour change
- [x] version bump to 0.38.0 (the Linux helper in lockstep); no schema moved — the change rides
      the observation's own output, so `Provider.json` and the TS client were untouched
- [x] full gate green, output pasted into the phase history
- [x] `specs/status.md` row updated (own row only, Rule 15)
