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

### [DECISION] 2026-09-12 — D76: the workspace is one or many roots, chosen per thread and added live; the environment and the provider follow the mode

Topics: workspace, roots, environment, modes, provider, resume, sink, BUG-032, BUG-033, ENH-011
Affects-phases: phase-28-the-workspace
Affects-specs: architecture/overview.md#environment, architecture/wire.md, architecture/adapters.md

**Roots.** A `Workspace` is an ordered tuple of `Root(name, path)` — the first is the primary,
where a relative path resolves; the rest are addressed by name (`sales/notes.md`) — VS Code's
multi-root, Claude Code's `--add-dir`, Codex's `writable_roots`. It lives in the kernel as pure
data (paths are strings; the kernel touches no filesystem, so nesting is the environment's to
refuse). The environment opens on it: the seatbelt/bubblewrap profile allows writes under every
root, the proof (D36) writes inside *each* and outside *all*, and `inside()` resolves by name,
by absolute path under a root, or under the primary. The policy's scope stays `workspace`: a
rule that wants to tell roots apart names the path (D65). A thread names its roots at
`thread/start` (`root` alone still means one root, named after its directory) and the record
carries them; `thread/add_root` re-opens the environment on the new set — proven again — and
`WorkspaceChanged` goes on the record, between turns, like `ModeChanged`. A box
(`SandboxEnvironment`) mounts one root and refuses a re-open honestly; a second root there is
another box, later. Measured live: `second-repo` added mid-conversation; the tools' descriptions
named it; the agent read and wrote there through the sandbox (9¢).

**The environment follows the mode.** A `ModeSpec` names the environment mode it needs
(`environment`); the shipped four do, a document may. `Thread.set_mode` re-opens the
environment when that differs from the one open (`Environment.reopen`: the mechanism proves
again, `requires` refuses unchanged) before the policy flips. The record and the wire carry
`environment` beside `mode`, so a page never says `full` over a sandbox that is not. Measured
live: `read-only` after `workspace-write` — reads everywhere, no write anywhere, inside or out.

**The provider follows the mode (BUG-032).** The offered registry sends
`notifications/tools/list_changed` to every live connection (the connection registers how, on
its own stream; a gone one is dropped). Measured: Claude Code 2.1.235 kept the list it had
("my tool list still shows it") and the call failed honestly. So a mode change and a root added
reopen the provider — on its own session: `AgentPort.open(resume=)`, the Claude Code file's
`resume_args = ["--resume"]` and `session_id_at = "session_id"`, the id read off every line of
its stream and kept on the record after every turn. Measured live: reopened in `read-only`, the
model remembered the word given before the switch and listed exactly the eight tools of the
read-only registry — nothing stale, nothing lost. A behaviour change reopens the same way.

**Kept, not printed (ENH-011).** `KeepingSink` is the composition's sink: a `skill` proposal
becomes a `skills` row (D66), offered after a restart with source `store`; everything still
reaches the sink behind it. The runtime still has no write path — the host's sink writes.

**BUG-033, not reproduced.** wigolo ended with `serve` under SIGTERM to the python, SIGKILL to
the python, and SIGTERM to its parent (measured three ways, with a thread open); it exits on
stdin EOF. The orphan seen once (pid 27919) is recorded and watched for, not fixed blind.

*Why:* what a conversation works on is the product's to choose, per conversation and while it
runs (principle 10 — data changes live); and every one of the three surfaces a mode touches —
what the OS enforces, what the policy judges, what the model is told it has — must move
together, or the page lies.

---

### [DECISION] 2026-09-12 — D77: one rule, one implementation — a session leader is started in one place, frames are split in one place, and a root's name is a rule rather than a guess

Topics: processes, framing, workspace, principles, BUG-033
Affects-phases: phase-28-the-workspace
Affects-specs: architecture/runtime.md#modules

Three tightenings after the owner's standing rule (no patchwork, even in a fix), each turning a
duplicated or heuristic piece into one stated rule with a test that refuses the next copy.

**A session leader is started in one place.** Five copies of `create_subprocess_exec(...,
start_new_session=True)` + `hold(process)` — the leash (twice), the jsonl CLI session, the ACP
bridge, and the battery transport BUG-033 had just added — were one rule with five
implementations, the exact shape D35 was written against. `runtime.processes.start_held` is now
the one place; every caller calls it; an invariant walks every package's source and refuses a
`start_new_session=True` anywhere else (RED: it named all five).

**Frames are split in one place.** The wire's stdio channel and the recording adapter's pipes
each carried a buffer-and-split loop for newline-delimited JSON — and already differed (one
skipped blank lines, one did not). `runtime.lines.LineBuffer` is the one implementation: a
frame is what lies between newlines, a carriage return is not part of it, a blank line is not a
frame, what is left at end of stream is a truncated frame. Both readers use it; four mutations
(CR kept, blank lines as frames, and two more) each fail a test.

**A root's name is a rule.** `inside()` had decided whether `finance/x` meant the root named
`finance` or a directory in the primary by asking whether the literal path *existed* — a
heuristic, and one that would flip as files appeared. The rule now: another root's name wins;
the primary's own name is not an address (a repository `foo` with a package `foo/` inside keeps
meaning what it always meant); the one spelling the rule would hide — an entry of the primary
named like another root — is refused when the root is named (at open and on `add_root`), once,
rather than guessed at every path. Resolution never touches the filesystem.

*Why:* a rule with two implementations is a rule with one bug; a heuristic is a rule nobody
wrote down. The owner's rule (2026-09-12): every change to the harness, a fix included, is done
the principled way.

---

## Verification Evidence

Captured fresh 2026-09-12 on the phase branch at close, before landing:

- `uv run ruff check -q` → exit 0
- `uv run ruff format --check -q` → exit 0
- `uv run mypy` → exit 0 (`Success: no issues found in 245 source files`)
- `uv run pytest -q -p no:cacheprovider -m 'not live'` → `1392 passed, 2 skipped, 12 deselected, 85 warnings in 147.84s (0:02:27)`
- `tests/test_versions.py` → EXPECTED `0.25.0`, eighteen packages moved together (D9); `uv sync --all-packages` clean; `../harness-demo` re-synced and sees 0.25.0
- RED first, every group: group 1 `'ScriptedThreads' has no attribute 'tools'`, `no method 'tools/list'`, the parity invariant naming `Thread.tools`; group 2 a child judged with `{'posture', 'component', 'inputs'}` and no `mode`; `set(by_id)` lacking `ask`; group 3 `No module named 'shadow_hdk.kernel.workspace'`, `KeyError: 'roots'`, `[] == ['workspace_changed']`, `assert 'allow' == 'ask'` (the studio host's own pre-approving rule, the test re-aimed at `run_shell`), `assert 0 == 1` notifications heard; group 4 `No module named 'shadow_hdk.serve.keeping'`; the kernel-purity invariant refused `pathlib` in the kernel and the roots became strings
- Found by running the README's snippet for real: a relative root reached the OS profile as written and the proof said *not proven* — resolved before the proof, a test added
- Live, on the owner's subscription (Claude Code 2.1.235), through `../harness-demo/` (`shadow-hdk serve harness.toml --http --page studio/page.html`, the demo's own `pyproject.toml` over the sibling tree): eight turns in the review ($1.60) and four in the build — `second-repo` added mid-thread (`thread/add_root`): the tools named it, the agent read and wrote there through the sandbox (4 calls · 9¢); `read-only` after `workspace-write`: the sandbox followed, reads everywhere, no write anywhere, the CLI's cached list stale ("my tool list still shows it") and the call failed honestly (BUG-032 measured, 27¢); after the reopen-on-resume: the word PELICAN given in `workspace-write` remembered in `read-only`, and the model listed exactly the eight tools of the read-only registry (11¢); the `ask` mode: approve · approve-and-add-rule · deny (13¢)
- BUG-033: wigolo ended with `serve` under SIGTERM to the python, SIGKILL to the python, and SIGTERM to its parent — each with a thread open and the battery running; not reproduced

---
