"""Governance composed by routing (Phase 30 group 4, D92)."""

from __future__ import annotations

from typing import Any

import pytest

from shadow_hdk.adapters.modes import ModeGovernance, ModeRegistry, Routed, shipped_modes
from shadow_hdk.kernel import EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement, Refuse
from shadow_hdk.testing import GovernancePortContract

pytestmark = pytest.mark.anyio

WRITES = EffectProfile(writes=ScopeSet.of("workspace"), reversible=False)


class Says:
    def __init__(self, judgement: Judgement) -> None:
        self.judgement = judgement
        self.seen: list[Context] = []

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        self.seen.append(context)
        return self.judgement


def _context(component: str | None) -> Context:
    attributes: dict[str, Any] = {"mode": "full"}
    if component is not None:
        attributes["component"] = component
    return Context(run_id="r", step="s", attributes=attributes)


async def test_each_component_is_judged_by_the_port_named_for_it_and_the_rest_by_otherwise() -> (
    None
):
    record = Says(Ask("the constitution asks"))
    machine = Says(Refuse("the machine refuses"))
    rest = Says(Allow())
    routed = Routed({"note_fact": record, "run_shell": machine}, otherwise=rest)
    assert isinstance(await routed.judge(WRITES, _context("note_fact")), Ask)
    assert isinstance(await routed.judge(WRITES, _context("run_shell")), Refuse)
    assert isinstance(await routed.judge(WRITES, _context("turn")), Allow)
    assert isinstance(await routed.judge(WRITES, _context(None)), Allow), "no component: otherwise"
    assert len(record.seen) == 1 and len(machine.seen) == 1 and len(rest.seen) == 2


async def test_the_shipped_modes_serve_as_a_route() -> None:
    machine = ModeGovernance(ModeRegistry(shipped_modes()), default="read-only")
    routed = Routed({"write_file": machine}, otherwise=Says(Allow()))
    judged = await routed.judge(
        WRITES,
        Context(run_id="r", step="s", attributes={"mode": "read-only", "component": "write_file"}),
    )
    assert isinstance(judged, Refuse)


class TestRoutedIsAGovernancePort(GovernancePortContract):
    def port(self) -> Routed:
        return Routed({}, otherwise=ModeGovernance(ModeRegistry(shipped_modes()), default="full"))
