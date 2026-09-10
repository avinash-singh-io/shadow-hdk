---
type: Plan
phase: 3-workspace-and-code
---

# Phase 3 — plan

```
# Parallel:  (Group 0 + Group 1) → Group 2
```

The two adapters share nothing but the contract suite, so they can be built in either order. Group 2
is the end-to-end proof that ties `contained` to what the model can see.

## Group 0 — the workspace

**Parallel with Group 1.**

- `WorkspaceComponents(root, *, at, writable=True)` — `read_file`, `write_file`, `list_dir`, `delete_file`
- One resolver, used by every operation: resolve, then refuse anything outside the root
- **Symlinks resolved before the check**, because a link is how a confined path stops being one
- Effects: reads declare `reads: {workspace}`; writes declare `writes: {workspace}`, `reversible: true`
- RED first: escape by `..`, by absolute path, by symlink; each a `Failed`, never a raise

**Commit:** `feat(adapters): a workspace the agent can write to, and cannot write outside`

## Group 1 — the sandbox

**Parallel with Group 0.**

- `SubprocessSandbox(root, *, contained, timeout_s, output_limit, network=False)`
- `run_python`, `run_shell` — cwd inside the root, env stripped, output capped
- `contained` has **no default**: a deployment states it
- Effects: `writes: {workspace}`, `reaches: network`, `reversible: false`, `contained: contained`
- RED first: a timeout that fires and is measured; an output cap that bites; a non-zero exit that is data

**Commit:** `feat(adapters): a subprocess sandbox that says what it is`

## Group 2 — containment decides visibility

**Sequential.** Depends on both.

- End to end: `contained=False` + a mode requiring containment → refused, and **absent** from `RunContext.visible()`
- The same sandbox with `contained=True` → allowed and visible
- An agent writes a markdown file and an HTML page through the workspace, on a real run
- Phase records, board, status

**Commit:** `feat: what the deployment is decides what the model can see`
