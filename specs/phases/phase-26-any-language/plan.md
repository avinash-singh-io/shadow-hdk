---
type: Plan
phase: 26
---

# Plan — Phase 26

## Group 1 — threads over the wire
The wire's runtime side gains a `ThreadHost` — a port the process that runs the wire hands in
(`open`, `resume`, `list`, and the handles: approvals, store, modes, rules) — and thread methods
over it: `thread/start`, `turn/start` (events, items and activity as notifications, the turn's
record as the result), `thread/resume`, `thread/list`, `thread/fork`, `thread/rollback`,
`thread/archive`, `thread/set_mode`, `thread/set_option`, `turn/steer`, `turn/interrupt`. The
runtime side holds the ports in this shape (a "batteries" host); the inverted shape (`run`,
`resume` with host-side ports) stays as it is. RED: a loopback test with a scripted provider.

## Group 2 — handles over the wire
`approvals/pending`, `approvals/answer` (approve · deny · approve_and_add_rule with the rule;
text for an input request), `approvals/withdrawn` as a notification; `run/cancel`. The parity
invariant extended: a table of host handles and thread operations → wire methods, walked against
`protocol.py`, so a handle added in-process without a wire method fails the build.

## Group 3 — the store over the wire
`store/put|get|delete|list|version` generic; `modes/list`, `rules/list` conveniences. A row put
through the wire is a mode at the next `thread/set_mode` — the same live claim, crossed.

## Group 4 — `serve`
A `shadow-hdk-serve` package (the wire cannot import adapters — the stands-alone rule — so
the composition lives beside it): the conversation composition moved out of the coder example
(`a_thread`, the workshop) into the harness as `shadow_hdk.serve.host`; `shadow-hdk
serve harness.toml --stdio|--http`: `--http` the existing loopback listener with a token, `--stdio`
the existing newline-delimited JSON-RPC over stdin/stdout; a minimal `harness.toml` (root, mode,
provider, store, modes dir) — the full facade is Phase 27. The coder and the studio import the
composition from the package.

## Group 5 — TypeScript
Survey `json-schema-to-typescript` and `quicktype` (READMEs read, recorded in history with the
choice). Generate `clients/typescript/src/schemas.ts` from `schemas/*.json` at build time with the
chosen tool, installed locally under `clients/typescript/` (never globally); a thin client
(`thread.start`, `turn`, `approve`, `setMode`, `interrupt`, `steer`, event/item/activity streams
over HTTP/SSE); an invariant that regenerates into a temp dir and diffs, so the checked-in types
cannot drift from the schemas.

## Group 6 — the studio on the wire
The studio's Python host becomes `serve --http`; the page talks JSON-RPC and SSE — the same
methods a TypeScript product would call. Driven live once or twice.

## Close
D67+ where decisions were taken; index; status/roadmap/changelog/README; Verification Evidence
fresh; a wire contract change → 0.23.0 across every package; land; board with a Pins row.
