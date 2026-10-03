---
type: Evidence
phase: phase-66-the-short-list
group: G5-D
---

# D — a chooser description, confirmed before implementation

Read at `df83606` on 2026-10-04. Pattern and the row loader have no description field. The agent
registry's listing derives its line from the first stripped system-prompt line. The wire's
agents/list already exposes that listing as description. Thus the missing path is one optional
field plus registry selection; the wire shape already exists. Preserve the old derivation when
absent, exactly as the approved G2 design requires. No redesign or new decision is needed.

D190: a coding tool, a support desk and a research assistant would each use this. An agent's
human-readable description is presentation content, held in the adapter's data, not core or
runtime. Verify the stored row reaches the actual agents-list reply, and keep existing prompts.

## Verification

Five new cases failed before implementation; six pass after it, with the existing wire tests.
Seven anchored mutations bite: lost description, changed role instructions, wrong direct default,
lost explicit text, lost intentional blank, and lost absent or null fallback. A clean installed
0.47.0 wheel outside checkout passes all six new cases. Its 165 Python source files match the
checkout. Schemas and TypeScript contracts regenerate without drift. Full gate with disposable
PostgreSQL enabled: 2,254 passed, 8 skipped, 24 deselected, exit 0.
