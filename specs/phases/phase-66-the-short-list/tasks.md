---
type: Tasks
phase: phase-66-the-short-list
---

# Phase 66 tasks

## G1 — H10: what moves to Shadow (D184)

- [x] G1.5 revised 2026-10-03 from Shadow's own row-by-row answer: five rows moved, the parity list is five, and `SinkPort` is settled as a real gap

- [x] G1.1 every contract from 0.38.0 to 0.44.0 classified: migrates, not planned, or unknown
- [x] G1.2 the method written down so the next reader can repeat it — and so counting cannot mislead
- [x] G1.3 D184 recorded; phase 65's history carries the finding
- [x] G1.4 the standing requirement stated: every later bridge phase updates the file before closing

## G2 — H11: confirm the gaps before building anything

- [x] G2.1 what an agent row can carry today, read off the source
- [x] G2.2 what a CLI provider honours of it — **nothing: `_agent_named` returns early with no model, so even the D176 refusal never runs**
- [x] G2.3 what a key-backed model honours of it — all of the row; `plan`, `absorb` and `offload_over` are not settable *as data*
- [x] G2.4 the gap list reported in `evidence/g2-h11-gaps.md`, with a recommendation per item and one question for the owner (F)

## G3 — H20: full diffs

- [x] G3.1 `Environment.open(change_diff_bytes=)` — an int, or `None` for the whole diff; the default is unchanged
- [x] G3.2 `change_diff` — a registered read-class component, paging by `handle`/`start`/`length` as `recall` does (D47)
- [x] G3.3 unified diff from stdlib `difflib` throughout, on the record and through the door
- [x] G3.4 `truncated` and `whole` — the uncut size, so a host can decide whether to ask before asking

## G4 — H23: a governed Codex carries only what it was given

- [x] G4.1 confirmed — and the record's own prose was the false claim: it said Codex needed a strict flag upstream, and `--ignore-user-config` existed on that very version
- [x] G4.2 `mcp_strict_args = ["--ignore-user-config"]`, the same seam Claude Code uses; our own servers survive it as `-c` overrides and auth still uses `CODEX_HOME`
- [x] G4.3 applied only when tools are injected — a launch governing nothing does not drop a person's configuration

## G5 — H11's confirmed remainder

- [x] G5.1 **A** — the name resolved on every path (D176 made true on a CLI), and a dropped agent named on the thread, the record and the wire
- [x] G5.2 **B** — the agent's `system` and `tool_names` honoured on a CLI, intersected with the mode's and never widening; composed in **one place**, the behaviour every provider session is opened with
- [x] G5.3 **E** — `skill` on the row
- [x] G5.4 **C** — `plan` on the row
- [x] G5.5 **D** — `description` on the row
- [x] G5.6 **F** — not built: `model` and `effort` stay on the mode (G2's recommendation, lane P and the owner agreed)

## G6 — H6–H8

- [x] G6.1 H6 confirm: fragments in a mode document, and over the wire
- [x] G6.2 H7 confirm: interrupting Claude Code without ending the session
- [x] G6.3 H8 confirm: cache tokens on the key-backed loop
- [x] G6.4 fix what is confirmed; report what is not

## G7 — the release train

- [x] G7.1 the migration note
- [x] G7.2 version, changelog, status, history, retrospective with verification evidence
- [x] G7.3 the reply to lane P in `specs/epics/`
- [x] G7.4 the full gate green, output read from a file

## 0.45.0 checkpoint — E plus the required default change

- [x] confirm E against source before implementation; preserve the approved binding/choosing boundary
- [x] new tests red, then 17 targeted tests green; 37 PostgreSQL/store tests green on a disposable server
- [x] mutation checks bite; remove the redundant internal preparation default
- [x] migration table updated for E, with C and D left unbuilt
- [x] full gate and installed-artifact check: 2,238 passed; 17 new cases pass on installed wheel
- [x] owner protected landing, tag and GitHub Release; verify both published distributions afterwards

G7 closes only when the train is complete. This checkpoint does not close the phase.

## 0.46.0 checkpoint — C

- [x] source confirmed and reported before implementation; six cases red, ten new cases green
- [x] ten anchored mutations bite; installed-wheel behaviour verified outside checkout
- [x] full gate: 2,248 passed with disposable PostgreSQL; migration table and lane P note updated
- [x] owner parent-first landing, tag, publication and fresh-install/seven-file verification

## 0.47.0 checkpoint — D

- [x] source confirmed before implementation; five cases red, six new cases green
- [x] seven mutations bite; installed chooser behaviour verified outside checkout
- [x] full gate: 2,254 passed with disposable PostgreSQL; migration table and lane P note updated
- [x] owner parent-first landing, tag, publication and fresh-install/seven-file verification

## 0.47.1 checkpoint — H6 / BUG-238

- [x] source confirmed and reported before implementation; five cases red, six green
- [x] existing wire-store path proved; ten mutations bite; six installed-wheel cases pass
- [x] full gate: 2,260 passed with disposable PostgreSQL; D184 map and lane P note updated
- [x] owner parent-first landing, tag, publication and fresh-install/seven-file verification

## 0.47.2 checkpoint — H7 / BUG-239

- [x] source confirmed and reported before implementation; two cases red, four final cases green
- [x] eight mutations bite; four installed-wheel cases pass; live same-process/session next-turn check passes on source and installed wheel
- [x] full gate: 2,264 passed with disposable PostgreSQL; D184 map and lane P note updated
- [x] owner parent-first landing, tag, publication and fresh-install/seven-file verification

## 0.47.3 checkpoint — H8 / BUG-240

- [x] source confirmed and reported before implementation; nine cases red, ten green
- [x] twenty mutations bite; ten installed-wheel cases pass; all 55 earlier train checks rechecked with source caches cleared
- [x] full gate: 2,274 passed with disposable PostgreSQL; D184 map and lane P note updated
- [x] owner parent-first landing, tag, publication and fresh-install/seven-file verification

## Implementation and release complete

G1–G6 are complete. Every release has a version, migration note, full gate, installed-package
behaviour proof and concrete owner commands. G7 is complete: all six versions are merged,
published and independently verified. See the release-train index in the epic replies.
