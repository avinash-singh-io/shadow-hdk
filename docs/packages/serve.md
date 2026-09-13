# `shadow_hdk.serve`

The shipped composition, behind the wire. `shadow-hdk serve harness.toml --http` or
`--stdio` puts a `ServeHost` — the local environment with a mode, the shipped skills,
`ask_person`, the mode registry (files and a store), the act rules, the authenticated socket
offer, and whichever provider is signed in here — behind the wire's thread methods, so a host in
any language opens a thread, turns it, answers what it asks, switches modes and reads the store.

```toml
# harness.toml — what serve needs now; the full facade is Phase 27
[environment]
root = "."
mode = "workspace-write"      # read-only | workspace-write | full
[provider]
want = ""                     # claude-code | codex | opencode | "" for the first ready
[store]
path = "live.sqlite"          # modes, rules, skills, switches — live, no restart
[modes]
dir = "modes"                 # reviewer.md, builder.toml …
[registry]
name = "tools"                # what the provider sees its tools named
```

```
uv run shadow-hdk serve harness.toml --http --port 8765
uv run shadow-hdk serve harness.toml --stdio
```
