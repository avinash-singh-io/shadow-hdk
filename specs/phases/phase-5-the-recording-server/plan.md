---
type: Plan
phase: 5-the-recording-server
---

# Phase 5 — plan

```
# Sequential:  Group 0 → Group 1 → Group 2
```

## Group 0 — posture, where it belongs

**Sequential.** A kernel change, so it goes first and everything else assumes it.

- `Provenance.posture: Literal["controlled", "observed"] = "controlled"`
- Every package to the next minor (D9), and a *Pins* row on the board
- RED: the default is `controlled`; an `observed` provenance round-trips through JSON

**Commit:** `feat(kernel)!: provenance says whether an effect was controlled or merely observed`

## Group 1 — the server

**Sequential.**

- `RecordingServer(context, *, name)` over `mcp.server.lowlevel.Server`
- `list_tools` → `await context.visible()`, translated to MCP tools
- `call_tool` → **`run()` a one-step composition as a child**, and hand back the observation
- A refusal becomes an MCP error the child can read; a `Failed` becomes an error too
- `connected()` — an in-memory transport, so a real `ClientSession` can drive it

**Commit:** `feat(adapters): our registry, offered to a child as an MCP server`

## Group 2 — proof, and what is not wired

**Sequential.**

- A real `ClientSession` lists and calls
- A narrowing mode narrows the child, with nothing between
- The parent's stream carries the child's steps
- The lease stops a child that will not stop
- `[~]` serving a *subprocess* child needs a listening transport — recorded with what it needs

**Commit:** `feat: what a child did is on the parent's record because it was routed`
