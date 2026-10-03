---
type: History
phase: phase-66-the-short-list
---

# Phase 66 history

### [SCOPE_CHANGE] 2026-10-03 — the last bridge phase: a short list, then maintenance
Topics: scope, maintenance, shadow, lane-p
Affects-phases: none
Affects-specs: specs/phases/phase-66-the-short-list/overview.md
Detail: The owner's decision after lane P's cross-repo plan of 2026-10-03: HDK takes six items —
H10, H11 (confirm then build), H20, H23, H6–H8 — released as 0.45.x, and is then maintenance only:
bugs and the product's pins. H12–H17, H21, H22, H29, H30 and H41–H43 belong to Shadow and are not to
be built here. The owner also set two standing constraints: prefer open-source software where it does
the job, and follow open standards rather than inventing a format where one exists.

---

### [DECISION] 2026-10-03 — D184: H10 is one file, kept current, not a paragraph per phase
Topics: h10, d153, migration, parity
Affects-phases: none
Affects-specs: specs/planning/what-moves-to-shadow.md, specs/decisions/index.md
Detail: G1 complete. D153 permitted this bridge on the condition that each phase say what migrates
and what is throwaway; phases 59–65 did not, so eight shipped capabilities had no planned home and
nobody had decided whether they survive. The correction is one file that *is* the answer and that
every later bridge phase updates before closing — a per-phase paragraph in a retrospective is the
mechanism that already failed. The evidence and the parity list are in
`specs/planning/what-moves-to-shadow.md`; the finding is also appended to phase 65's history, where
the work that found it lives.

---
