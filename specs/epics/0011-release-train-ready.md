---
type: Reply
---

# Lane H — approved implementation and release preparation complete

**Not published.** Six independent release candidates are frozen and pushed, in the order below.
Latest published release remains 0.44.1, confirmed from GitHub release state on 2026-10-04.
The phase remains open for owner landing, publication and closure; no product pin changed.

| order | candidate branch | item | full gate passed | new installed cases | anchored mutations | owner note |
|---|---|---|---:|---:|---:|---|
| 1 | codex/release-0.45.0 | E plus mandated PostgreSQL default flip; previously gated short-list work retained | 2,238 | 17 | 20 | [0.45.0](0011-reply-to-lane-p-3.md) |
| 2 | codex/release-0.46.0 | C, stored plan limits | 2,248 | 10 | 10 | [0.46.0](0011-release-0.46.0.md) |
| 3 | codex/release-0.47.0 | D, human-readable description | 2,254 | 6 | 7 | [0.47.0](0011-release-0.47.0.md) |
| 4 | codex/release-0.47.1 | H6 / BUG-238, mode fragment decoding | 2,260 | 6 | 10 | [0.47.1](0011-release-0.47.1.md) |
| 5 | codex/release-0.47.2 | H7 / BUG-239, native interrupt and next-turn boundary | 2,264 | 4 | 8 | [0.47.2](0011-release-0.47.2.md) |
| 6 | codex/release-0.47.3 | H8 / BUG-240, model-loop cache usage | 2,274 | 10 | 20 | [0.47.3](0011-release-0.47.3.md) |

Every gate has 8 skipped and 24 live cases deselected, with disposable PostgreSQL enabled.
Lint, format and strict types pass. Each kit wheel/sdist builds; new cases pass on installed wheels
outside checkout. The final wheel matches all 165 Python package source files. Schemas and the
TypeScript contracts regenerate without drift. H7 additionally passes a live check on Claude Code
2.1.187, from source and installed wheel, retaining its process/session and answering the next turn.

## Decisions and source confirmation

E needed no new decision: it was already decided and implemented. Preserve the binding/choosing
boundary documented in [E evidence](../phases/phase-66-the-short-list/evidence/g5-e-confirmed.md).
The host pre-binds where the kit owns the loop; CLI runs report agent.skill as unhonoured, while
use_skill remains a governed component with its needs check. Never insert unchecked procedure
text into CLI instructions. C/D follow their approved design; absorb and offload_over were not
added to stored rows.

H6's crash was confirmed; the missing-wire-path claim was not: store/put already transports mode
rows. H7 required both a native control request and draining cancelled frames before the next
prompt. H8 required preserving existing usage counters at every adapter join. Each was documented
before implementation, tested red first, then fixed separately. D190's genericity sentence is in
every implementation commit; D184's [migration map](../planning/what-moves-to-shadow.md) is updated.
No excluded native work, product vocabulary, product pins or unassigned framework scope was built.

## Verification tool finding

TD-021 records a same-second/same-size Python bytecode cache risk in the mutation helper.
The general tooling fix is separate work. This train uses source caches cleared before every
mutant and bytecode writes disabled. All 55 earlier checks were re-run under that precaution,
and H8 adds 20 more: all 75 bite. Raw recheck evidence is in
[train mutations](../phases/phase-66-the-short-list/evidence/train-mutations-rechecked.txt) and
[H8 mutations](../phases/phase-66-the-short-list/evidence/g6-h8-mutations.txt).

Completion evidence is recorded in the [requirement audit](../phases/phase-66-the-short-list/evidence/train-completion-audit.md) and
[wheel/ref audit](../phases/phase-66-the-short-list/evidence/train-artifact-audit.json).

## Owner landing and publication

Use the exact command block in each owner note, one candidate at a time, parent-first. Each block
fetches current state, lands staging then main, compares the resulting tree to the frozen candidate,
and supplies tag/Release commands. Stop on any mismatch and gate the changed tree. Never merge the
moving phase branch as a substitute. Proposed merged trees match the gated candidates; recheck
when landing because upstream can change.

Protected pushes, approval sentinels, tags, GitHub Releases, product pins and final phase closure
are the owner's actions. None was performed by this preparation. After each publication, verify
both distributions and all seven files, the matching Linux helper, and a fresh install outside CI
before proceeding to the next candidate. G7 stays open for these actions; G1–G6 are complete.

## Published 0.45.0 — 2026-10-04

Owner explicitly authorized all six versions in this chat. Staging → main landed parent-first;
the package sources match the frozen candidate. The release retains the verified CLI-independent
wire-test repair. Merged-tree lint, format and strict types pass; 2238 passed, 8 skipped, 24 deselected, 85 warnings in 188.91s (0:03:08)
Publish workflow 37160034400 is green, including installed Linux confinement. Both PyPI distributions
have all seven files; downloaded hashes and 165 wheel Python sources match the tag. A fresh
Python 3.12 installation outside checkout imports and answers initialize. Linux manylinux2014
x86_64 and aarch64 resolutions each pull the exact matching helper.

Release: https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.45.0. Evidence: `evidence/published-0.45.0.json`.

## Published 0.46.0 — 2026-10-04

Owner explicitly authorized all six versions in this chat. Staging → main landed parent-first;
the package sources match the frozen candidate. The release retains the verified CLI-independent
wire-test repair. Merged-tree lint, format and strict types pass; 2248 passed, 8 skipped, 24 deselected, 85 warnings in 198.09s (0:03:18)
Publish workflow 37160648652 is green, including installed Linux confinement. Both PyPI distributions
have all seven files; downloaded hashes and 165 wheel Python sources match the tag. A fresh
Python 3.12 installation outside checkout imports and answers initialize. Linux manylinux2014
x86_64 and aarch64 resolutions each pull the exact matching helper.

Release: https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.46.0. Evidence: `evidence/published-0.46.0.json`.

## Published 0.47.0 — 2026-10-04

Owner explicitly authorized all six versions in this chat. Staging → main landed parent-first;
the package sources match the frozen candidate. The release retains the verified CLI-independent
wire-test repair. Merged-tree lint, format and strict types pass; 2254 passed, 8 skipped, 24 deselected, 85 warnings in 216.82s (0:03:36)
Publish workflow 37161642730 is green, including installed Linux confinement. Both PyPI distributions
have all seven files; downloaded hashes and 165 wheel Python sources match the tag. A fresh
Python 3.12 installation outside checkout imports and answers initialize. Linux manylinux2014
x86_64 and aarch64 resolutions each pull the exact matching helper.

Release: https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.47.0. Evidence: `evidence/published-0.47.0.json`.

## Published 0.47.1 — 2026-10-04

Owner explicitly authorized all six versions in this chat. Staging → main landed parent-first;
the package sources match the frozen candidate. The release retains the verified CLI-independent
wire-test repair. Merged-tree lint, format and strict types pass; 2260 passed, 8 skipped, 24 deselected, 85 warnings in 210.57s (0:03:30)
Publish workflow 37179194036 is green, including installed Linux confinement. Both PyPI distributions
have all seven files; downloaded hashes and 165 wheel Python sources match the tag. A fresh
Python 3.12 installation outside checkout imports and answers initialize. Linux manylinux2014
x86_64 and aarch64 resolutions each pull the exact matching helper.

Release: https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.47.1. Evidence: `evidence/published-0.47.1.json`.

## Published 0.47.2 — 2026-10-04

Owner explicitly authorized all six versions in this chat. Staging → main landed parent-first;
the package sources match the frozen candidate. The release retains the verified CLI-independent
wire-test repair. Merged-tree lint, format and strict types pass; 2264 passed, 8 skipped, 24 deselected, 85 warnings in 198.34s (0:03:18)
Publish workflow 37180063858 is green, including installed Linux confinement. Both PyPI distributions
have all seven files; downloaded hashes and 165 wheel Python sources match the tag. A fresh
Python 3.12 installation outside checkout imports and answers initialize. Linux manylinux2014
x86_64 and aarch64 resolutions each pull the exact matching helper.

Release: https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.47.2. Evidence: `evidence/published-0.47.2.json`.
