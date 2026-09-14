# `shadow_hdk.serve`

The shipped composition, behind the wire. `shadow-hdk serve harness.toml --http` or
`--stdio` puts a `ServeHost` — the local environment with a mode, the shipped skills,
`ask_person`, the mode registry (files and a store), the act rules, the authenticated socket
offer, and whichever provider is signed in here — behind the wire's thread methods, so a host in
any language opens a thread, turns it, answers what it asks, switches modes and reads the store.

`ServeHost(requirements=ExecutionRequirements(...))` sets the process default, and
`thread/start {requirements: ...}` may narrow it per thread. Provider facts and the environment's
proven boundary are selected before the agent opens; a mismatch is typed and complete. Protocol 2
adds `providers/list`, `capabilities/check`, and the accepted `capabilities` on start/resume.

```toml
# harness.toml — what serve needs now; the full facade is Phase 27
[environment]
root = "."
mode = "workspace-write"      # read-only | workspace-write | full
[provider]
want = ""                     # claude-code | codex | opencode | "" for the first ready
idle_seconds = 1800           # a thread's CLI closed after this long idle, reopened at the next turn (D94)
[store]
path = "live.sqlite"          # modes, rules, skills, switches, threads, parked runs — live, no restart
# url = "postgresql://…"      # or Postgres, with the [postgres] extra: the same three, one choice (D79)
[modes]
dir = "modes"                 # reviewer.md, builder.toml …
[registry]
name = "tools"                # what the provider sees its tools named
[tools]
batteries = ["ddgs"]          # seeds the store's `wanted` rows once; the rows rule after (D83)
```

```
uv run shadow-hdk serve harness.toml --http --port 8765
uv run shadow-hdk serve harness.toml --stdio
```
