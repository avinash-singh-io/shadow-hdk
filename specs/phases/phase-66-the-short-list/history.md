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
### [DECISION] 2026-10-03 — D185/D186: the diff cap is the host's, and a cut diff is held, bounded
Topics: h20, diffs, environment, open-standards
Affects-phases: none
Affects-specs: none
Detail: G3. **D185 — the cap is the host's**: `Environment.open(change_diff_bytes=)`, an int or
`None` for the whole diff, defaulting to today's 4096 so nothing existing moves. The old comment
claimed *"a host that needs the whole change reads the file"*, which was never true for a contained
or remote environment — the case this record exists for. All four call sites had taken the default,
so lane P's workbench showed 4 KB per file because nobody could choose otherwise.

**D186 — a cut diff is held whole, by handle, bounded**: `change_diff` is a registered read-class
component paging by `handle`/`start`/`length`, deliberately `recall`'s idiom (D47) rather than a
second shape for the same problem. The hold is bounded (`change_diffs_held`, default 32, the host's)
because keeping every cut diff for an environment's life would hold the content of every file an
agent ever touched — a leak and a privacy problem nobody asked for. A handle exists **only** for a
cut diff, the oldest are evicted first, and asking for an evicted one is refused with *it was
dropped* rather than *no such handle*, which are different facts a host acts on differently.
`whole` reports the uncut size either way, so a host decides whether to ask before asking.

Open standards, per the owner's constraint: unified diff from the standard library's `difflib`, on
the record and through the door alike, so a product parses one format and we invent none.

The derivation moved rather than doubled: `changed` stays pure over two strings with the cutting done
by the environment that owns the cap and the hold, so the diff is computed once.

---

### [DISCOVERY] 2026-10-03 — three weak spots in G3's own tests, found by mutation
Topics: h20, mutation-testing
Affects-phases: none
Affects-specs: none
Detail: The eviction test passed for the wrong reason: its second write appended one line to the
same file, so the second diff was about eighty bytes, the cap never cut it, nothing was held and
nothing was evicted. Rewritten to write wholly different content. `change_diffs_held=0` was
documented as a supported choice with no test, so a mutation deleting the branch survived. And
`whole`'s contract — the **uncut** size — was invisible through an environment, because every
production call now passes `cap=None` and cuts afterwards; it is pinned directly on `changed` instead.
Also covered: `bool` is an `int` subclass in Python, so an unguarded `int(start)` turns `true` into 1
and silently drops the first character.

---
