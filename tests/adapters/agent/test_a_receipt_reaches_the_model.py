"""An act's receipt reaches the model, not only the record (R9: *every effect attributed*).

`_readable` rendered every non-`Completed` observation as `kind: reason`, and an `Acted` has no
reason — so the model was told `acted: ` and nothing else. It could not cite the foreign id, could
not tell *accepted* from *rejected by the world*, and would have re-sent. The receipt's audit half
(`grounds`) is deliberately **not** shown: it is the run's own lease and argv, for an auditor.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent import Pattern
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Acted
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

ROLE = "You are working on one task, using the tools you are given."


def notify(to: str) -> Acted:
    """Send a message."""
    return Acted(
        foreign_id="msg-77",
        idempotency_key="r/s1",
        exit="accepted",
        grounds={"lease": {"max_wall_seconds": 599}, "argv": {"to": to}},
    )


async def _drive_an_act() -> ScriptedModel:
    from shadow_hdk.adapters.agent import AgentComponent
    from shadow_hdk.adapters.basic import AllowAll, CallableComponents
    from shadow_hdk.kernel import Binding, Ceiling, Composition, Floor, Invoke, Lease
    from shadow_hdk.runtime import RunOptions, run

    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(notify, effects=EffectProfile(reaches=True, reversible=False))
    agent = AgentComponent(
        pattern=Pattern(name="p", system=ROLE),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse("notifying", (ToolCall("t1", "notify", {"to": "ops"}),)),
            ModelResponse("sent", (ToolCall("d1", "done", {"summary": "sent it"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    composition = Composition(
        (Invoke("a1", agent.registration_id, (Binding(name="brief", value="tell ops"),)),)
    )
    async for _ in run(
        composition, ports, options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0)))
    ):
        pass
    return model


async def test_the_model_is_told_the_receipt() -> None:
    model = await _drive_an_act()
    answer = [m for m in model.requests[1].messages if m.role == "tool"][0].content
    assert "acted" in answer, answer
    assert "msg-77" in answer, answer
    assert "accepted" in answer, answer
    assert "r/s1" in answer, answer


async def test_the_model_is_not_shown_the_grounds() -> None:
    """The audit half stays in the record. The receipt, not the lease it ran under."""
    model = await _drive_an_act()
    answer = [m for m in model.requests[1].messages if m.role == "tool"][0].content
    assert "599" not in answer and "grounds" not in answer, answer
