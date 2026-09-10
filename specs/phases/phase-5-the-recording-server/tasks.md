---
type: Tasks
phase: 5-the-recording-server
---

# Phase 5 — tasks

## Group 0 — posture

- [x] `Provenance.posture: Literal["controlled", "observed"] = "controlled"`
- [x] RED: the default is `controlled`; `observed` round-trips through JSON
- [x] every package to the next minor; `test_versions.py` updated
- [x] the ACP bridge marks a tool call it only *heard about* as `observed`
- [x] Gate

## Group 1 — the server

- [x] `packages/adapters/recording/pyproject.toml`, depending on the `mcp` SDK
- [x] `RecordingServer(context, *, name)` over `mcp.server.lowlevel.Server`
- [x] `list_tools` → `context.visible()`, name / description / input schema carried verbatim
- [x] `call_tool` → `run()` a one-step composition as a child of the parent run
- [x] a refused call → an MCP error naming the reason; the component never invoked
- [x] a `Failed` observation → an MCP error the child can read
- [x] `served()` + `attach()` — any stream pair, so a real `ClientSession` drives it
- [x] RED: each of the above
- [x] Gate

## Group 2 — proof

- [x] RED: a real `ClientSession` lists exactly what `visible()` returns
- [x] RED: a narrowing mode narrows the child, with no code in between
- [x] RED: `Invoked` and `Observed` reach the **parent's** stream, carrying the child's run id
- [x] RED: a child that calls forever is stopped by the parent's lease
- [x] a real subprocess child, served over its own pipes — `serve_over_pipes` +
      `spikes/mcp/child.py`; the topology is inverted, not merely un-listening
- [~] a child on **another machine** still needs a listening transport (streamable HTTP),
      because this server can only be connected to, never launched → Phase 9
- [x] records, board, status
- [x] Gate
