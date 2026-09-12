---
type: History
phase: 28
---

# History — Phase 28

Append-only. Decisions as `### [DECISION] date — D<n>: title`; the index in
`specs/decisions/index.md` is regenerated from them.

### [NOTE] 2026-09-12 — Opened, from the owner's review and a demo outside the tree

Topics: workspace, demo, review
Affects-phases: phase-28-the-workspace
Affects-specs: planning/roadmap.md
Detail: The owner asked four things: why a workspace is named when the harness starts rather than
when a conversation opens, and how two or three directories at once should work; to see the
modes behave differently and the approvals answered; to see the tool and skill registries,
which the page did not show; and to run the studio from outside the harness's tree. The studio
was copied to `../harness-demo/` (a `pyproject.toml` depending on every harness package by path,
editable; `harness.toml`; wigolo installed locally under `tools/`; a sample workspace with
`finance/` and `sales/`) and driven on the owner's subscription — eight turns, $1.60.

---

### [DECISION] 2026-09-12 — D73: the registries are the harness's answer — `Thread.tools()`, `tools/list`, `skills/list`

Topics: registries, tools, skills, wire, studio
Affects-phases: phase-28-the-workspace
Affects-specs: architecture/wire.md, architecture/overview.md

A page that shows "what the agent can do" must not guess it from the names it has seen go by.
`Thread.tools()` walks the thread's own component ports, and for every registration asks the
thread's governance the same question a step would ask — in the thread's context, with its
mode — and answers *allow*, *ask* or *refuse*, with who registered it (the registration's
provenance, looked through a wrapper such as `Switched`). A refused one is what the model is
not offered (`09` §4). On the wire as `tools/list`, held by parity rule 4. `skills/list` reads
the host's skill registry — one per host now (`skills_for`), shared by its threads, so a skill
minted in one thread is offered in the next and listed with source `minted`. Measured through
the demo: `workspace-write` offers 9 of 11 (the web batteries refused: they reach and are not
contained), `read-only` 6 (only reads, the skills, the person, the web), `ask` 9 with every
change marked *ask*.

*Why:* principle 7 — the host holds handles, not code; a registry it can only infer is code.

---

### [DECISION] 2026-09-12 — D74: a child run is judged in its parent's context

Topics: governance, context, children, modes, BUG-030
Affects-phases: phase-28-the-workspace
Affects-specs: architecture/overview.md#governance

Found by the demo: `set_mode("read-only")` — `tools/list` said `run_shell` was refused — and
the agent's `run_shell` appended a file. A tool call through the offered registry is a *child
run* (D62), and `spawn_options` carried no `context`, so the mode governance judged it in its
default — the mode the environment was opened in. Every earlier proof of `set_mode` had judged
the turn's own step, which does carry the context. A child now inherits its parent's attributes
(thread, turn, mode, the host's options) unless the caller hands it its own; the wire's
`spawn_options_now` is the same code. `tests/runtime/test_a_child_is_judged_in_its_parents_context.py`
holds it; the demo re-run showed the write tools absent from the model's catalogue in
`read-only` and the agent saying so.

*Why:* the policy is one, and it is told the same thing about every step of a run and of the
runs that run spawns; an attribute that reached the parent and not the child was a hole in
"govern effects" the size of every tool call.

---

### [DECISION] 2026-09-12 — D75: the `ask` mode; a run's tool surface is exactly the registry

Topics: modes, approval, providers, claude-code, BUG-031
Affects-phases: phase-28-the-workspace
Affects-specs: architecture/overview.md#modes, providers

**`ask`.** The shipped three had no band between *refuse* (read-only) and *allow inside*
(workspace-write): a person could not be asked about a write, and "approve and add a rule"
(D65) had nothing to answer unless the environment itself was opened `full`. `ask` is the
fourth shipped policy — the workspace is the ceiling, and anything that writes, runs or deletes
inside it is asked about (`ask_above` = reads and provider state) — the mode every coding CLI
opens in (Claude Code's *default*, Codex's *on-request*). Measured live: `run_python` approved;
`write_file` approved with a rule (the rule listed at once; the next write to that path silent);
`delete_file` denied, and the agent reported the refusal rather than retrying.

**`--tools ""`.** In a read-only thread the model wrote "the one shell path available is the
`Monitor` tool" — a Claude Code built-in the deny list did not name — and was stopped only by
the CLI's own redirect guard, not by this run's governance (69¢ of fumbling). A list of names is
a snapshot of one CLI version; `--tools ""` disables every built-in by construction and the MCP
registry still arrives (measured in the next turn: `use_skill`, `web_search`, `web_fetch`). The
deny list stays as the record of what was found.

*Why:* principle 2 — every effect goes through a component the runtime judged; a built-in the
CLI adds tomorrow must not be a second path.

---

### [DISCOVERY] 2026-09-12 — What the demo found, beyond the three fixed

Topics: workspace, modes, environment, catalogue, sink, batteries
Affects-phases: phase-28-the-workspace
Affects-specs: planning/roadmap.md
Detail: (1) The mode selector flips the *policy*; the environment stays as opened, so `full` on
a workspace-write thread reaches nothing outside and the page says `full` — group 3 (the
environment follows the mode; the environment's mode in `thread/start`'s result). (2) After
`set_mode` the resident CLI keeps the catalogue it fetched under the previous mode until the
thread is resumed — BUG-032, group 3 (`tools/list_changed`). (3) A minted skill is proposed to
`serve`'s sink, which is stdout: gone at restart — group 4. (4) A battery's process (wigolo,
pid 27919) outlived `serve` when the preview tool ended it — BUG-033. (5) The agent believed the
environment was workspace-write while the mode was read-only, because the mode's behaviour said
nothing — ENH-009: a shipped mode's `append_system` line. (6) A command that exits non-zero is a
*completed* tool call and shows ✓ — ENH-010, the page's presentation. (7) `ScopeSet.of("workspace")`
is one scope over one root: the many-roots design keeps it and lets a rule say the path.

---
