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
- [ ] `Workspace`/`Root` in the runtime's environment; the OS profiles over many roots; the proof over each; `inside()` by name
- [ ] `ThreadRecord.roots`; `thread/start {roots}`; `thread/add_root`; `RootAdded`
- [ ] `files/list` and `files/read` across roots; the page's trees; the demo on two roots
- [ ] `ModeSpec.environment`; `set_mode` re-opens the environment when it differs; the environment's mode in `thread/start`'s result
- [ ] BUG-032 `tools/list_changed` after `set_mode`, measured on Claude Code and Codex

## Group 4 — kept, not printed
- [ ] the host's sink keeps a minted skill as a store row; listed with source `store` after a restart

## Close
- [ ] decisions; index; README; 0.25.0; landed; board
