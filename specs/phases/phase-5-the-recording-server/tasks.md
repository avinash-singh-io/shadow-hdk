---
type: Tasks
phase: 5-the-recording-server
---

# Phase 5 — tasks

## Group 0 — posture

- [ ] `Provenance.posture: Literal["controlled", "observed"] = "controlled"`
- [ ] RED: the default is `controlled`; `observed` round-trips through JSON
- [ ] every package to the next minor; `test_versions.py` updated
- [ ] the ACP bridge marks a tool call it only *heard about* as `observed`
- [ ] Gate

## Group 1 — the server

- [ ] `packages/adapters/recording/pyproject.toml`, depending on the `mcp` SDK
- [ ] `RecordingServer(context, *, name)` over `mcp.server.lowlevel.Server`
- [ ] `list_tools` → `context.visible()`, name / description / input schema carried verbatim
- [ ] `call_tool` → `run()` a one-step composition as a child of the parent run
- [ ] a refused call → an MCP error naming the reason; the component never invoked
- [ ] a `Failed` observation → an MCP error the child can read
- [ ] `connected()` — an in-memory pair, so a real `ClientSession` drives it
- [ ] RED: each of the above
- [ ] Gate

## Group 2 — proof

- [ ] RED: a real `ClientSession` lists exactly what `visible()` returns
- [ ] RED: a narrowing mode narrows the child, with no code in between
- [ ] RED: `Invoked` and `Observed` reach the **parent's** stream, carrying the child's run id
- [ ] RED: a child that calls forever is stopped by the parent's lease
- [ ] `[~]` a subprocess child needs a listening transport — what it needs, recorded
- [ ] records, board, status
- [ ] Gate
