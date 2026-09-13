# `shadow_hdk.adapters.jsonl`

A coding CLI that answers on stdout as newline-delimited JSON — Claude Code, Codex — driven as a
governed agent provider.

One adapter, many CLIs: what differs between them is **names**, and the names live in the provider's
own TOML as a `Dialect`. Adding a CLI that speaks this way costs a file.
