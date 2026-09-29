---
type: Ad-hoc Record
---
# BUG-226 · BUG-227 · BUG-228 — the relay reaches the child; a parked call is told as a fact

> **Type**: quick-task
> **Created**: 2026-09-30
> **Branch**: fix/BUG-226-228-the-relay-reaches-the-child
> **Backlog**: BUG-226, BUG-227, BUG-228
> **Status**: at the gate

Three defects from lane P's walk of the **installed** Intent Studio 0.6.10 (bundling 0.34.1) on
macOS, plus one found in the kit while proving the first. Two of them have the same outcome — a
governed CLI with no tools at all — for two different reasons, and both were invisible to a
developer tree by construction: one needs a path with a space in it, the other needs a transport
nothing in the suite launched for real.

The two questions lane P asked alongside them (the shape of a key-backed model's parked turn, and a
resident CLI's lifetime) are answered in
[`docs/for-a-product.md`](/docs/for-a-product.md) and in the handoff back to lane P; the first is
now also pinned by a test, because an answer nobody can run is an opinion.

## Current Behavior

- `adapters/jsonl/transport.py::mcp_config_for` did `command, *arguments = source.address.split()`.
  In an application bundle the relay is at `/Applications/Intent Studio.app/…/shadow-hdk-registry`,
  so the CLI was launched with the command `/Applications/Intent`; Claude Code answered
  `Connection failed (ENOENT): posix_spawn 'stdio'`. `mcp_overrides_for` (Codex's `-c`) builds on
  the same function, and `adapters/acp/agent.py` did its own `shlex.split`. A governed CLI runs with
  its built-ins off (`--tools ""`, BUG-031), so the turn had **no tools at all**.
- `adapters/acp/agent.py::mcp_servers_from` built its MCP entry with `env=[]`. The registry's port
  and token are minted per thread and live **only** on the `ToolSource`, so the relay OpenCode
  launched had nothing to relay to.
- `runtime/offer.py::PARKED_REASON` ended *"Say what you proposed and why, then stop."* — an
  imperative, in the second person, delivered as a tool result; and
  `adapters/agent/model.py` used that same agent-facing sentence as the **turn's** text, so a host
  showing the turn showed it to the person.

## Expected Behavior

- **An address is a command, never a command line.** Nothing splits `ToolSource.address` on any
  transport; a path with a space is a path. The relay is resolved beside the running interpreter
  before `PATH`, because a console script is installed next to the interpreter of the environment it
  was installed into, while `PATH` answers for whatever environment the host process was started
  with — which inside a packaged application is a different one.
- The ACP entry carries the source's env, so the relay finds the registry.
- A parked call is reported as a fact about the call: it names the call, says it is waiting and has
  not run, and addresses nobody. A parked turn describes itself separately, and
  `Turn.stop_reason == "parked"` is the signal a host keys on to speak in its own words.

## Unchanged Behavior

No contract change, so no *Pins* row (D9): `ToolSource` is the same three fields, every port and
every wire method is unchanged, protocol 3 unchanged, and the six environment operations are
untouched. `relay_source` still falls back to `PATH` and then to the bare name. A source of a kind
nothing serves is still refused by name; an `mcp-http` source still becomes an HTTP server; a second
source is still named apart. The park mechanism itself is unchanged — only the words it carries.

A caller who put arguments **inside** `address` would previously have had them split out; nothing in
the tree did, and the one test that spelled an address that way was testing something else. The
vector shape is filed as ENH-040 rather than smuggled into a patch.

## Verification Evidence

Captured 2026-09-30 on the hotfix branch at the 0.34.2 bump (macOS 27.0, arm64; Python 3.14 and
3.12).

```
== uv run ruff check                       All checks passed!
== uv run ruff format --check              531 files already formatted
== uv run mypy                             Success: no issues found in 475 source files
== uv run pytest (3.14, non-live)
1871 passed, 20 skipped, 13 deselected, 85 warnings in 190.90s (0:03:10)
== pytest 3.12 (--all-extras)
1871 passed, 20 skipped, 13 deselected, 85 warnings in 171.92s (0:02:51)
```

RED before the fix, each for its stated reason
(`tests/adapters/test_the_relay_reaches_the_child.py`,
`tests/runtime/test_a_parked_call_is_told_as_a_fact.py`):

```
7 failed, 4 passed   — the JSON config, the launch argv, the Codex overrides and the ACP entry
                       each named "/Applications/Intent"; the ACP entry's env was []; the relay
                       was found on PATH, not beside the interpreter; a second source's
                       "/tmp/other relay" came back as "/tmp/other"
3 failed, 1 passed   — the note addressed the agent ("you", "your"), gave an order
                       ("Say what you proposed", "then stop"), and said neither "waiting" nor
                       "kept ... has not run"
```

The four passes in the first run are the guards that had to stay green: an unfindable relay still
named rather than empty, the `PATH` fallback, a refused unknown kind, an `mcp-http` source.

`tests/runtime/test_a_key_backed_models_park_settles_after_a_restart.py` is new and green; it is
the evidence behind the answer to lane P's question 3, and it was written because the existing
proof of a surviving park used a resident CLI double, which is the case that was not in doubt.

CI cannot run (GitHub billing, see `specs/status.md`); the gate above ran locally.
