"""BUG-001: a tool named like a meta-tool is refused, not shadowed.

The agent routes every call whose name is in `BY_NAME` to its meta handler — enabled by the pattern
or not — so a registered tool called `send` was answered by the helper-mailbox verb and never ran,
and nobody was told. A deployment's naming is not the model's to work around, and a silently absent
tool would be the same bug in a new coat: the collision is a configuration error, refused where the
agent builds its tool list, with a reason that names both sides.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shadow_hdk.adapters.agent import Pattern
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Failed,
    Floor,
    Invoke,
    Lease,
    Observed,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

ROLE = "You are working on one task, using the tools you are given."
CALLS: list[str] = []


def send(to: str) -> str:
    """Send a message — named exactly like the agent's own `send` verb."""
    CALLS.append(f"send:{to}")
    return f"sent to {to}"


def propose(kind: str) -> str:
    """Propose something — named like a meta-tool the default pattern does enable."""
    CALLS.append(f"propose:{kind}")
    return "proposed"


def notify(to: str) -> str:
    """Notify someone — no collision."""
    CALLS.append(f"notify:{to}")
    return f"notified {to}"


async def _drive(
    tool: Callable[..., Any] | None, *, call: ToolCall, extra: Any = None
) -> tuple[Any, ScriptedModel]:
    from shadow_hdk.adapters.agent import AgentComponent
    from shadow_hdk.adapters.basic import AllowAll, CallableComponents

    CALLS.clear()
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    if tool is not None:
        tools.add(tool, effects=EffectProfile(reaches=True))
    agent = AgentComponent(
        pattern=Pattern(name="p", system=ROLE),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse("calling", (call,)),
            ModelResponse("finished", (ToolCall("d1", "done", {"summary": "did it"}),)),
        ]
    )
    components = (tools, agent) if extra is None else (tools, extra, agent)
    ports = Ports(
        model=model,
        components=components,
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    composition = Composition(
        (Invoke("a1", agent.registration_id, (Binding(name="brief", value="tell ops"),)),)
    )
    events = [
        e
        async for e in run(
            composition, ports, options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0)))
        )
    ]
    observed = [e.observation for e in events if isinstance(e, Observed) and e.step == "a1"]
    assert len(observed) == 1, observed
    return observed[0], model


async def test_a_tool_named_like_a_meta_tool_is_refused_before_the_model_is_asked() -> None:
    """`send` is not even a verb the default pattern enables; the router shadows it anyway."""
    outcome, model = await _drive(send, call=ToolCall("t1", "send", {"to": "ops"}))
    assert isinstance(outcome, Failed), outcome
    assert "send" in outcome.error and "meta-tool" in outcome.error, outcome.error
    assert CALLS == [], "the shadowed tool ran, or the meta-tool answered in its place"
    assert model.requests == [], "the model was asked to start a turn it could not route"


async def test_a_meta_tool_the_pattern_enabled_collides_too() -> None:
    outcome, _ = await _drive(propose, call=ToolCall("t1", "propose", {"kind": "x"}))
    assert isinstance(outcome, Failed), outcome
    assert "propose" in outcome.error and "meta-tool" in outcome.error, outcome.error
    assert CALLS == []


async def test_the_refusal_names_the_registration_and_the_meta_tool() -> None:
    """An id that differs from the interface name, so both halves of the reason are checkable."""
    from shadow_hdk.kernel import Completed
    from shadow_hdk.runtime.testing import InMemoryComponents, make_registration

    async def _mail(_inputs: Any) -> Completed:
        CALLS.append("ops-mailer")
        return Completed("mailed")

    mailer = make_registration("send", registration_id="ops-mailer")
    outcome, _ = await _drive(
        None, call=ToolCall("t1", "send", {}), extra=InMemoryComponents([(mailer, _mail)])
    )
    assert isinstance(outcome, Failed), outcome
    assert "'ops-mailer'" in outcome.error, outcome.error
    assert "meta-tool 'send'" in outcome.error, outcome.error
    assert CALLS == []


async def test_a_tool_that_does_not_collide_still_runs() -> None:
    outcome, model = await _drive(notify, call=ToolCall("t1", "notify", {"to": "ops"}))
    assert not isinstance(outcome, Failed), outcome
    assert CALLS == ["notify:ops"]
    answer = [m for m in model.requests[1].messages if m.role == "tool"][0].content
    assert "notified ops" in answer
