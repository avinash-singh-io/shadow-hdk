"""A model that can start, message and let go of a helper.

Phase 7 built `children.spawn/send/release` on `RunContext` and deliberately stopped there: D3 says
meta-tools belong to the **Pattern**, and a `spawn` a model can call has to say what the child *is*.
That shape is what lands here — a brief, then a wait on the mailbox, which is exactly D16's held
child (a parked run) expressed as a composition.

The three verbs are the pattern's, so an agent that should not be able to start helpers simply is
not offered them, and there is nothing in the runtime that knows the names.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent import (
    MAILBOX,
    RELEASE,
    SEND,
    SPAWN,
    AgentComponent,
    Pattern,
    shipped,
)
from shadow_hdk.adapters.basic import AllowAll, CallableComponents, Mailbox
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

READS = EffectProfile(reads=ScopeSet.of("workspace"))
AGENT = EffectProfile(reads=ScopeSet.of("workspace"), costs=True)

KEEPS = Pattern(
    name="keeps",
    system="You are coordinating, and you may keep a helper between messages.",
    meta_tools=frozenset({SPAWN, SEND, RELEASE, "done"}),
)
HELPER = Pattern(name="helper", system="You do one job and then wait to be asked another.")


def look_up(topic: str) -> str:
    """Look a topic up."""
    return f"what is known about {topic}"


async def drive(
    script: list[ModelResponse], *, with_a_mailbox: bool = True
) -> tuple[list[Event], ScriptedModel]:
    """One run: a coordinating agent, a helper agent it may keep, and a mailbox to park on.

    **One script, in call order.** Both agents share the model port, so the boss and the helper draw
    from the same list in the order they actually ask — a boss turn, then the helper the spawn
    starts, then the boss again. The first version handed the boss and the helper separate lists
    and they interleaved, which is why the order is worth writing down.
    """
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look_up, effects=READS)
    boss = AgentComponent(pattern=KEEPS, effects=AGENT, name="boss", at="2026-01-01T00:00:00+00:00")
    helper = AgentComponent(
        pattern=HELPER, effects=AGENT, name="helper", at="2026-01-01T00:00:00+00:00"
    )
    model = ScriptedModel(script)
    ports = Ports(
        model=model,
        components=(tools, boss, helper, *((Mailbox(),) if with_a_mailbox else ())),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition((Invoke("b1", "boss", (Binding(name="brief", value="get it done"),)),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(60, 3600, 100_000), Floor(0))),
        )
    ]
    return events, model


def _tool_answers(model: ScriptedModel, turn: int) -> list[str]:
    return [m.content for m in model.requests[turn].messages if m.role == "tool"]


async def test_the_mailbox_name_the_verbs_use_is_the_one_the_component_registers() -> None:
    """The agent adapter cannot import `adapters/basic`, so the name is a convention on both sides.
    A convention with nothing pinning it is a rename waiting to break a spawn at runtime."""
    assert MAILBOX == Mailbox.NAME


async def test_a_model_can_start_a_helper_and_is_given_a_handle() -> None:
    events, model = await drive(
        [
            # boss turn 1: delegate
            ModelResponse(
                "delegating",
                (ToolCall("s1", SPAWN, {"agent": "helper", "brief": "find the mass"}),),
            ),
            # the helper the spawn starts
            ModelResponse("on it", (ToolCall("h1", "done", {"summary": "found it"}),)),
            # boss turn 2
            ModelResponse("thanks", (ToolCall("d1", "done", {"summary": "delegated"}),)),
        ]
    )
    answers = _tool_answers(model, 2)
    assert answers, "the spawn was never answered"
    assert "held" in answers[-1].lower(), answers[-1]
    assert [e for e in events if e.kind == "held"], "the parent record does not show a held child"


async def test_a_model_can_message_a_helper_it_kept() -> None:
    """The point of keeping one: the second question does not re-pay the brief."""
    _events, model = await drive(
        [
            ModelResponse(
                "delegating",
                (ToolCall("s1", SPAWN, {"agent": "helper", "brief": "find the mass"}),),
            ),
            ModelResponse("on it", (ToolCall("h1", "done", {"summary": "found it"}),)),
            ModelResponse(
                "asking again",
                (ToolCall("s2", SEND, {"handle": "@1", "message": "and the width?"}),),
            ),
            ModelResponse("thanks", (ToolCall("d1", "done", {"summary": "delegated twice"}),)),
        ]
    )
    answers = _tool_answers(model, 3)
    assert answers, "the send was never answered"
    assert "and the width?" in answers[-1] or "answered" in answers[-1].lower(), answers[-1]


async def test_a_model_can_let_a_helper_go() -> None:
    _events, model = await drive(
        [
            ModelResponse(
                "delegating",
                (ToolCall("s1", SPAWN, {"agent": "helper", "brief": "find the mass"}),),
            ),
            ModelResponse("on it", (ToolCall("h1", "done", {"summary": "found it"}),)),
            ModelResponse("finished with it", (ToolCall("s2", RELEASE, {"handle": "@1"}),)),
            ModelResponse("thanks", (ToolCall("d1", "done", {"summary": "let it go"}),)),
        ]
    )
    answers = _tool_answers(model, 3)
    assert answers and "released" in answers[-1].lower(), answers[-1]
    # And it actually stopped. A verb that only says "released" is a verb that leaks helpers.
    cancelled = [e for e in _events if e.kind == "ended" and e.reason == "cancelled"]
    assert cancelled, "the helper was told it was released and kept running"


async def test_sending_to_a_handle_that_was_never_spawned_is_an_answer_not_a_crash() -> None:
    """The model's mistake is data (D7). It gets told, and keeps its turn."""
    _events, model = await drive(
        [
            ModelResponse(
                "guessing", (ToolCall("s1", SEND, {"handle": "@9", "message": "hello"}),)
            ),
            ModelResponse("fine", (ToolCall("d1", "done", {"summary": "learned"}),)),
        ]
    )
    answers = _tool_answers(model, 1)
    assert answers and "@9" in answers[-1], answers[-1]
    # The *helpful* message, not the generic one. Asserting only that the handle appears cannot
    # tell "there is no helper @9; spawn one first" from "that did not work: KeyError: @9".
    assert "spawn one first" in answers[-1], answers[-1]


def test_the_framework_ships_a_pattern_that_offers_the_verbs() -> None:
    keeps = shipped()["keeps-helpers"]
    assert {SPAWN, SEND, RELEASE} <= keeps.meta_tools


def test_a_pattern_that_does_not_offer_them_cannot_keep_a_helper() -> None:
    """D3, again. An agent that should not start helpers is simply not offered the verbs."""
    from shadow_hdk.adapters.agent import single

    assert not ({SPAWN, SEND, RELEASE} & single.meta_tools)


def _unused(_i: JsonValue) -> None:  # pragma: no cover
    return None


async def test_a_helper_that_cannot_wait_is_reported_as_finished_not_as_held() -> None:
    """A deployment with no mailbox registered.

    The helper does its brief and then cannot park, so it ends. Saying it is *held* would hand the
    model a handle for something that is already gone, and every later `send` would fail for a
    reason that had nothing to do with the send.
    """
    _events, model = await drive(
        [
            ModelResponse(
                "delegating",
                (ToolCall("s1", SPAWN, {"agent": "helper", "brief": "find the mass"}),),
            ),
            ModelResponse("on it", (ToolCall("h1", "done", {"summary": "found it"}),)),
            ModelResponse("oh well", (ToolCall("d1", "done", {"summary": "no helper"}),)),
        ],
        with_a_mailbox=False,
    )
    answers = _tool_answers(model, 2)
    assert answers, "the spawn was never answered"
    assert "finished" in answers[-1].lower(), answers[-1]
    assert "held" not in answers[-1].lower(), answers[-1]
