"""An id offered by two ports resolves to the first, and the second is reported (BUG-037).

The registry is the one funnel (D27): every port's catalogue lands in one map keyed by id. That map
took the **last** writer — so a battery wanted after another that named the same tool, or an MCP
server connected mid-session that happened to call something `read_file`, replaced what was there
without a word. Found by the batteries test the day `ddgs` became installable in the dev venv
(D78: one distribution, `--all-extras`): two batteries offered `web_search`, the second answered
with the wrong shape, and nothing said why.

The rule: the first port to offer an id keeps it — a registration the run started with cannot be
taken over by a later port, which is the safer direction for a live registry — and the hidden one
is named in `shadowed`, beside `unreachable` and `refused` (TD-006's shape: tolerated, and seen).
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel, make_registration


class Port:
    """A component port that answers with its own name, so the test can tell which one ran."""

    def __init__(self, name: str, *registrations: Registration) -> None:
        self.name = name
        self._registrations = list(registrations)

    async def registrations(self) -> Sequence[Registration]:
        return self._registrations

    async def invoke(self, _r: RegistrationId, _i: JsonValue) -> Observation:
        return Completed({"answered_by": self.name})


SEARCH = make_registration("web_search")
LOOK = make_registration("look")


async def test_the_first_port_to_offer_an_id_keeps_it() -> None:
    registry = Registry([Port("reference", SEARCH), Port("ddgs", SEARCH, LOOK)])
    await registry.refresh()

    port, registration = registry.resolve("web_search")
    assert isinstance(port, Port) and port.name == "reference"
    assert {r.id for r in registry.all()} == {"web_search", "look"}


async def test_the_hidden_offer_is_reported_by_id_and_by_both_ports() -> None:
    registry = Registry([Port("reference", SEARCH), Port("ddgs", SEARCH)])
    await registry.refresh()

    assert len(registry.shadowed) == 1
    report = registry.shadowed[0]
    assert "web_search" in report and "Port" in report, report


async def test_nothing_is_reported_when_every_id_is_offered_once() -> None:
    registry = Registry([Port("reference", SEARCH), Port("other", LOOK)])
    await registry.refresh()

    assert registry.shadowed == []


async def test_a_refresh_forgets_a_shadow_that_went_away() -> None:
    """Live (`09` §4): the report is of the last refresh, not an accumulation."""
    second = Port("ddgs", SEARCH)
    registry = Registry([Port("reference", SEARCH), second])
    await registry.refresh()
    assert registry.shadowed
    second._registrations.clear()
    await registry.refresh()

    assert registry.shadowed == []


async def test_a_component_can_see_what_is_shadowed_from_inside_a_run() -> None:
    """The same door `unreachable` has (TD-006): a host or a component reads it off the context."""
    seen: list[tuple[str, ...]] = []

    class Noting(Port):
        async def invoke(self, _r: RegistrationId, _i: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            seen.append(context.shadowed)
            return Completed("ok")

    ports = Ports(
        model=ScriptedModel(),
        components=(Noting("first", LOOK), Port("second", LOOK)),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _event in run(
        Composition((Invoke("s1", "look"),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(3, 60, 1_000), Floor(0))),
    ):
        pass

    assert seen and seen[0] and "look" in seen[0][0]
