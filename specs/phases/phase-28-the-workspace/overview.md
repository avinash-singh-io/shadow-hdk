---
type: Phase
phase: 28
name: the-workspace
status: complete
topics: [workspace, roots, environment, modes, approval, registries, tools, skills, studio, demo]
deps: [phase-25-the-hosts-controls, phase-26-any-language, phase-27-batteries-and-the-facade]
---

# Phase 28 — The workspace

**What a conversation works on, chosen by the product** — one directory or several, named when
a thread starts, added while it runs — and **what the person sees of the harness while it works**:
the tools the agent is offered under the mode, with their effects and the mode's judgement; the
skills it may choose and the ones it mints; a mode that *asks*.

Opened from the owner's review of 2026-09-12 and from the demo that followed it, which found
three bugs (BUG-030 to BUG-032), one leak (BUG-033) and the gaps this phase closes.

## What this phase makes true

- **The registries are visible** (group 1 — built): `Thread.tools()` answers what the agent is
  offered *now* — every registration with the judgement the current mode gives its effects —
  and crosses as `tools/list`; `skills/list` crosses the skill registry with its sources; the
  host holds one skill registry across its threads, so a minted skill is offered in the next.
- **A child is judged in its parent's context** (group 2 — built, BUG-030): the mode a host set
  reaches every tool call, not only the turn's own step.
- **The `ask` mode** (group 2 — built): the workspace is the ceiling, and every write, run or
  delete inside it is asked about first — the mode every coding CLI opens in. Approve · deny ·
  approve-and-add-rule, measured live.
- **A run's tool surface is exactly the registry** (group 2 — built, BUG-031): every Claude Code
  built-in off by construction (`--tools ""`), not by a list of names.
- **The workspace is one or many roots** (group 3 — built, D76): a thread
  names its roots at `thread/start` (or takes the host's default), each root a name and a path;
  the environment confines to all of them and proves it; the file tools address `name/path`;
  `files/*` list and read across them; a root can be **added live** (`thread/add_root`, Claude
  Code's `/add-dir`) with the proof re-run for the new set.
- **The environment follows the mode** (group 3 — built): a shipped mode names the environment mode it
  needs, and `set_mode` re-opens (re-proves) the environment when that differs — today the
  selector flips the policy while the sandbox stays as opened, so `full` on a workspace-write
  thread reaches nothing more, and the page says otherwise.
- **The provider's catalogue follows the mode** (group 3 — built, BUG-032): the offered registry sends
  `notifications/tools/list_changed` after `set_mode`, so a resident CLI re-lists — today it holds
  the catalogue it fetched under the previous mode until the thread is resumed.
- **Kept, not printed** (group 4 — built, ENH-011): what a run proposes for keeping — a minted skill — is kept in
  the store by the shipped composition, so it is offered after a restart; today `serve`'s sink is
  stdout.

## Out of scope

- Multiple *providers* on one thread; multiple *threads* on one page — a product's composition.
- A workspace that is not a directory (a database, a bucket) — an environment adapter of its own.
- Context engineering (Phase 29) and collaboration (Phase 30).
