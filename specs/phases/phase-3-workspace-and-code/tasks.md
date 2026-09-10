---
type: Tasks
phase: 3-workspace-and-code
---

# Phase 3 — tasks

## Group 0 — the workspace

- [x] `packages/adapters/workspace/pyproject.toml`
- [x] `WorkspaceComponents(root, *, at, writable=True)`
- [x] `_resolve(path)` — one resolver, `Path.resolve()` then `is_relative_to(root)`, used by all four
- [x] `read_file`, `write_file`, `list_dir`, `delete_file`
- [x] effects: reads `{workspace}`; writes `{workspace}` and `reversible: true`
- [x] RED: `..` refused · absolute path refused · **a real symlink out of the root** refused
- [x] RED: a missing file is `Failed`, not a raise; a write creates parents; a read round-trips text
- [x] `writable=False` makes the write and delete components absent, not refused at call time
- [x] `TestWorkspaceComponentsIsAComponentPort(ComponentPortContract)`
- [x] Gate

## Group 1 — the sandbox

- [x] `packages/adapters/sandbox_subprocess/pyproject.toml`
- [x] `SubprocessSandbox(root, *, contained, timeout_s=30, output_limit=64_000, network=False)`
- [x] `contained` keyword-only with **no default**
- [x] `run_python(source)` and `run_shell(command)` — cwd in the root, env stripped
- [x] output capped, and the cap **said** in the result rather than silently truncating
- [x] RED: a sleeping script is stopped by the timeout, and the elapsed time is measured
- [x] RED: a non-zero exit is `Completed` with the code, not `Failed` — a failing script ran fine
- [x] RED: output beyond the cap is truncated and says so
- [x] effects carry `contained` verbatim and `reaches=network`
- [x] `TestSubprocessSandboxIsAComponentPort(ComponentPortContract)`
- [x] Gate

## Group 2 — containment decides visibility

- [ ] RED: `contained=False` + a mode requiring containment → `Refuse`
- [ ] RED: the same sandbox is **absent** from `RunContext.visible()` — end to end, through a run
- [ ] RED: `contained=True` → allowed and visible
- [ ] a real run in which the agent writes `notes.md` and `page.html`, and the files exist
- [ ] tasks, history, status, board
- [ ] Gate
