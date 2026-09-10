---
type: Phase
phase: 3
name: workspace-and-code
epic: 0002-the-workspace-and-driving-another-agent
status: not-started
topics: [workspace, filesystem, sandbox, subprocess, contained, artifacts]
deps: [phase-2-the-spike]
---

# Phase 3 — The workspace, and code

## Goal

The agent can **make things**: write a markdown file, render an HTML page, generate a script — and,
where the deployment permits it, run one. Two adapters, and one idea underneath them.

## The idea underneath

`09` §5 gives "program" three forms, and the third is *code in a sandbox — a component with
`contained: true`, present only on deployments that have a sandbox adapter, absent everywhere else.*

So **whether the agent may run code is not a policy decision made per call.** It is a fact about the
deployment, stated once when the adapter is constructed, and everything downstream follows from it:

```
SubprocessSandbox(root, contained=False)      # a laptop: no real isolation, and it says so
     ↓ declares contained=False
mode ceiling requires contained=True
     ↓ narrows() is False
governance refuses  →  the component is absent from the catalogue  →  the model never sees it
```

The agent always *has* the ability. The deployment decides the permission, once, honestly. A
sandbox that claimed containment it did not have would be the single most dangerous lie in this
system, so `contained` is a constructor argument with no default.

## Scope

### In
- `packages/adapters/workspace` — `read_file`, `write_file`, `list_dir`, `delete_file`, confined to a root
- **Every path resolved and refused outside the root**, symlinks included
- `packages/adapters/sandbox_subprocess` — `run_python`, `run_shell`, with a timeout, an output cap and network off by default
- `contained` as a constructor argument, no default, carried into the effect profile
- Both adapters subclass `ComponentPortContract`

### Out
- gVisor and Firecracker (Phase 11) · the ACP bridge (Phase 4) · artifact versioning, which is a product concern

## Deliverables

| # | Deliverable | Verification |
|---|---|---|
| 1 | `adapters/workspace`, confined | `uv run pytest tests/adapters/workspace` |
| 2 | Escape refused: `..`, absolute paths, symlinks out | the same, one test each |
| 3 | `adapters/sandbox_subprocess` | `uv run pytest tests/adapters/sandbox_subprocess` |
| 4 | A timeout that fires, and an output cap that bites | the same, both measured |
| 5 | `contained=False` → refused by a mode that requires containment, and absent from the catalogue | `tests/adapters/sandbox_subprocess/test_contained.py` |
| 6 | Both pass their port's contract suite | `tests/adapters/contract` |

## Acceptance criteria

- An agent writes a markdown file and an HTML page through components, and the files exist on disk.
- Every escape from the root is refused **as an observation**, never as an exception: `..`, an
  absolute path, and a symlink pointing outside — the last one tested with a real symlink.
- A runaway script is stopped by the timeout, and the stop is measured rather than asserted.
- On `contained=False` a containment-requiring mode refuses the sandbox, and `RunContext.visible()`
  does not list it — proven end to end, not by reading the profile.

## Non-goals worth stating

- **This is not a security boundary.** A subprocess with a timeout is not isolation; it is a leash.
  The adapter says `contained=False` by default *because that is true*, and the honest name for what
  Phase 11 adds is the boundary this one does not have.
