"""What a child agent is asking for, in our own vocabulary.

ACP labels a tool call with a `ToolCallKind`. That is **half a profile** — the same half MCP's
annotations gave us in Phase 1 — and the other half belongs to the deployment: whether this machine
contains anything, and whether the network is open.

The rule for everything else is the one that lets the registry stay open: **an effect nobody
vouched for is assumed to be the worst one.** `other`, an absent kind, and a kind invented after
this was written all come out `ASSUME_WORST`, which is blunt and safe, and which a mode can still
allow deliberately.
"""

from __future__ import annotations

from shadow_hdk.kernel.effects import ASSUME_WORST, NOTHING, EffectProfile, ScopeSet

WORKSPACE = ScopeSet.of("workspace")

READS = EffectProfile(reads=WORKSPACE)
EDITS = EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=True)
DESTROYS = EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=False)
FETCHES = EffectProfile(reads=WORKSPACE, reaches=True, costs=True)

KNOWN_KINDS = frozenset({"read", "search", "think", "edit", "move", "delete", "execute", "fetch"})
"""The kinds this bridge maps. `other` and `switch_mode` are deliberately absent — see below."""


def effects_for(kind: str | None, *, contained: bool, network: bool = False) -> EffectProfile:
    """Turn ACP's label into the six fields, hardening what it does not say.

    `contained` and `network` are the **deployment's** answers, not the child's, and `execute`
    follows Phase 3's rule exactly: an uncontained host cannot promise a run will not reach the
    network, so it does not claim to.

    `switch_mode` is not mapped on purpose. A child changing its *own* mode is a thing whose effect
    we cannot read off a label — it could be harmless or it could be the child talking itself out of
    a restriction — so it takes the worst case until somebody has a reason to say otherwise.
    """
    match kind:
        case "read" | "search":
            return READS
        case "think":
            return NOTHING
        case "edit" | "move":
            return EDITS
        case "delete":
            return DESTROYS
        case "fetch":
            return FETCHES
        case "execute":
            return EffectProfile(
                reads=WORKSPACE,
                writes=WORKSPACE,
                reaches=network or not contained,
                reversible=False,
                contained=contained,
                costs=False,
            )
    return ASSUME_WORST


def writing_a_file() -> EffectProfile:
    """`write_text_file` — a child changing a file it can name."""
    return EDITS


def reading_a_file() -> EffectProfile:
    """`read_text_file`."""
    return READS


def opening_a_terminal(*, contained: bool, network: bool = False) -> EffectProfile:
    """`create_terminal` — the same thing as `execute`, asked for a different way."""
    return effects_for("execute", contained=contained, network=network)


__all__ = [
    "KNOWN_KINDS",
    "effects_for",
    "opening_a_terminal",
    "reading_a_file",
    "writing_a_file",
]
