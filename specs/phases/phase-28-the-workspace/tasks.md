---
type: Tasks
phase: 28
---

# Tasks — Phase 28

## Group 1 — the registries visible
- [x] `Thread.tools()`; `tools/list`, `skills/list`; parity rule 4; `ServeHost.skills` shared across threads; the page's Tools and Skills panes; TS client; `--flag value`

## Group 2 — what the demo found
- [x] BUG-030 a child inherits its parent's context (measured: `set_mode("read-only")` then `run_shell` — refused, the tool absent from the model's catalogue)
- [x] BUG-031 every Claude Code built-in off (`--tools ""`; measured: the MCP registry still reaches the model)
- [x] the `ask` mode (measured live: approve · approve-and-add-rule · deny)
- [x] `shadow-hdk-serve[providers]`

## Group 3 — the workspace
- [x] `Workspace`/`Root` in the kernel (pure); the environment over many roots — the OS profiles, the proof over each, `inside()` by name; `Environment.reopen`
- [x] `ThreadRecord.roots` and `.environment`; `thread/start {roots}`; `thread/add_root`; `WorkspaceChanged` (the fifteenth kind; schemas and TS regenerated)
- [x] `files/list` (root per entry) and `files/read {root, path}`; the page's trees and add-directory; the demo on two roots (measured live: `second-repo` added mid-thread, read and written)
- [x] `ModeSpec.environment`; `set_mode` re-opens the environment when it differs; `environment` in `thread/start`, `set_mode` and `add_root` results (measured live: read-only after workspace-write denied every write)
- [x] BUG-032 `tools/list_changed` sent per connection — Claude Code 2.1.235 ignores it (measured) — so a mode change or a root added reopens the provider on its own session (`AgentPort.open(resume=)`, `--resume`; measured live: memory kept, list fresh); Codex to measure when a Codex turn is next spent

## Group 4 — kept, not printed
- [x] `KeepingSink`: a minted skill is a store row, offered after a restart with source `store`; everything still reaches the sink behind it

## Close
- [x] decisions (D73–D76); index; README; 0.25.0 across eighteen packages
- [x] landed: branch CI `da98996` green → staging `720059a` green → main `720059a` green → `v0.25.0` tagged and released (`gh release create --latest`) → branch deleted; board row H30, Pins row, log line (`d2aec68`)
