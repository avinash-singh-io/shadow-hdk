---
type: Phase
status: in-progress
epic: inner-loop-primitives
tags: [record, diff, write, delete, edit, move, proposals, sink, keeping, lane-p]
deps: [phase-45-truth-both-ways]
---

# Phase 59 — a change is legible on the record

## Goal

A host can show **what an agent changed** without reading the disk behind the runtime's back, and a
run's creations reach the product that composes the kit rather than a store inside it.

Lane P's asks 1 and 7 of 2026-10-01 (ENH-044), and their ask 6 (the `KeepingSink` subtraction). Both
are the same complaint in two places: the record is a weaker account of the run than the filesystem
is, so a product has to go around it.

## Why now, and why first

`write_file` records `{"path", "bytes"}`; `delete_file` records the path; `EffectRecorded` carries a
digest and a free `detail`, and neither holds content. So a host showing a files-changed panel or an
approval preview must read the environment's root itself — which lane P does today
(`told.previews_from(self._root())`).

Three things are wrong with that, and only the first is cosmetic:

1. It races the agent — the disk has moved on by the time the host looks.
2. **It cannot work at all** for a contained or remote environment, where the host has no such
   access. That is the one that makes this a primitive and not a nicety.
3. It makes the record a weaker account of the run than the filesystem, which inverts the point of
   having a record.

And Phase 61 (checkpoints and undo) cannot be designed before this one: a snapshot has to know what
a change is, and the backlog records that dependency.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D154 | **A change is carried as a bounded unified diff, not as before-and-after content.** Exact added/removed line counts ride beside it and stay exact even when the diff is cut | lane P settled the open question — content to a cap, `truncated` past it, no per-file history because git keeps that. A diff is what survives the cap usefully: before/after truncated at 2 KB of a 1 MB file shows nothing, while a diff of the same change shows all of it. Standard, compact, and lossless for the text this surface already deals in |
| D155 | **Capturing the change must never fail the write.** An unreadable prior state (binary, absent, denied) is *marked* on the change and the write proceeds | the alternative is a write that fails because the record-keeping failed, which is the tail wagging the dog. A marked gap is honest; a refused write is a regression |
| D156 | **The kit keeps a run's proposals only when nobody else is listening.** `keep_proposals=None` (the default) keeps them in the kit's store only where the host passed no sink of its own; `True`/`False` force it | `KeepingSink`'s own docstring says *whoever holds the sink decides* — so a kit that keeps regardless is taking the product's decision, which is lane P's ask 6. But flipping the default to never would re-break what ENH-011 fixed for a standalone `serve`, where keeping is the only way a minted skill survives a restart. The rule serves both and states itself |

## Boundary and acceptance

**In:** the change on every write-class operation (`write_file`, `delete_file`, `edit_file`,
`move_file`); the cap, truncation and binary markers; the proposal-keeping rule.

**Out:** restoring from a change (Phase 61); a cross-file patch (Phase 60); whole-file *version*
history, which lane P explicitly does not want; any new port or kernel event field — if this phase
finds it needs one, that is an ADR and a re-plan, not a quiet addition.

**Unchanged:** `{"path", "bytes"}` and the other existing result keys stay exactly where they are, so
nothing lane P reads today changes shape. Protocol 3 unchanged. Contract additions only — a minor
bump and a *Pins* row (D9).

## Groups

| | What | Asks |
|---|---|---|
| G1 | a write and a delete say what changed | 1 |
| G2 | the same shape for an edit and a move | 1 |
| G3 | the cap is honest — truncated, binary, unreadable, and never fatal | 1 |
| G4 | a run's creations reach the product, not the kit's store | 6 |
| G5 | the migration note, and the gate | — |

## Verification

Per project-rules, and TDD is strict here: every group starts red, every assertion is
mutation-checked. The Rule 12 evidence for this phase is the full gate — `ruff check`,
`ruff format --check`, `mypy` strict, the whole suite — plus, for G1–G3, a measurement that the
change on the record matches what the filesystem actually holds, since agreeing with itself is not
the property that matters.
