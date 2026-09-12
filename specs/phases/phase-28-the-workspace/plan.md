---
type: Plan
phase: 28
---

# Plan — Phase 28

## Group 1 — the registries visible (built)
`Thread.tools() -> list[Offered]` (registration, judgement, source); `tools/list {thread_id}`
and `skills/list` on the wire; parity rule 4 grows `Thread.tools`; `ServeHost.skills` — one
`SkillRegistry` (`skills_for`: shipped, then the store) handed to `workshop(skills=)` for every
thread; the studio's environment pane shows both; the TypeScript client has `tools.list` and
`skills.list`. `shadow-hdk serve` takes `--flag value` as well as `--flag=value`.

## Group 2 — what the demo found (built)
BUG-030: `spawn_options` inherits the parent's context attributes (thread, turn, mode, options)
unless the caller hands the child its own. BUG-031: `--tools ""` in the Claude Code provider file.
The `ask` mode as the fourth shipped policy (`_asking`: ceiling OURS, `ask_above` PROVIDER).
`shadow-hdk-serve[providers]` — the `jsonl` and `acp` transport adapters as an extra.

## Group 3 — the workspace: roots, and the environment that follows the mode
**Design.** A `Workspace` is an ordered tuple of `Root(name, path)`; the first is the primary
and where relative paths resolve; the rest are addressed `name/relative` (VS Code's multi-root,
Claude Code's `--add-dir`, Codex's `writable_roots`). The environment (`LocalEnvironment`,
`SandboxEnvironment`) opens on a workspace: the seatbelt/bubblewrap profile allows writes under
every root; `inside(path)` resolves against the primary or the named root and refuses the rest;
the proof (D36) writes inside *each* root and outside *all*; `Isolation` is unchanged. The scope
stays `workspace` — a policy that wants to distinguish roots writes an act rule on the path
(D65). `ThreadRecord.root` becomes `roots`; `thread/start {roots: [{name, path}], …}` (a bare
`root` still works and means one root named after its directory); `thread/add_root` re-opens the
environment for the new set and records `RootAdded` on the thread — between turns only. The
files methods list and read across roots (`files/list` returns `root` per entry; `files/read
{root, path}`). The page shows one tree per root and a "+ add directory" affordance; the demo's
`workspace/finance` and `workspace/sales` become two roots.

**The environment follows the mode.** `ModeSpec` grows `environment: Mode | None` — the shipped
`read-only` and `ask` name `read-only` and `workspace-write`; a mode document may name one.
`Thread.set_mode` re-opens the environment when the named environment mode differs from the one
open (the proof runs again, ~1 s), and the registry's next refresh recomputes every profile.
Until then the page must not say `full` when the sandbox is workspace-write: `thread/start`
returns the environment's mode beside the policy's.

**The catalogue follows the mode** (BUG-032): `RecordingServer` sends
`notifications/tools/list_changed` after `set_mode`; measured against Claude Code and Codex —
where a CLI ignores it, `set_mode` reopens the provider (as a behaviour change already does).

## Group 4 — kept, not printed
`ServeHost`'s sink keeps what a run proposes: a `mint_skill` proposal becomes a `skills` row
(D66), so the skill is offered after a restart and listed by `skills/list` with source `store`.
The rule stays: the runtime has no write path; the *host's* sink writes.

## Close
Decisions recorded (D73–D75 so far); the index; the studio and the demo copy in step; README;
0.25.0 across every package (a contract change: `tools/list`, `skills/list`, the `ask` mode,
the child's context); land; board.
