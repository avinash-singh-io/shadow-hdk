"""Another agent, driven as a governed component."""

from shadow_hdk.adapters.acp.client import REFUSED, BridgeClient, Spend
from shadow_hdk.adapters.acp.kinds import (
    KNOWN_KINDS,
    effects_for,
    opening_a_terminal,
    reading_a_file,
    writing_a_file,
)

__all__ = [
    "KNOWN_KINDS",
    "REFUSED",
    "BridgeClient",
    "Spend",
    "effects_for",
    "opening_a_terminal",
    "reading_a_file",
    "writing_a_file",
]
