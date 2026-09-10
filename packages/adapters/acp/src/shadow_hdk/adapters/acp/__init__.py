"""Another agent, driven as a governed component."""

from shadow_hdk.adapters.acp.agent import AcpAgent
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
    "AcpAgent",
    "BridgeClient",
    "Spend",
    "effects_for",
    "opening_a_terminal",
    "reading_a_file",
    "writing_a_file",
]
