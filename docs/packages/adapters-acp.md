# `shadow_hdk.adapters.acp`

Another agent, driven as a **component**. Codex, Claude Code, or anything speaking Zed's Agent
Client Protocol becomes a `ComponentPort`: the agent composes it into a step, governance judges it,
its lease is carved from the parent's, and everything it does comes back as observations.

**The bridge is a governance surface with fourteen doors, not a wrapper around `prompt`.** A child
asking to `write_text_file` or `create_terminal` is asking to do something our effect vocabulary
already has words for, so each request is turned into an `EffectProfile` and judged.
