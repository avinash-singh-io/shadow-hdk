---
type: History
phase: 26
---

# History — Phase 26

Append-only. Decisions as `### [DECISION] date — D<n>: title`; the index in
`specs/decisions/index.md` is regenerated from them.

### [NOTE] 2026-09-12 — Opened

Topics: wire, thread, serve
Affects-phases: phase-26-any-language
Affects-specs: none

Cut from `main` after Phase 25 landed (v0.22.0). The plan is `planning/the-substrate.md` §1.1,
§3.8 and §4 (Phase 26). The wire already has a stdio transport (the runtime as a child, newline-
delimited JSON-RPC) and an HTTP/SSE listener with a token; the thread, the handles and the store
are what do not cross yet.

---
