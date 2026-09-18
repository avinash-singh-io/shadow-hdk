# `shadow_hdk.providers`

Which model or agent this machine can reach, and whether it is ready to be used.

Two seams (D39): an **inference** provider you hold a key for, and an **agent** provider you already
have a subscription to. This package finds them, asks them about themselves, and hands back the
right port — and it imports no adapter to do it.

It never reads a credential and it never installs anything (D41).

Every `Provider` also carries `ProviderCapabilities`: tool path, session continuity,
interruptibility, streaming, reasoning, token usage and cost usage, with evidence per axis. Missing
fields default to `unknown`; discovery keeps the record on `Available`. The shipped records are
measured or derived facts, not normalization: Claude Code has a controlled path, Codex is
uncontrolled because configured MCP servers cannot be excluded, and OpenCode currently exposes a
process session with final-only output through this adapter. A host compares these facts with
`ProviderRequirements` before opening the agent.

Which of a mode's behaviour fields a provider can take is also a fact of its record:
`kernel.providers.unmapped_behaviour(provider, behaviour)` names the fields the record has no flag
for. Every opener reports them on the session it hands back, and the thread and the wire carry them
(`Thread.unmapped_behaviour`, `unmapped_behaviour` on the thread results) rather than losing them.
