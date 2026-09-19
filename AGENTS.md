<!-- momentum-managed (generated) — regenerate with `npm run generate-instructions`
     in the momentum repo; sources: core/instructions/ + adapters/<agent>/instructions/.
     Everything above '## Project Extensions' may be replaced by `momentum upgrade`. -->

# Project Rules: shadow-hdk

> Codex configuration for this momentum-managed project.

## Navigation (Where to Find Things)

| Question | File |
|----------|------|
| Current state / what phase? | `specs/status.md` |
| What's in the backlog? | `specs/backlog/backlog.md` |
| Phase tasks/progress? | `specs/phases/phase-N-*/tasks.md` |
| Why was X chosen? | `specs/decisions/NNNN-*.md` |
| Roadmap / timeline? | `specs/planning/roadmap.md` (authored at founding — `/start-project`) |
| Project config (forge, publish, branch flow)? | `specs/config.md` (inferred by `momentum init`, authored at `/start-project`) |
| How to contribute? | `docs/developer-guide.md` |

> **First file to read: ALWAYS `specs/status.md`.**

---

## Momentum Recipes — Codex Skills

Each momentum recipe ships as a native Codex skill at
`.agents/skills/<name>/SKILL.md` ([Codex skills
docs](https://developers.openai.com/codex/skills)). Codex auto-discovers
skills under `.agents/skills/` at session start across CLI, IDE, and
desktop app — so when the user invokes `/brainstorm-phase`, asks "run
brainstorm-phase", or types `$brainstorm-phase`, Codex routes directly
to that skill.

The shipped recipe set (one skill per recipe, all under
`.agents/skills/`):

| Recipe | What it does |
|---|---|
| brainstorm-idea | Explore an idea before scaffolding anything |
| brainstorm-phase | Plan the next implementation phase (gate-protected) |
| start-project | Scaffold a new spec-driven project |
| start-phase | Begin a planned phase (autonomous execution contract) |
| complete-phase | Verify, retro, release a finished phase |
| sync-docs | Propagate history entries to other spec docs |
| track | Track a backlog item (bug / feature / tech debt / enhancement) |
| review | Review and groom the backlog between phases |
| log | Append a manual narrative entry to the history of the phase bound to your branch (fallback: status.md) |
| migrate | Onboard an existing project into momentum |
| validate | Check spec structure health |
| sync-config | Re-infer project shape, show config drift, apply on approval (ENH-062) |
| ecosystem | Cross-repo ecosystem coordination |
| initiative | Manage cross-repo initiatives |
| session | Append a manual narrative entry to today's ecosystem session log |
| systematic-debug | Systematically isolate, reproduce, and resolve task execution failures |
| scout | Read-only context fetch from one ecosystem member repo |
| dispatch | Parallel multi-repo fan-out + synthesis |
| handoff | Cross-session control transfer with structured context block |
| continue | Pick up a pending handoff in this repo |
| review-code | Multi-perspective code review (uses momentum-reviewer-* subagents) |
| swarm | Sustained parallel multi-project feature delivery (uses swarm-supervisor subagent) |
| momentum-orient | Read `specs/status.md` before starting any work (Rule 1) |

Each `SKILL.md` declares `name` + `description` frontmatter and includes
the full recipe body. The recipes are platform-independent — they
describe what to do, not how Codex specifically should do it. When you
read a recipe that mentions "use the Task tool" (Claude Code
terminology), translate to Codex's equivalent: spawn the relevant
`momentum-reviewer-*` subagent (see below), or use natural-language
parallel fan-out.

> Legacy installs from momentum ≤ v0.20.0 shipped recipes as Markdown
> fragments under `.codex/commands/`. `momentum upgrade --agent codex`
> regenerates skills under `.agents/skills/` and removes the old
> lookup directory.

## Codex Subagents

Momentum ships four subagents discoverable at `.codex/agents/`:

- `momentum-reviewer-security.toml` — OWASP/STRIDE-focused
- `momentum-reviewer-qa.toml` — test coverage + edge cases + regression risk
- `momentum-reviewer-architecture.toml` — rule compliance + pattern consistency
- `swarm-supervisor.toml` — Phase 18 / v0.20.4. Per-repo supervisor spawned by `/swarm start`. Drives one repo's phase to completion under a pinned cwd (see MCP cwd shim section below).

The three reviewers each declare `sandbox_mode = "read-only"` so they
cannot modify the codebase. The `review-code` recipe dispatches all
three in a single turn so Codex can fan them out in parallel (subject
to `agents.max_threads`, default 6). The swarm supervisor does not
declare a read-only sandbox — supervisors write code, that's the job.

To add a project-specific reviewer, drop another `*.toml` into
`.codex/agents/` with required keys `name`, `description`,
`developer_instructions`. Optionally set `sandbox_mode = "read-only"` if
the subagent shouldn't modify files.

## Codex Hooks

Codex hook wiring lives in `.codex/hooks.json`. Momentum installs reusable
shell scripts to `scripts/` and references them from this file:

| Event | Matcher | Script | Purpose |
|---|---|---|---|
| `PreToolUse` | `apply_patch\|Bash` | `scripts/brainstorm-gate.sh` | Blocks writes to `specs/` while a `/brainstorm-*` session is active (sentinel `.momentum/brainstorm-active`). Exits 2 to block. |
| `PostToolUse` | `apply_patch\|Bash` | `scripts/check-history-reminder.sh` | Prompts for `history.md` append when meaningful edits land during phase work — resolved to the phase bound to the current branch (fallback: `status.md`) (Rule 8). |
| `SessionStart` | (none) | `scripts/sessionstart-handoff.sh` | Auto-greets with any pending handoff banner + ecosystem context. |

> Matcher uses `Bash` (not `shell`) because that's the canonical
> `tool_name` Codex emits for shell tool calls — see the [Codex hooks
> reference](https://developers.openai.com/codex/hooks).

### Trust review

Hooks are **enabled by default** in current Codex CLI (`hooks` is `stable`
in `codex features list`). The first time momentum's hooks run in a fresh
project, Codex prompts you to review and trust them via `/hooks`. Trust is
recorded per-hash, so any change to the hook command requires re-approval.

If hooks don't appear to fire:

1. Run `/hooks` inside Codex and confirm `brainstorm-gate.sh`,
   `check-history-reminder.sh`, and `sessionstart-handoff.sh` are listed
   and marked trusted.
2. Run `codex doctor` and confirm `hooks` shows as `stable: true`.
3. Only as a last resort, force-enable in `~/.codex/config.toml`:

   ```toml
   [features]
   hooks = true
   ```

The `brainstorm-gate.sh` script resolves the project root from
`CLAUDE_PROJECT_DIR` → `MOMENTUM_PROJECT_DIR` → `pwd`, so Codex's default
cwd-as-session-root behavior works without env-var configuration.

## Codex Skills

All momentum recipes ship as Codex skills under `.agents/skills/<name>/SKILL.md`
(see the "Momentum Recipes — Codex Skills" section above for the full
shipped set). Each `SKILL.md` declares `name` + `description` frontmatter
per the [Codex skills format](https://developers.openai.com/codex/skills).

Add additional project-specific skills under
`.agents/skills/<name>/SKILL.md` following the same convention. Invoke
via the `/skills` picker or `$<skill-name>` mention.

## Swarm — Lookup Pattern

Momentum's swarm primitive — sustained parallel multi-project feature
delivery — ships on Codex as of Phase 18 / v0.20.4. The swarm recipe
lives as a Codex skill at `.agents/skills/swarm/SKILL.md`; Codex
auto-discovers and routes `/swarm <sub>` to it.

The CLI floor is `momentum swarm <sub> [args]`. The slash command and
the CLI produce the same on-disk artifacts — pick whichever fits the
moment.

| Subcommand | What it does |
|---|---|
| `start` | Plan + spawn Wave 1. Presents wave plan for approval before any spawn. |
| `status` | Render the materialized board cache. Read-only. |
| `tell` | Push a one-shot context note to one supervisor (`swarm-context.md`). |
| `broadcast` | Push context to every supervisor in the swarm. |
| `verify` | Contract verifier + manifest+brief drift check. |
| `complete` | Synthesize the cross-repo changeset and finalize the swarm. |
| `resume` | Re-attach this session to a swarm; renews owned leases. |
| `cancel` | Graceful halt; preserves all artifacts for forensics. |
| `budget` | Adjust a per-repo token budget. |
| `claim` | Multi-session ownership primitive (Phase 17.5). |
| `release` | Release ownership; idempotent. |
| `focus` | Issue a single-use focus token to hand a repo to a side session. |
| `join` | Register a second session as co-conductor; optionally consume a token. |
| `absorb` | Converge two swarms back into one (forensic-preserving). |
| `inbox` | Supervisor → conductor questions (`list` / `write` / `resolve`). |
| `preview-merge` | Dry-run `git merge --no-commit` per supervisor branch. |

**Supervisor declaration**: `.codex/agents/swarm-supervisor.toml`. Each
supervisor reads `core/swarm/supervise.md` end-to-end on boot. The
conductor (this user session) dispatches spawns through
`adapters/codex/adapter.js::spawn(directive)` — which shells
`codex --cwd <repoPath>` with the supervisor TOML.

If `codex` CLI isn't on PATH, `momentum swarm start --spawn` degrades
to dry-run: it prints the spawn directives so the user can launch
sessions manually.

## MCP cwd shim — Codex configuration

> Phase 18 / v0.20.4. Required for the swarm primitive to honor the
> per-repo cwd pin every supervisor needs.

Each supervisor must run with its `repoPath` as its working directory —
that's the hard invariant the supervise.md recipe is written against
(every "stay in repoPath, never cd out" guard in `swarm-supervisor.toml`).

Codex's CLI accepts `--cwd <path>` for each `codex` invocation, so the
conductor's spawn call honors cwd at process boundary. Inside a
supervisor session, momentum relies on Codex's MCP filesystem server to
keep file ops scoped to that cwd — which means you (the user) configure
the MCP filesystem server's `--root` to follow `$PWD`.

In `~/.codex/config.toml` add:

```toml
[mcp_servers.filesystem]
command = "npx"
args    = ["-y", "@modelcontextprotocol/server-filesystem", "${PWD}"]
```

(See [Codex MCP servers](https://developers.openai.com/codex/mcp) for
the canonical form. `${PWD}` is interpolated by Codex at server-spawn
time, so each supervisor sees its own pinned `repoPath` as the
filesystem server root.)

**Verifying the shim**: inside a supervisor session, run:

```bash
pwd
ls -la
```

You should see `repoPath` and the repo's top-level contents, not the
ecosystem root. If you see the ecosystem root, the shim isn't applied —
exit and reconfigure before launching supervisors.

**If the doc-only shim doesn't hold on your Codex version**: file a
bug against momentum and fall back to running each supervisor in a
separate terminal with `cd <repoPath> && codex …` — a manual cwd pin.
This is the documented escalation point referenced in Phase 18 G1
plan.md; if the MCP shim is widely broken, momentum will ship a
minimal `core/swarm/mcp-cwd-server.js` in a follow-up.

## In-Session Task Tool

When a rule mentions tracking in-session progress (Rule 2), Codex's task tool is the built-in **plan** tool — in-session only; the durable record is `specs/phases/<phase>/tasks.md`.

## Autonomous Behaviors (Always-On Rules)

### Rule 1: Always Orient First

Before ANY work, read `specs/status.md`. This tells you:
- What phase is active
- What's blocking progress
- What P0 items need attention

If `status.md` says **Not founded**, stop: the project has no charter or
roadmap yet — foundation docs are authored at founding, never scaffolded
(`core/project-lifecycle.md`). Route to `/start-project` before any phase work.

### Rule 2: Auto-Update Tracking After Changes

After completing ANY meaningful work, automatically update:

1. **Your phase's `tasks.md`** (the phase bound to your branch — Rule 15) — mark completed `[x]`, in-progress `[/]`
2. **`specs/status.md`** — if phase progress, blockers, or P0 items changed (touch only your own lane's row — Rule 15)
3. **`specs/changelog/YYYY-MM.md`** — log what changed (one line per change, append-only)

Use your in-session task-tracking tool (named in the "In-Session Task Tool" note above) to track in-session task progress. Do NOT wait for the user to ask you to update tracking.

#### Why
Tracking debt compounds invisibly. A task list one day stale is recoverable; one week stale is fiction. Status drift is how phases silently lose direction.

#### Red Flags — STOP and update tracking now

| If you find yourself thinking… | …STOP and update before doing anything else |
|---|---|
| "I'll batch the tracking updates at the end" | The end never comes — context fades and details get lost |
| "This change is too small to log" | Small changes accumulate into invisible drift |
| "The diff makes it obvious what changed" | The diff shows *what*; the changelog explains *why* |
| "The user can read git log" | Git log doesn't index by phase or backlog ID |
| "I'll log this as part of the next bigger update" | Bigger updates conflate decisions and lose per-step reasoning |

#### Anti-Rationalization Counters

- "It's faster to do the work first and track at the end" — wrong: reconstruction takes 2-3× longer than real-time logging.
- "Your in-session task-tracking tool is enough" — it is in-session only; `tasks.md` is the durable record.
- "Mid-task tracking interrupts flow" — a one-line update costs <30s; reconstructing a day later costs 30 minutes.

### Rule 3: Auto-Track Discoveries

When you discover a bug, tech debt, or enhancement during work:
- Add it to `specs/backlog/backlog.md` immediately with appropriate priority
- Mention it to the user: "I found [issue] and added it as [ID] to backlog"

### Rule 4: Pre-Phase Bug Check

Before starting work on a new phase:
- Scan `specs/backlog/backlog.md` for P0/P1 bugs
- If any exist, recommend addressing them first
- Present: "N open bugs (X critical), recommend fixing before proceeding"

Also run `momentum learnings` and report what it finds:
- **Recurring classes** — "class X has recurred N times". A defect class that
  keeps returning is worth a phase, not another one-off fix.
- **Stale closures** — rows still marked `open` whose work the code says landed.
  This check exists because Rule 4 reads the backlog to decide what to fix
  first, so a stale entry sends the phase chasing something already done.

Both are **advisory inferences, not measurements**. Report them; never flip a
status or accept a proposal on their say-so. Verify first — a hand audit of this
project's own backlog once reported seven stale entries with two P0/P1s when the
truth was four and none.

Starting a phase while other lanes are active is normal (Rule 15) — the bug
check still runs per phase start.

### Rule 5: Phase Boundary Awareness

When completing the last task in a phase:
- Prompt the user: "All tasks in Phase N are complete. Run `/complete-phase` to verify and release?"
- Do NOT auto-complete a phase without user confirmation
- "Complete" means the phase bound to YOUR branch (Rule 15); landing it on
  `main` follows the Rule 6 landing order when other lanes are in flight

### Rule 6: Git Lifecycle

> **Enforced vs advised.** momentum installs git hooks that *enforce* the
> high-stakes parts of this lifecycle (see `core/lifecycle-contract.md`):
> `commit-msg` validates Conventional Commits; `pre-push` blocks direct pushes
> to `main`/`staging` without the single-use `.momentum/merge-approved`
> sentinel, and blocks release-tag pushes lacking verification evidence
> (Rule 12). Hooks install to `.githooks/` via `core.hooksPath`. Emergency
> bypass (auditable, preferred over `--no-verify`): `MOMENTUM_SKIP_HOOKS=1`.
> Everything else below is agent convention, not mechanism.
>
> *Optional hardening:* enable your forge's server-side branch protection
> (GitHub Rulesets / GitLab protected branches / Bitbucket permissions) as an
> unbypassable backstop. momentum stays forge-neutral and ships no forge code.

#### Starting Work
- **Before ANY code change**, check current branch
- If on `main` or `staging`, **auto-create a feature branch**:
  - Phase work: `phase-N-shortname`
  - Bug fix: `fix/BUG-NNN-short-desc`
  - Feature: `feat/short-desc`
  - Tech debt: `refactor/TD-NNN-short-desc`

#### During Work
- **Auto-commit** after each logical unit with conventional commits:
  - `feat(scope):` | `fix(scope):` | `docs:` | `refactor(scope):` | `chore:` | `infra:`
- Keep commits atomic — one logical change per commit
- Push to remote after significant milestones

#### Completing Work
- Commit all remaining changes, push branch
- **ASK the user** before merging to `staging` or `main`

| Action | Agent does automatically | Needs approval | Hook enforcement |
|--------|--------------------------|----------------|------------------|
| Create feature branch | Yes | No | — (convention) |
| Commit to feature branch | Yes | No | `commit-msg` validates the message |
| Push feature branch | Yes | No | `pre-push` allows (non-protected) |
| Delete merged feature branch | Yes (after confirmed merge) | No | `/complete-phase` step 13 |
| Merge to `staging`/`main` | No | **Yes** | `pre-push` **blocks** without `.momentum/merge-approved` |
| Tag a release | No | **Yes** | `pre-push` **blocks** without verification evidence |

#### Landing Order — Concurrent Lanes (Rule 15)

When more than one lane is in flight, `main` is the runway — lanes land
**one at a time**:

1. One lane merges (with its approval gate above).
2. The full suite runs green on the updated `main` **before** the next landing.
3. Remaining lanes **rebase onto the updated `main`** before they land.
4. Stacked (dependent) lanes land parent-first; a child rebases onto its
   parent until the parent lands, then onto `main`.

Never land two lanes back-to-back without the suite passing in between — a
green suite on each lane's branch does not prove the *combination* is green.

#### Why
Direct commits to `main` bypass review, history, and rollback. A single rushed commit on `main` is harder to revert than ten commits on a branch. The branch convention is the cheapest possible insurance against catastrophic mistakes.

#### Red Flags — STOP and check the branch

| If you find yourself thinking… | …STOP and switch to a branch |
|---|---|
| "Just one tiny commit to main" | One becomes ten — branch first, decide later |
| "I'll create the branch after these edits" | The edits are the work; the branch is non-optional |
| "The hook is in the way, --no-verify just this once" | The momentum hooks are real now. Fix the cause; for a genuine emergency use the auditable `MOMENTUM_SKIP_HOOKS=1`, never blanket `--no-verify`. |
| "Force push is fine, nobody else is on this branch" | Future you is on this branch. `--force-with-lease` at minimum. |

#### Anti-Rationalization Counters

- "It's a one-line typo fix on main" — branches are free; revert is cheap; main is sacred.
- "The branch protection isn't set up yet" — that's a reason to be more careful, not less.
- "I'll squash-merge later, so the intermediate commits don't matter" — they matter for `git bisect` and for narrating *why*.

### Rule 7: Plan Before Implementing

For any non-trivial implementation (new feature, architectural change):
- Use `/brainstorm-phase` to design the approach first
- Present the plan for user approval before making changes

### Rule 8: Record Phase History

While working on a phase, append meaningful changes to that phase's history log — `specs/phases/<phase-bound-to-your-branch>/history.md` (Rule 15; each lane writes only its own history).

#### What counts as "meaningful"

Append a history entry when ANY of these occur:

| Trigger | Entry type |
|---|---|
| ADR was created or its status/decision changed | `[DECISION]` |
| Phase scope was added to or reduced | `[SCOPE_CHANGE]` |
| Bug, tech debt, or enhancement was added to backlog | `[DISCOVERY]` |
| New feature was added to the phase plan | `[FEATURE]` |
| Architectural pattern or integration approach changed | `[ARCH_CHANGE]` |
| Locked evaluator was defined or its evaluation set changed | `[EVALUATOR]` |
| Anything else worth a future reader's time | `[NOTE]` |

After writing a history entry, check `specs/decisions/impact-map.md` and add any new topics so `/sync-docs` can find affected files.

The hook script `scripts/check-history-reminder.sh` runs after edits as a safety net — heed its prompts.

#### Format (APPEND ONLY)

```
### [TYPE] YYYY-MM-DD — Short title
Topics: topic-1, topic-2
Affects-phases: phase-N-name (or "none")
Affects-specs: path/to/file.md#section (or "none")
Detail: One to three sentences describing what changed and why.

---
```

#### Why
The history log is the only place that preserves *why* a decision was made at the moment it was made. Specs document the current state; commits document mechanical changes; only history captures motivation. Without it, six months later nobody can reconstruct whether a constraint is load-bearing or accidental.

#### Red Flags — STOP and log

| If you find yourself thinking… | …STOP and append the entry now |
|---|---|
| "I'll write the history at the end of the phase" | You won't remember the *why*. Log when the decision is fresh. |
| "This decision isn't important enough to log" | If it's not worth logging, it's not worth deciding — log it or revert it. |
| "I already mentioned it in the commit message" | Commit messages get buried; history.md is the canonical source. |
| "The change is obvious from the diff" | Diffs show *what*; history shows *why*. |

#### Anti-Rationalization Counters

- "We didn't decide anything — just discovered an issue" — that's `[DISCOVERY]`, log it.
- "It's a minor scope tweak, not a real `[SCOPE_CHANGE]`" — every scope change is real, log it.
- "I'll consolidate entries later" — consolidation loses per-decision context.

### Rule 9: Doc Sync Protocol — Never Mid-Phase, Always at Completion

- **During a phase**: Record to history. Do NOT update other specs.
- **At phase completion**: Run `/sync-docs` BEFORE `/complete-phase`.

#### Multi-repo projects only

If this project depends on, or is depended on by, other repos in a parent workspace:
- NEVER modify docs that live in another repo during `/sync-docs`. You only own this repo's docs.
- If a history entry's `Affects-specs:` path starts with `../` (or otherwise points outside this repo), leave that file alone.
- Flag the cross-repo impact to the user — give the exact path — so they can sync the other repo manually.
- Cross-repo doc ownership is a structural choice. Never quietly change docs you don't own.

### Rule 10: Architecture Specs Stability (monorepo only)

Files under `specs/architecture/` are constitutional documents. Treat them as a stable reference *during* phase work. The key distinction is **additive bookkeeping** vs **architectural decisions**.

**During phase implementation (both types — no spec changes):**
- READ specs as stable reference
- NEVER modify them based on implementation discoveries
- Log all gaps and changes as `[ARCH_CHANGE]` in phase history with `Affects-specs:`

**At phase completion (via `/sync-docs`):**
- **Additive changes** (new fields, new ports, new modes — extending an existing design): update specs directly. No ADR required.
- **Decisional changes** (approach changes, trade-off choices, design direction shifts): require an ADR amendment **before** any spec update.

#### Why
The original "all spec changes via ADR" rule worked when the architecture was stabilizing and every change was a decision. By mid-to-late phases, the architecture is proven — most changes are additive extensions, not decisions. Requiring ADRs for bookkeeping creates spec staleness while adding no value. ADRs capture *why* a path was chosen; they're not required when you're just recording *what was added*.

#### Red Flags — STOP and route correctly

| If you find yourself thinking… | …STOP |
|---|---|
| "I just need to update one field, not a real change" | Additive — fine at completion; not now. Log `[ARCH_CHANGE]`. |
| "It's faster to fix the spec than to log the gap" | Faster locally, catastrophic globally — specs out of sync with rationale. |
| "The implementation diverged because the spec was wrong" | That's a decision — ADR first, spec update second. Don't silently rewrite. |
| "I'll log it as `[NOTE]` instead of `[ARCH_CHANGE]`" | If it touches `specs/architecture/`, it's `[ARCH_CHANGE]`. |

#### Anti-Rationalization Counters

- "Specs are wrong, code is right, so update specs" — only after an ADR documents *why* the design shifted.
- "Mid-phase spec edits are fine if I'm careful" — the rule isn't about care; it's about preventing reference instability while you're depending on the reference.
- "This is just renaming, not redesigning" — renames are decisions when others read the spec.

### Rule 11: Evaluator Discipline — Lock Evaluators Before Loops

Before building any learning, optimization, or self-improvement loop:

1. Define the **evaluation set** — a fixed corpus with known-good outputs
2. Define the **scalar** — a single number that improves or doesn't
3. Commit the evaluator to `tests/benchmarks/` with a version tag
4. Build the loop **AFTER** the evaluator is committed
5. **NEVER** change the evaluator while the loop is being optimized

#### Why
Optimization loops with mutable evaluators don't measure progress — they measure motion. Every "small fix" to the eval set silently rewrites the score history and makes A-vs-B comparisons meaningless. Locking the evaluator first costs an hour; not locking it costs the entire experiment.

#### Red Flags — STOP and freeze

| If you find yourself thinking… | …STOP |
|---|---|
| "Just one tweak to the eval so this run looks better" | That's exactly the failure mode. Freeze first; tweak in a v2 evaluator. |
| "We'll lock the evaluator after we know what works" | You can't know what works without a locked evaluator. |
| "The current eval doesn't measure what we actually care about" | Correct — but freeze it before optimizing, then version-bump to a new locked eval. |
| "It's just an internal experiment, locking is overkill" | Internal experiments produce internal beliefs that drive external decisions. Lock. |

#### Anti-Rationalization Counters

- "The eval set is too small, I'll just add a few more cases" — version-bump the evaluator (`v1` → `v2`); don't mutate `v1`.
- "I noticed a bug in the scorer mid-run" — fix it in `v2`; rerun the prior runs against `v2`; don't backfill `v1` scores.
- "Production data drifted, I should refresh the eval" — that's a `v2` decision, not a `v1` patch.

### Rule 12: Verify Before Claim — No Completion Without Evidence

Before claiming any task, fix, or implementation is "done":

1. Run the actual verification command (test, lint, typecheck, smoke test, build)
2. Read the output — both exit code and content
3. If the output isn't fresh from this attempt in this session, treat the task as unverified
4. Only mark a task `[x]` after a verification command produced passing output in this session

#### Why
The most common agentic-workflow failure is "should work now" — claiming completion based on intent rather than evidence. Fresh, observable output is the only signal that the change actually achieves what was claimed. Box-checking without verification compounds across phases until shipped releases contain unrun code paths.

#### Red Flags — STOP and run the verification

| If you find yourself thinking… | …STOP and run the verification before marking done |
|---|---|
| "I'm confident this works — no need to test" | Confidence is not evidence. Run the test. |
| "The change is small enough that I can skip verification" | "Small" is the most common predicate of a regression. Run it. |
| "I already tested something similar earlier" | Earlier ≠ now. Re-run against the current code. |
| "The unit tests pass — that's enough" | Unit tests don't catch wiring bugs. Run the integration / smoke path too. |
| "I'll batch verifications at the end of the phase" | At the end you can't tell which change caused which failure. Verify per-task. |

#### Anti-Rationalization Counters

- "The diff is obviously correct" — diffs lie when context is incomplete. Run the test.
- "The CI will catch any issue" — CI catches it after you claimed done; that's the failure mode this rule prevents.
- "Type checking passed, so it works" — types catch shape errors, not behavior. Run the runtime check.
- "I read the code carefully and it looks right" — careful reading misses race conditions, missing imports, off-by-one bugs. Verification commands don't.
- "The previous task was similar and that worked" — previous ≠ current. Each task gets its own verification.

If a verification command does not exist for the task, write one before marking done. If a command can't run in the current environment, say so explicitly — do not silently downgrade to "looks correct".

---

### Rule 13: Test-Driven Development (TDD) — Opt-in

If enabled in the project rules extensions (under `## Project Extensions` in this file), follow a strict test-first development loop:

1. **Red**: Write a unit or integration test that specifies the new behavior *before* writing any application code.
2. **Verify Failure**: Run the test runner and verify that the newly added test fails. Do not write any implementation code until you have seen the test fail.
3. **Green**: Write the minimal application code necessary to make the test pass.
4. **Refactor**: Clean up and optimize the code while keeping all tests green.

#### Red Flags — STOP and write the test first

| If you find yourself thinking… | …STOP |
|---|---|
| "I will write the tests at the end" | Post-facto tests are not TDD — they inherit confirmation bias from the implementation. |
| "The change is too simple to warrant a test-first approach" | Simple changes are excellent TDD candidates to establish correct wiring. |

### Rule 14: Work-Type Escalation — Pick the Lightest Type That Fits

Not every change is a phase. momentum has three work types (see
`specs/adhoc/README.md`):

| Type | When | How |
|---|---|---|
| `phase` | Net-new features; cross-cutting or architectural work | `/brainstorm-phase` → `/start-phase` → … → `/complete-phase` |
| `quick-task` | A bounded bugfix / chore / audit / dependency bump | `/hotfix` — ad-hoc record + Rule 12 gate, no phase scaffold |
| `spike` | Time-boxed, throwaway exploration | `/hotfix --spike` — declared, gate-exempt, record what was learned |

**Governing principle:** select the lightest work type that fits; escalate only
when scope/risk/cross-cutting impact justifies it. (Per Anthropic's "build the
simplest thing first; add structure only when it demonstrably helps.")

**A quick-task MUST escalate to a phase when it:** touches more than ~5 files of
production code, modifies anything under `specs/architecture/`, needs an ADR,
changes a public contract/interface, or displaces a planned phase.

#### Red Flags — STOP and escalate (or de-escalate)

| If you find yourself thinking… | …STOP |
|---|---|
| "This `/hotfix` is growing — I'll just keep going" | If it now touches architecture or many files, it's a phase. Escalate. |
| "I'll spin up a whole phase for this one-line fix" | Over-ceremony. A `/hotfix` quick-task is the right size. |
| "It's exploratory but I'll ship it straight to main" | A spike is gate-exempt *because* it's throwaway. Harden it as a quick-task first. |

### Rule 15: Concurrent Workstreams — Lanes

Multiple workstreams may be active in one repo at the same time (see
ADR-0001). A **lane** is one workstream: a branch (usually in its own
worktree) bound to one phase or ad-hoc record.

#### Lane binding — which phase is yours

- Your phase is **the phase bound to your branch**: branch
  `phase-N-shortname` ↔ directory `specs/phases/phase-N-shortname/`.
- `specs/status.md`'s Active Phase table is the **fallback and the
  cross-lane overview** — read it to see what else is in flight, not to
  decide which phase is yours.
- Non-phase branches (`fix/*`, `chore/*`, `feat/*`) bind to the ad-hoc lane
  (`specs/adhoc/`, Rule 14). Detached HEAD → fall back to `status.md`.

#### Lane-scoped tracking

- Write ONLY your own phase's artifacts (`tasks.md`, `history.md`,
  `evidence/`) — these are parallel-safe by construction.
- Shared tracking files (`status.md`, `backlog.md`, `changelog/`) are
  **append / own-row-touch only** from a lane: add or edit your own
  row/line; never reformat, renumber, or rewrite other lanes' entries.
- The Active Phase table holds **one row per active lane**
  (Phase | Branch | Status | Progress). Add your row at phase start; update
  only your row; mark it at completion.
- **Across machines (Team Mode, v0.37.0+):** this convention is now backed by a
  *mechanism*, not only discipline — per-actor coordination fragments
  (`.momentum/team/`, collision-free by own-prefix construction) + `refs/momentum/*`
  compare-and-swap for allocation (`momentum claim <phase|id|version>`).
  `momentum team sync`/`board` compile the shared view. This makes **N humans on
  N clones** trivially mergeable, not just N sessions on one disk; the social
  discipline above is the fallback. See ADR-0012/0013/0014.

#### Landing

Lanes integrate per the Rule 6 **Landing Order** — one lane at a time, suite
green on updated `main` between landings, remaining lanes rebase.

**Mechanism:** `momentum lanes` — open/board/queue/signal/inbox/done/land
(see the `/lanes` recipe). The board shows every lane + queue pressure from
any session; `lanes land` enforces turn, rebase-freshness, and the
Rule-14-graded evidence gate before merging.

#### Off-lane work

Brainstorms and spikes are **off-lane** — zero tracking contention by
design. `/brainstorm-idea` writes no files; a spike writes only its own
`specs/adhoc/<id>/` record. Neither touches the Active Phase table.

#### Why
Two concurrent sessions cannot both be right about "the active phase" when
the spec layer models exactly one. Binding phase to branch makes each
session's context unambiguous, and append-only discipline on shared files
keeps N lanes trivially mergeable. Git isolation (worktrees) was never the
problem — the spec layer was.

#### Red Flags — STOP and re-scope to your lane

| If you find yourself thinking… | …STOP |
|---|---|
| "I'll just fix this line in the other phase's tasks.md while I'm here" | That's another lane's artifact. Leave it; tell the user or file a backlog item. |
| "status.md is stale for that other lane, I'll update their row" | Their session owns that row. Touch only your own. |
| "I'll reformat the Active Phase table while adding my row" | Reformatting rewrites every lane's row — append yours, change nothing else. |
| "Which phase am I on? I'll take status.md's first row" | Your branch decides your phase. status.md is the overview, not the binding. |
| "Both lanes are done, I'll merge them together to save a suite run" | One at a time; suite green between landings (Rule 6 Landing Order). |

#### Anti-Rationalization Counters

- "The other lane's edit is tiny and obviously right" — cross-lane edits are how tracking corrupts; smallness is irrelevant.
- "Rebasing my lane again is wasted work" — rebasing is the price of a green runway; a stale lane landing on moved `main` is how combination bugs ship.
- "There's only one lane active right now, Rule 15 doesn't apply" — a single lane is the N=1 case; the binding still defines which phase is yours.

---

## Naming Conventions

### Backlog IDs
| Type | Prefix | Example |
|------|--------|---------|
| Bug | `BUG-` | `BUG-001` |
| Feature | `FEAT-` | `FEAT-001` |
| Tech Debt | `TD-` | `TD-001` |
| Enhancement | `ENH-` | `ENH-001` |

### Priorities
| Level | Meaning | SLA |
|-------|---------|-----|
| `P0` | Critical — blocks current phase | < 1 day |
| `P1` | High — current/next phase | < 1 week |
| `P2` | Medium — within 2 phases | < 1 phase |
| `P3` | Low — nice to have | best-effort |

### Git Branches
| Type | Pattern |
|------|---------|
| Phase | `phase-N-shortname` |
| Feature | `feat/description` |
| Bug fix | `fix/description` |
| Refactor | `refactor/description` |
| Infrastructure | `infra/description` |
| Delete after merge | `git push origin --delete <branch>` once merged |

### Git Commits (Conventional)
`feat:` | `fix:` | `docs:` | `refactor:` | `chore:` | `infra:`

Also accepted by the `commit-msg` hook: `test:` `perf:` `build:` `ci:` `style:` `revert:` (standard Conventional-Commit types). Scope and breaking-change `!` are optional, e.g. `fix(install)!: …`.

Use `infra:` for CI, build, deploy, tooling, and release-pipeline changes that don't ship code.

---

## Constraints

1. **No secrets in code** — all credentials via env vars
2. **Never commit to main** — always use feature/phase branches
3. **Plan before implementing** — use `/brainstorm-phase` for non-trivial work

---

## Project Extensions

<!-- momentum:project-rules-pointer -->
> **Project-specific rules live in `specs/project-rules.md`** — read it now.
> Session-start self-audits, project constraints, and any project-specific
> guidance are there, shared identically by every agent (ADR-0010). This
> section is a momentum-managed pointer; edit `specs/project-rules.md`, not
> this file.
