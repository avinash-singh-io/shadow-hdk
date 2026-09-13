"""The contracts ship (Phase 30 group 3, D91).

A product implementing a port proves it with the very suites the kit's adapters pass — imported
from the wheel, not copied from our tests. A scripted provider ships beside them, so a product's
tests of its governance, its verbs and its record spend nothing. And the runtime asks its
questions through a kernel port, `Questions`, which the host's `Approvals` implements and a
product's own may — without inheriting ours.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    EffectProfile,
    Floor,
    Lease,
    Questions,
    Request,
    ScopeSet,
)
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    QuestionsContract,
    ScriptedAgent,
    make_registration,
)

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))


def test_the_suites_are_importable_from_the_wheel() -> None:
    import shadow_hdk.testing.contracts as shipped

    assert {"StoreContract", "ThreadStoreContract", "QuestionsContract"} <= set(shipped.__all__)
    assert "tests" not in Path(shipped.__file__).parts, "in the wheel, not in our tests"
    assert Path(shipped.__file__).parent.name == "testing"


# ---------------------------------------------------------------- the Questions port


class Decides:
    """A product's own way of asking — no handle of ours inherited. It answers the moment it is
    asked, from a table, and remembers what it was asked."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.asked: list[Request] = []

    async def ask(self, request: Request) -> Any:
        self.asked.append(request)
        return self.answers.get(request.component or "", {"kind": "deny", "reason": "no"})


class AsksAboutWrites:
    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.attributes.get("component") == "write_file":
            return Ask("may it write?")
        return Allow()


async def test_the_hosts_handle_is_a_questions_port_and_so_is_a_products_own() -> None:
    assert isinstance(Approvals(), Questions)
    assert isinstance(Decides({}), Questions)


async def test_a_products_own_questions_port_answers_a_run(tmp_path: Path) -> None:
    wrote: list[Any] = []

    async def write(inputs: Any) -> Any:
        wrote.append(inputs)
        return Completed({"wrote": True})

    decides = Decides({"write_file": {"kind": "approve"}})
    agent = ScriptedAgent([([("write_file", {"path": "a.txt"})], "wrote")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([(WRITE, write)]),),
            governance=AsksAboutWrites(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        approvals=decides,
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("write")]
        assert wrote == [{"path": "a.txt"}]
        (asked,) = decides.asked
        assert asked.component == "write_file" and asked.inputs == {"path": "a.txt"}
        assert thread.record.turns[-1].outcome == "completed"
    finally:
        await thread.close()


class TestApprovalsHoldsTheQuestionsContract(QuestionsContract):
    def questions(self) -> Approvals:
        return Approvals()

    async def answer(self, questions: Approvals, request: Request, answer: Any) -> None:
        for _ in range(100):
            if any(p.handle == request.handle for p in questions.pending()):
                break
            await asyncio.sleep(0)
        assert questions.answer(request.handle, answer)


# ---------------------------------------------------------------- the scripted provider


async def test_the_scripted_agent_keeps_what_it_was_told_and_what_it_heard(tmp_path: Path) -> None:
    agent = ScriptedAgent([([("write_file", {"path": "a.txt"})], "one"), ([], "two")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([(WRITE, lambda _i: _ok())]),),
            governance=AsksAboutWrites(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("first")]
        assert agent.prompts == ["first"]
        (heard,) = agent.answers
        assert heard.kind == "refused", "nobody to ask: refused, and the agent heard it"
        [e async for e in thread.turn("second")]
        assert agent.prompts == ["first", "second"] and agent.opened == 1
    finally:
        await thread.close()
    assert agent.closed == 1


async def _ok() -> Any:
    return Completed({"wrote": True})
