---
type: Tasks
phase: 26
---

# Tasks — Phase 26

## Group 1 — threads over the wire
- [x] `ThreadHost` port on the runtime side; `thread/start`, `turn/start` streaming events, items, activity (tagged with the thread)
- [x] `thread/resume`, `close`, `list`, `fork`, `rollback`, `archive`, `set_mode`, `set_option`, `remaining`; `turn/steer`, `turn/interrupt`

## Group 2 — handles over the wire
- [x] `approvals/pending`, `approvals/answer` (approve · deny · approve_and_add_rule; `{text}` for input); `approval_request`/`input_request`/`request_withdrawn` pushed; `run/cancel`
- [x] the parity invariant's rule 4: every public method of `Thread`, `Approvals` and `Store` crosses or says why

## Group 3 — the store over the wire
- [x] `store/put|get|delete|list|version`; `modes/list`, `rules/list`; a crossed row is a mode at the next read

## Group 4 — serve
- [x] `shadow-hdk-serve`: the composition moved out of the coder example (`ServeHost`, `a_thread`, `workshop`, `modes_for`); `shadow-hdk serve harness.toml --stdio|--http [--page]`; the thread's offer held by one task (found behind `--http`)
- [x] the coder and the studio import the composition from the package; the coder's former `workshop` module deleted

## Group 5 — TypeScript
- [x] survey recorded (D68); `clients/typescript/` — generation from the schemas (one module per contract), a thin JSON-RPC/SSE client, `tsc --noEmit`, the drift invariant, proven against a live `serve --http`; CI installs node and builds it

## Group 6 — the studio on the wire
- [x] the studio consumes the wire and nothing local (D69): `serve --http --page`, `files/list`+`files/read` as thread methods, a session's threads close with it, `serve` flags; driven live — one turn on Claude Code (7 tool calls, 31¢), a reload resumed the thread over a new session with no provider left behind

## Close
- [x] D67, D68, D69 recorded and indexed; `architecture/wire.md` grew the second shape; status/roadmap/changelog/README; 0.23.0 across eighteen packages; Verification Evidence fresh
- [x] landed (CI green on `0299fca` → staging `c87c65f` → main → `v0.23.0` → release); board with a Pins row (`f8f2f02`)
