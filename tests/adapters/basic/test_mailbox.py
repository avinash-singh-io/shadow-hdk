"""A child held on the shipped mailbox, with nothing doubled.

`tests/runtime/test_children.py` proves spawn, send and release against a test component that
answers `Pending`. This proves the same thing against the component a host would actually use, so
the convention a held child parks on is the one in the package rather than one invented per test.
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll, CallableComponents, Mailbox
from shadow_hdk.kernel import (
    Await,
    Binding,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Held,
    Invoke,
    Lease,
    Observation,
    Observed,
    ScopeSet,
)
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from shadow_hdk.testing.contracts import ComponentPortContract

AnyCallable = Callable[..., object]
WORKSPACE = ScopeSet.of("workspace")


def look_up(topic: str) -> str:
    """Look a topic up."""
    return f"what is known about {topic}"


CHILD = Composition(
    (
        Invoke("brief", "look_up", inputs=(Binding(name="topic", value="lathes"),)),
        Await("inbox", Mailbox.NAME),
    )
)


def _ports(parent: AnyCallable) -> Ports:
    components = CallableComponents()
    components.add(look_up, effects=EffectProfile(reads=WORKSPACE))
    components.add(
        parent, effects=EffectProfile(), name="hold_a_helper", labels=frozenset({"agent"})
    )
    return Ports(
        model=ScriptedModel(),
        components=(components, Mailbox()),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_a_child_is_held_on_the_shipped_mailbox_and_answers_when_sent_to() -> None:
    seen: list[list[Event]] = []

    async def hold_a_helper() -> Observation:
        """Spawn a helper, keep it, and send it something."""
        context = current_run()
        assert context is not None
        handle, first = await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        seen.append(first)
        assert handle in context.children.held, "the child did not park on the mailbox"
        seen.append(await context.children.send(handle, {"say": "what did you find?"}))
        return Completed("held and messaged")

    events = [
        e
        async for e in run(
            Composition((Invoke("p1", "hold_a_helper"),)),
            _ports(hold_a_helper),
            options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
        )
    ]
    assert len(seen) == 2, "the parent step did not get as far as sending"
    spawned, answered = seen

    # It did its brief, then waited — and waiting was recorded as waiting, not as an ending.
    brief = [e for e in spawned if isinstance(e, Observed) and e.step == "brief"]
    assert brief[-1].observation == Completed("what is known about lathes")
    assert not [e for e in spawned if isinstance(e, Ended)], "a held child has not ended"

    held = [e for e in events if isinstance(e, Held)]
    assert len(held) == 1, "the parent's record does not say a child is being held"

    # Woken where it slept: the brief is not read a second time.
    assert "brief" not in [e.step for e in answered if e.kind == "invoked"]
    inbox = [e for e in answered if isinstance(e, Observed) and e.step == "inbox"]
    assert inbox[-1].observation == Completed({"say": "what did you find?"})
    assert [e for e in answered if isinstance(e, Ended)][-1].reason == "completed"


async def test_the_mailbox_refuses_a_name_that_is_not_its_own() -> None:
    """A port asked for something it does not have says so, rather than waiting forever."""
    observation = await Mailbox().invoke("not_the_mailbox", {})
    assert observation.kind == "failed"


def _unused(_inputs: JsonValue) -> None:  # pragma: no cover — keeps the import honest
    return None


async def test_a_mode_that_allows_nothing_still_lets_a_child_wait() -> None:
    """Why the empty profile is load-bearing rather than tidy.

    Waiting reads nothing, writes nothing and reaches nowhere, so it survives the narrowest mode
    there is. If the mailbox claimed an effect it does not have, a child narrowed to do no work
    could not even be *held* — the one thing it was narrowed in order to do safely.
    """
    from shadow_hdk.adapters.modes import Mode, ModeGovernance

    nothing = Mode("nothing", EffectProfile())
    ports = Ports(
        model=ScriptedModel(),
        components=(Mailbox(),),
        governance=ModeGovernance({nothing.name: nothing}, default=nothing.name),
        sink=ListSink(),
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition((Await("inbox", Mailbox.NAME),)),
            ports,
            options=RunOptions(
                lease=Lease(Ceiling(10, 600, 1000), Floor(0)),
                run_id="narrow",
                checkpointer=InMemorySaver(),
            ),
        )
    ]
    assert not [e for e in events if isinstance(e, Ended)], "the narrowed child could not wait"
    waiting = [e for e in events if isinstance(e, Observed) and e.step == "inbox"]
    assert waiting[-1].observation.kind == "pending", (
        "waiting was refused by a mode allowing nothing"
    )


class TestMailboxIsAComponentPort(ComponentPortContract):
    """The component a held child parks on (D16), held to the shared shape like any other.

    Its effect profile is empty and a test already proves that load-bearing — a child can be held
    under a mode that allows nothing at all. The contract asks the other four questions.
    """

    def port(self) -> ComponentPort:
        return Mailbox()

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        return "mailbox", {}
