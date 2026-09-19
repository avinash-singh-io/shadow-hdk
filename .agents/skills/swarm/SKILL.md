---
name: swarm
description: "Swarm — sustained parallel multi-project feature delivery (Phase 18, Codex parity). Activates when the user invokes /swarm or asks momentum to run the swarm recipe."
---

Swarm — sustained parallel multi-project feature delivery (Phase 18, Codex parity).

A **swarm** is a declared cross-repo work unit driven from ONE user session. The user's session becomes the **conductor**. The conductor spawns one **supervisor** Codex session per impacted repo, each pinned to that repo's working directory (cwd) via the MCP cwd shim (see AGENTS.md → `## MCP cwd shim — Codex configuration`). Each supervisor runs momentum's normal `/start-phase` → implement → `/sync-docs` → `/complete-phase` loop INSIDE its repo. The conductor coordinates waves (computed from `ecosystem.json` dependency edges), surfaces inbox decisions, broadcasts cross-cutting concerns, and synthesizes per-repo retrospectives at fan-in.

> Phase 18 / v0.20.4 — Codex parity of the Phase 17 / 17.5 swarm surface that originally shipped Claude Code only. All 13 subcommands work through the Codex `adapter.spawn(directive)` dispatch (`adapters/codex/adapter.js`).

> **⚠ DEPRECATED — the wave runner, not the whole subsystem (Phase 32a, BUG-031).**
> `--mode autopilot`'s wave advance has **never had a production caller**:
> `pollTurn` and `recordRepoComplete` are referenced only by tests, there is no
> `poll` subcommand, and wave-1 spawn directives are the only ones ever built.
> Launch a swarm today and the board freezes at wave-1-start. It is **not being
> repaired** — even wired it drives one phase per repo, which the
> tier-parameterized runner (`momentum run`, Epic 0001) supersedes; removal
> lands in **Phase 32d**. The **inbox protocol** and **wave ordering** are
> retained and already in use by the new runner. For multi-phase or multi-repo
> autonomous work, use `momentum run`.

## Architecture

| Layer | Owns | Reads |
|---|---|---|
| Conductor (this user session) | `<eco>/swarms/<id>/manifest.json` + `board.json` + `contracts/` + `inbox/` + `signals/` + `changes/` | Per-supervisor `dispatch-run-<id>.json` (status) |
| Supervisor (per repo, fresh Codex session pinned to repo cwd) | `<repo>/specs/phases/phase-N-<slug>/*` + `<repo>/.momentum/runs/dispatch-run-<id>.json` | Its phase brief + contract + history.md tail |

Agents are stateless across turns; **state lives in files**. A swarm survives session boundaries the same way a phase does — every state-changing action writes to disk; `/swarm resume` reconstitutes from disk.

## When to use

- A feature spans **two or more momentum-installed repos** AND has dependency ordering (frontend depends on backend depends on shared-types).
- The user wants ONE Codex session driving the whole feature, not three serial sessions.
- An initiative exists or is about to exist at `<eco>/initiatives/<slug>.md`.

Do NOT use `/swarm` for:
- Read-only cross-repo audits — use `/dispatch`.
- Single-repo phases — use `/start-phase` directly.
- Pure context transfer — use `/handoff`.

## Codex specifics

- **Supervisor declaration**: `.codex/agents/swarm-supervisor.toml` (Codex subagent). Each supervisor reads `core/swarm/supervise.md` end-to-end on boot.
- **cwd pinning**: per-supervisor cwd is honored via the MCP filesystem server (`## MCP cwd shim — Codex configuration` in AGENTS.md). Without the shim, every supervisor would see the conductor's cwd — a hard supervise.md invariant violation.
- **Spawn dispatch**: the CLI floor (`momentum swarm start --spawn …`) dispatches each spawn directive through `adapters/codex/adapter.js::spawn()`. The adapter shells `codex --cwd <repoPath>` with the supervisor TOML as the agent declaration.
- **Hook integration**: `apply_patch|Bash` matchers in `.codex/hooks.json` apply uniformly inside each supervisor. The brainstorm gate keeps supervisors from drifting into spec edits during phase implementation.

## Subcommands

The slash command form mirrors the CLI: `/swarm <sub> [args]`. The CLI floor is `momentum swarm <sub> [args]` — pick whichever door fits the moment. Both produce the same on-disk artifacts.

---

### `/swarm start <slug> --initiative <slug> --repos r1,r2,... --phase <phase-slug> [--mode checkpoint|autopilot]`

Plan + spawn Wave 1.

**Step 1 — Present the plan and ask for approval.**

Compute the wave plan in-process (no spawn yet) by calling the CLI floor in dry-run:

```bash
momentum swarm start <slug> --initiative <slug> --repos r1,r2,... --phase <phase-slug> --mode <mode> --json
```

Read the JSON. Render the wave plan to the user:

```
▸ Swarm <NNNN-slug> — planned (not yet spawning)
  Initiative: <slug>
  Mode: <mode>
  Waves:
    Wave 1: <r1>, <r2>
    Wave 2: <r3>
    Wave 3: <r4>
  Token budget: 300k per supervisor (override with /swarm budget)
  Lease: 24h per repo, renewed each turn

Proceed?
```

WAIT for user approval. If `mode = autopilot`, plan approval is the only checkpoint until completion. If `mode = checkpoint`, you'll also pause between waves.

**Step 2 — Spawn Wave 1 supervisors via the Codex adapter.**

After approval, run:

```bash
momentum swarm start <slug> --initiative <slug> --repos ... --phase <phase-slug> --mode <mode> --spawn
```

`bin/swarm.js` dispatches each directive through `adapters/codex/adapter.js::spawn()`, which shells `codex --cwd <repoPath>` with the supervisor TOML as the subagent declaration. If `codex` is not on PATH, the CLI surfaces the spawn directives and exits non-zero — degrade by reporting the directives to the user (they can launch sessions manually) and continue with conductor polling on the existing manifest.

**Step 3 — Begin the conductor poll loop.**

See `/swarm status` (next subcommand). On every conductor turn:

1. Read `<eco>/swarms/<id>/board.json` (≈3KB).
2. Read `<eco>/swarms/<id>/inbox/INDEX.md`.
3. If `inbox_count > 0`, surface each pending item; resolve interactively.
4. If a supervisor reports `done: true` for the active wave's last repo, run the wave checkpoint flow (`/swarm verify`).

---

### `/swarm status <swarm-id>`

Render the materialized board cache. Read-only — no manifest mutation. Strategy A from the indexing design: conductor reads ONLY `board.json` (~3KB).

```bash
momentum swarm status <swarm-id>
```

Default output is a rendered ANSI table. Pass `--json` for machine-readable.

Surface:
- Per-repo: wave, status, tasks N/M, tokens used/budget, commits, current task.
- `inbox_count` warning at the bottom if > 0.
- Recent activity tail (last 10 audit events).

When inboxes are pending, prompt: "Run `/swarm verify <id>` to surface the questions, or `/swarm tell <id> <repo> '...'` to push context to a specific supervisor."

---

### `/swarm tell <swarm-id> <repo> "<text>"`

Push a one-shot context note to a specific supervisor. The text lands at `specs/phases/<phase-slug>/swarm-context.md` inside the target repo — supervisors read this file at the top of every turn.

```bash
momentum swarm tell <swarm-id> <repo> "<text>"
```

Use when one supervisor needs context the others don't (e.g., "the auth contract was just updated to v3 — your contract.json target should bump to match"). For cross-cutting context, use `/swarm broadcast`.

---

### `/swarm broadcast <swarm-id> "<text>"`

Push context to every supervisor in the swarm. Appends `## broadcast @ <ts>` blocks to each repo's `swarm-context.md`.

```bash
momentum swarm broadcast <swarm-id> "<text>"
```

Use sparingly — broadcast costs each supervisor a context-fetch turn. Prefer `/swarm tell` for repo-specific notes.

---

### `/swarm verify <swarm-id>`

Run the contract verifier + manifest+brief drift check. Read-only. Exits non-zero if any drift surfaces; meant as the pre-/swarm-complete gate.

```bash
momentum swarm verify <swarm-id>
```

Checks:
- Manifest schema validates.
- Initiative back-reference exists at `<eco>/initiatives/`.
- Every supervisor brief carries the matching swarm frontmatter (swarm, wave, initiative).
- Every `contracts/*.contract.json` has surface/owner/consumers/version/content_hash.

Pending inbox items are advisory, not failures.

---

### `/swarm complete <swarm-id>`

Synthesize the cross-repo changeset and finalize the swarm. Writes `<eco>/changes/<swarm-id>.md` summarizing per-repo contributions (wave, branch, phase slug, tasks done, commits). Flips manifest status to `complete` once every repo reports complete; otherwise leaves the manifest status as-is and reports partial completion.

```bash
momentum swarm complete <swarm-id>
```

Run AFTER `/swarm verify` shows OK.

---

### `/swarm resume <swarm-id> [--session <id>]`

Re-attach the current session to an existing swarm — reconstitutes the conductor state from `<eco>/swarms/<id>/manifest.json` + `board.json` and renews any leases the session owns.

```bash
momentum swarm resume <swarm-id> [--session <id>]
```

Use when:
- The conductor session was killed mid-swarm.
- A user wants to take over a swarm from a previous session (combine with `/swarm join` for explicit handoff).

---

### `/swarm cancel <swarm-id> [--reason "<text>"]`

Graceful halt. Halts every supervisor, marks the swarm `cancelled` in the manifest, preserves all artifacts for forensics.

```bash
momentum swarm cancel <swarm-id> --reason "<text>"
```

**Confirm with the user before running.** Cancel is reversible only via `/swarm resume` re-attaching to a frozen state — you cannot un-cancel a wave that was mid-flight if commits have been pushed and force-overwrites would be needed.

After cancel:
1. All queued/running/blocked repos move to `cancelled`.
2. All queued/running waves move to `cancelled`.
3. Branches remain — supervisors do NOT force-push or delete.
4. Audit log gains a `cancel` entry with the reason.

---

### `/swarm budget <swarm-id> <repo> +N | -N`

Adjust the per-repo token budget. Tokens are advisory — the conductor reports a `budget` audit entry and the supervisor uses the budget to scope subsequent turns.

```bash
momentum swarm budget <swarm-id> <repo> +100000
momentum swarm budget <swarm-id> <repo> -50000
```

---

### `/swarm claim <swarm-id> <repo> [--session <id>] [--lease-hours 24]`

> Phase 17.5 / v0.20.2 — multi-session ownership primitive.

Claim ownership of `<repo>` inside `<swarm-id>` for the current session. The conductor library uses this whenever a session needs authority to write to a repo's manifest entry — `/swarm focus`, `/swarm join`, and a co-conductor taking a wave all compose `claim` under the hood.

```bash
momentum swarm claim <swarm-id> <repo> [--session <id>] [--lease-hours 24]
```

Claim succeeds when:
- the repo is `_unclaimed` or `_focusing` (sentinel — anyone may claim), OR
- the current owner's `lease_expires_at` is in the past (takeover; audit logs both `claim` and `lease-takeover`).

Claim is rejected when the current owner's lease is still valid; the CLI writes a `claim-request` signal so the existing owner sees the request on their next conductor poll. Exit code 1 on rejection.

---

### `/swarm release <swarm-id> <repo> [--session <id>]`

> Phase 17.5 / v0.20.2 — multi-session ownership primitive.

Release the current session's ownership of `<repo>`. Sets `owner = _unclaimed`, clears the lease, and audit-logs `release`. Idempotent — releasing an already-unclaimed repo is a no-op.

```bash
momentum swarm release <swarm-id> <repo> [--session <id>]
```

Only the current owner may release.

---

### `/swarm focus <swarm-id> <repo> [--session <id>] [--expires-min 60]`

> Phase 17.5 / v0.20.2 — split one repo off the swarm into a side-session.

Issue a single-use focus token for `<repo>` and hand control to a second Codex session. Use when one repo needs sustained one-on-one attention without halting the rest of the swarm.

```bash
momentum swarm focus <swarm-id> <repo> [--session <id>] [--expires-min 60]
```

Behavior:
1. Asserts the caller currently owns `<repo>` (rejected with exit 1 if not).
2. Issues an opaque focus token at `<eco>/swarms/<id>/tokens/<token>.json` (single-use, 1-hour default expiry).
3. Flips `repos[<repo>].owner` to the `_focusing` sentinel — anyone with the token may claim.
4. Writes a `focus-request` signal carrying the token + repo.
5. Audit-logs `focus`.
6. Prints a spawn directive — run a second `codex --cwd <eco>` session in a separate terminal, then inside that session call `momentum swarm join <swarm-id> --token <token>`.

---

### `/swarm join <swarm-id> [--token <token>] [--claim <repo>] [--session <id>]`

> Phase 17.5 / v0.20.2 — register a session with an existing swarm.

Attach the current Codex session to `<swarm-id>` as a co-conductor. Adds the session to `sessions[]` (idempotent — touch on re-join), auto-renews any repos the session already owns, and optionally consumes a transfer token or claims a specific repo.

```bash
momentum swarm join <swarm-id> [--token <token>] [--claim <repo>] [--session <id>]
```

Three shapes:

| Form | Result |
|---|---|
| `join <id>` | Registration only. Adds the session; renews any owned leases. |
| `join <id> --token <token>` | Consumes the token. If `kind=focus`, claims the token's `target_repo` automatically. |
| `join <id> --claim <repo>` | Explicit claim — bound by the same lease rules as `/swarm claim`. |

Exit codes: 0 on success, 1 if the swarm doesn't exist, the token is missing/expired, or the claim is rejected.

---

### `/swarm absorb <target-swarm-id> <source-swarm-id> [--yes] [--session <id>]`

> Phase 17.5 / v0.20.2 — converge two swarms back into one.

Merge `<source-swarm-id>` into `<target-swarm-id>` (the caller's swarm). Use to reunite after a `/swarm focus` split, or to absorb work from a peer swarm that's now done.

```bash
momentum swarm absorb <target-swarm-id> <source-swarm-id> [--yes] [--session <id>]
```

Behavior:
1. Loads both manifests. If either is missing → exit 1.
2. Detects contract conflicts: for every shared `surface` in both swarms' `contracts`, the `owner` must match and the `content_hash` must match. Mismatches abort cleanly — both swarms left untouched.
3. Without `--yes`, prints a dry-run plan. Re-run with `--yes` to proceed.
4. On commit: union of repos (target wins on overlap); waves recomputed; sessions[] union; contracts union; audit[] concat+sort; inbox merge.
5. Archives the source swarm directory to `<eco>/swarms/.absorbed/<source-id>/`.

---

### `/swarm inbox list|write|resolve <swarm-id> …`

Supervisor → conductor questions. Supervisors write inbox items; the conductor resolves them on its turn.

```bash
momentum swarm inbox list <swarm-id>
momentum swarm inbox write <swarm-id> --repo <r> --slug <s> --question "<text>"
momentum swarm inbox resolve <swarm-id> <id> --answer "<text>"
```

---

### `/swarm preview-merge <swarm-id>`

Dry-run `git merge --no-commit --no-ff` for every supervisor branch against `main`. Always aborts; useful before approving a fan-in.

```bash
momentum swarm preview-merge <swarm-id>
```

---

## Tracking contract

- **Auto every time:** `manifest.json` writes via the conductor library; `board.json` regenerated on each write.
- **Auto only when meaningful:** `[SWARM]` entry in each supervisor's repo `history.md` after wave completion; `[NOTE]` in the originating session log on wave transitions.
- **Never:** silent overwrites of supervisor branches. Cancel preserves; resume reconstitutes.

## Errors

- Ecosystem root not found → suggest `--ecosystem <path>` or running from inside an ecosystem.
- Repo arg not a member → list valid members and abort.
- Initiative does not exist → suggest `momentum ecosystem initiative create <slug>` and abort.
- `codex` CLI not on PATH → degrade to dry-run + manual spawn instructions.
- MCP cwd shim not configured → supervisors see the conductor's cwd. See AGENTS.md → `## MCP cwd shim — Codex configuration` for setup.
