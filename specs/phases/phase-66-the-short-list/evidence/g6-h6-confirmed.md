# H6 — confirmed before implementation, 2026-10-04

`mode_from_document` forwards raw fragment dictionaries into `Behaviour`. A direct reproduction with one named, attributable fragment prints its runtime type as `dict`; `framed(carried_by(spec.behaviour))` then raises `AttributeError: 'dict' object has no attribute 'name'`.

The audit's missing-wire-path claim is not confirmed: the existing `ThreadMethods._store_put` writes a supplied row unchanged, and `StoreModes` reads the `modes` collection. No new wire method is needed. The regression must exercise that existing write/read/assembly path, including source attribution and fragment order.

BUG-238 is P1. Decode only the existing fragments field through the existing contract decoder, preserving other mode fields and the shared assembler. Malformed fragment documents must fail as named source problems instead of reaching assembly. This repairs an existing contract and merits a patch, 0.47.1, after the frozen 0.47.0 candidate. D190: a coding tool, a support desk and a research assistant would each use named context from stored mode data. No tool meaning or policy enters kernel/runtime.

## Implementation verification

Five new cases failed for the defect before production changes (the empty list already passed).
The existing contract loader now decodes only the fragments field. All six new cases and 118 mode
cases pass. Ten anchored mutations bite; names, text, attribution, order, empty lists, each malformed
case and source-problem reporting are load-bearing. Full gate: 2,260 passed, 8 skipped, 24 deselected; lint/format/types clean. Six new cases pass on the installed wheel outside checkout; all 165 package Python sources match it. Kit wheel and sdist build; schemas and TypeScript contracts regenerate without drift.
