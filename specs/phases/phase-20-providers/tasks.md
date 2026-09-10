---
type: Tasks
phase: 20
---

# Tasks — Phase 20, Providers

Rule 13 throughout: every claim is a test that failed first, for the stated reason, and every
assertion is mutation-checked.

## Group 1 — the abstraction (kernel; contract 0.14.0)

- [x] `AgentPort` and `AgentSession` protocols in the kernel — open, turn, stream, close
- [x] D14's refuse-not-crash default on the port's later method
- [x] `Provider` — the frozen record: identity, binary and fallbacks, version probe, auth probe and
      its patterns, environment to set / strip / backfill, transport, tool injection
- [x] `ProviderStatus` — `ready · absent · not-signed-in · too-old · unknown`
- [x] contracts round-trip through JSON, like every other kernel type (D19)
- [x] eighteen distributions to 0.14.0, the pins with them, a *Pins* row on the board (D9)

## Group 2 — discovery (`packages/providers`)

- [x] the search path is `PATH` plus the user toolchain directories
- [x] resolution yields **every** candidate in order, not the winner
- [x] a candidate that cannot be spawned is abandoned for the next one
- [x] the spawn path carries the same directories resolution searched
- [x] a launcher that never reached its program is told apart from a program that ran and failed
- [x] the version probe, and `too-old` against a declared floor
- [x] the auth probe: asked, never read; patterns from the record; unmatched is `unknown`
- [x] **no credential is opened, stored, forwarded or logged** — asserted, not assumed
- [x] an absent provider reports the command that would fix it, and installs nothing
- [x] the environment rules applied from the record (set / strip / backfill)
- [x] the TOML library loader, with a malformed file refused at load naming file and field
- [x] the entry-point selection surface, and the direct-registration escape hatch
- [x] **invariant: `providers` imports no adapter** — rule 5, with its synthetic breaking case

## Group 3 — the socket (`adapters/acp`, runtime leash)

- [x] `session/new` carries the run's registry as an MCP server
- [x] the provider's native tools are refused, so ours are the only ones it has
- [x] `create_terminal` granted and backed by the runtime's leash — output cap, timeout, kill
- [x] the terminal's follow-ups (`output`, `wait`, `kill`, `release`) against a real process
- [x] a tool call from the child lands on the parent's record as `Invoke` with a child run id
- [x] a refusal reaches the child in its own vocabulary and the turn still ends cleanly
- [x] the lease bounds a child that will not stop
- [x] **the socket has no hole**: a child cannot cause an effect that is not on the record

## Group 4 — the library, as data

- [x] `claude-code.toml`, every quirk carrying the measurement that found it
- [x] `CLAUDECODE` in its strip list — measured 2026-09-11: Claude Code refuses to launch inside
      another Claude Code session, and the message says which variable to clear
- [x] `opencode.toml` — the proof that the second provider costs a file, not a phase.
      **opencode, not codex**: it was already installed here and speaks ACP natively, so the
      claim could be *measured* rather than written from documentation
- [x] a shipped-library test: every TOML in the library parses into a valid record

## Group 5 — proof

- [x] end to end against a real CLI and a real subscription, marked `live`, deselected by default
- [x] it **skips** rather than fails where the CLI is absent or not signed in
- [x] what it measured is written into `history.md`

## Closing

- [x] decisions D39–D43 recorded, `specs/decisions/index.md` regenerated
- [x] `specs/architecture/` reconciled: the port table, the file structure, the adapter list
- [x] README's port table grows the seventh row
- [x] status, roadmap, changelog
