"""The adapter declares itself; the selection surface never imports it (D39).

`providers` hands back a `ModelPort` from one adapter or an `AgentPort` from another, and a module
that imported the two it chooses between would depend on both — the opposite of the inversion. So an
adapter names itself in its own distribution metadata under `shadow_hdk.transports`, and the
surface looks the name up.

The consequence worth stating: a third party can ship a transport nobody here has heard of, and
nothing in this repository changes.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path

from shadow_hdk.adapters.acp import AcpAgent, open_agent
from shadow_hdk.kernel import AgentPort, Provider, ToolSource
from shadow_hdk.providers.surface import TRANSPORT_GROUP, transports


def test_the_acp_transport_is_declared_in_distribution_metadata() -> None:
    """Metadata rather than an import: this is what rule 5 is enforcing on the other side."""
    declared = {entry.name for entry in entry_points(group=TRANSPORT_GROUP)}

    assert "acp" in declared, f"the ACP adapter declares no transport; found {declared}"


def test_the_surface_finds_it_without_importing_an_adapter() -> None:
    assert "acp" in transports()


async def test_opening_gives_something_that_satisfies_the_agent_port(tmp_path: Path) -> None:
    """The contract, not the class: whatever comes back must be usable as an `AgentPort`."""
    provider = Provider(id="claude-code", kind="agent", bin="claude", transport="acp")

    opened = await open_agent(provider, binary=Path("/bin/echo"), env={}, workspace=tmp_path)

    assert isinstance(opened, AgentPort)


async def test_what_it_opens_carries_the_tools_and_the_workspace(tmp_path: Path) -> None:
    """D42 end to end at the seam: the registry the caller built reaches the child's session."""
    provider = Provider(id="claude-code", kind="agent", bin="claude", transport="acp")
    ours = ToolSource(kind="mcp", address="shadow-hdk-registry --stdio")

    opened = await open_agent(provider, binary=Path("/bin/echo"), env={}, workspace=tmp_path)
    session = await opened.open(tools=(ours,), workspace=str(tmp_path))

    # Narrowed to the concrete adapter on purpose: the claim is about what this transport handed
    # down to the child it is about to start, which the port deliberately does not expose.
    assert isinstance(session, AcpAgent)
    assert session._tools == (ours,)  # noqa: SLF001
    assert session._workspace == tmp_path  # noqa: SLF001
