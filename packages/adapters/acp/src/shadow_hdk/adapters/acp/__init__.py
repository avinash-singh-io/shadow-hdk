"""Another agent, driven as a governed component."""

from shadow_hdk.adapters.acp.agent import AcpAgent, mcp_servers_from
from shadow_hdk.adapters.acp.client import REFUSED, BridgeClient, Spend
from shadow_hdk.adapters.acp.kinds import (
    KNOWN_KINDS,
    effects_for,
    opening_a_terminal,
    reading_a_file,
    writing_a_file,
)
from shadow_hdk.adapters.acp.transport import AcpProvider, open_agent

__all__ = [
    "AcpProvider",
    "open_agent",
    "mcp_servers_from",
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
