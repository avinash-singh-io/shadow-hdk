"""A thread can say what its agent is offered *now* — every registration its ports carry, with
the judgement the current mode would give it — so a host shows the tool registry the way it shows
the mode: as the harness's data, not a guess (Phase 28 group 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Ceiling, EffectProfile, Floor, Lease, ScopeSet
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement, Refuse
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from tests.wire.test_a_thread_crosses_the_wire import ScriptedAgent, look

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))
TOUCH = make_registration(
    "touch", effects=EffectProfile(reads=ScopeSet.of("workspace"), writes=ScopeSet.of("workspace"))
)


class ByMode:
    """A policy in two modes: `looking` refuses writes; `working` asks before them."""

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        if effects.writes.names or effects.writes.everything:
            if context.attributes.get("mode") == "looking":
                return Refuse("looking only")
            return Ask("may it write?")
        return Allow()


async def _thread(tmp_path: Path, mode: str) -> Thread:
    ports = Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look), (TOUCH, look)]),),
        governance=ByMode(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    return await Thread.open(
        agent=cast(Any, ScriptedAgent()),
        ports=ports,
        store=InMemoryThreads(),
        root=str(tmp_path),
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        mode=mode,
        provider="scripted",
    )


async def test_the_offer_is_every_registration_with_its_judgement(tmp_path: Path) -> None:
    thread = await _thread(tmp_path, "working")
    try:
        offered = await thread.tools()
    finally:
        await thread.close()
    by_name = {o.registration.id: o for o in offered}
    assert set(by_name) >= {"look", "touch"}
    assert by_name["look"].judgement == "allow"
    assert by_name["touch"].judgement == "ask"
    assert by_name["touch"].registration.component.effects.writes == ScopeSet.of("workspace")
    assert by_name["look"].source == "InMemoryComponents", "which port carried it"


async def test_the_offer_follows_the_mode(tmp_path: Path) -> None:
    thread = await _thread(tmp_path, "looking")
    try:
        before = {o.registration.id: o.judgement for o in await thread.tools()}
        await thread.set_mode("working")
        after = {o.registration.id: o.judgement for o in await thread.tools()}
    finally:
        await thread.close()
    assert before["touch"] == "refuse" and after["touch"] == "ask"
    assert before["look"] == after["look"] == "allow"
