# `shadow_hdk.adapters.jsonl`

A coding CLI that answers on stdout as newline-delimited JSON — Claude Code, Codex — driven as a
governed agent provider.

One adapter, many CLIs: what differs between them is **names**, and the names live in the provider's
own TOML as a `Dialect`. Adding a CLI that speaks this way costs a file.

A mode's `Behaviour` becomes launch flags through the record's `[[dialect.behaviour_args]]` (D64).
Only `claude-code.toml` maps `system`, `append_system`, `model` and `effort`; `codex.toml` maps
none. A field the record has no flag for is **named, never dropped**: the opened session carries
`unmapped` (computed by `kernel.providers.unmapped_behaviour`), the thread reads it as
`Thread.unmapped_behaviour` at open, at resume and after every `set_mode`, and the wire says it as
`unmapped_behaviour` on `thread/start`, `thread/resume` and `thread/set_mode` — so a host hides the
system-prompt or model control on a provider that cannot honour it instead of showing one that
does nothing.
