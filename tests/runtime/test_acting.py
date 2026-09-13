"""Every effect is attributed, and the authority for it is checked at the moment of the act (R9).

The vision's phrase is *authority checked at the moment of the act and every effect attributed*.
The runtime's half of that is here: what a driver reads when it is about to act, what it leaves
behind when it has, and a key that tells a retry from a second act. The driver in this file is
test-local — a fake world it appends to — because the policy for real ones waits on ADR-1.

The claim *at the moment of the act* is a claim about time, so it is tested by moving the clock
between the step's admission and the act.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import (
    Acted,
    Await,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    Pending,
    Refused,
)
from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.runtime import Ports, RunOptions, current_run, resume, run
from shadow_hdk.runtime.acting import exhausted, grounds
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel, make_registration

SEND = make_registration("send", effects=EffectProfile(reaches=True, reversible=False))
CEILING = Ceiling(max_steps=10, max_wall_seconds=600, max_cost_cents=100)


class World:
    """What the act touches. A driver that refuses must leave it exactly as it was."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, JsonValue]] = []


class Driver:
    """A driver that reads the lease at the moment of the act, not at planning.

    `delay` is how long the driver takes *before* acting — connecting, queueing — and it is what
    lets a test move the clock between the step's admission and the act itself.
    """

    def __init__(self, world: World, clock: FixedClock, *, delay: float = 0) -> None:
        self.world, self.clock, self.delay = world, clock, delay
        self.seen_steps: list[str | None] = []
        self.keys_outside: list[str] = []

    async def registrations(self) -> Sequence[Registration]:
        context = current_run()
        self.seen_steps.append(context.step if context is not None else "<no run>")
        if context is not None:
            try:
                context.idempotency_key()
                self.keys_outside.append("named an act that does not exist")
            except RuntimeError as refused:
                self.keys_outside.append(type(refused).__name__)
        return [SEND]

    async def invoke(self, _r: RegistrationId, inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        self.seen_steps.append(context.step)
        self.clock.advance(self.delay)
        if why := exhausted(context.remaining()):
            return Refused(why)
        key = context.idempotency_key()
        self.world.sent.append((key, inputs))
        return Acted(
            foreign_id=f"msg-{len(self.world.sent)}",
            idempotency_key=key,
            exit="accepted",
            grounds=grounds(context, argv=inputs),
        )


def _ports(driver: Driver, clock: FixedClock) -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(driver,),
        governance=AllowAll(),
        sink=ListSink(),
        clock=clock,
    )


async def _run(
    composition: Composition, driver: Driver, clock: FixedClock, **options: object
) -> list[Event]:
    return [
        e
        async for e in run(
            composition,
            _ports(driver, clock),
            options=RunOptions(lease=Lease(CEILING, Floor(0)), **options),  # type: ignore[arg-type]
        )
    ]


def _acts(events: list[Event]) -> list[Acted]:
    return [
        e.observation
        for e in events
        if isinstance(e, Observed) and isinstance(e.observation, Acted)
    ]


ONE = Composition((Invoke("s1", SEND.id, ()),))


# ---------------------------------------------------------------- the receipt


async def test_an_act_leaves_a_receipt_on_the_stream() -> None:
    world, clock = World(), FixedClock()
    events = await _run(ONE, Driver(world, clock), clock)
    receipts = _acts(events)
    assert len(receipts) == 1 and world.sent, "the act was not performed, or not recorded"
    (receipt,) = receipts
    assert receipt.foreign_id == "msg-1"
    assert receipt.idempotency_key == world.sent[0][0]
    assert receipt.exit == "accepted"
    assert isinstance(receipt.grounds, dict) and receipt.grounds["step"] == "s1"


async def test_the_grounds_say_what_it_was_performed_under() -> None:
    """Not *what happened* only: *on whose authority, at that moment* — the run, the step, the lease
    left, the argv, the time."""
    world, clock = World(), FixedClock()
    events = await _run(ONE, Driver(world, clock), clock, run_id="r-9")
    (receipt,) = _acts(events)
    assert isinstance(receipt.grounds, dict)
    assert receipt.grounds["run"] == "r-9"
    assert receipt.grounds["at"] == clock.now()
    assert receipt.grounds["argv"] == {}
    assert receipt.grounds["warrant"] is None, "no warrant was carried, and none is invented"
    lease = receipt.grounds["lease"]
    assert isinstance(lease, dict)
    assert lease["max_steps"] == 9, "one step was charged before the act"
    assert lease["max_wall_seconds"] == 600 and lease["max_cost_cents"] == 100


# ---------------------------------------------------------------- the lease at the act


async def test_the_lease_is_read_at_the_act_not_at_planning() -> None:
    """The clock moves 150s between the step's admission and the act; the receipt says so."""
    world, clock = World(), FixedClock()
    events = await _run(ONE, Driver(world, clock, delay=150), clock)
    (receipt,) = _acts(events)
    assert isinstance(receipt.grounds, dict) and isinstance(receipt.grounds["lease"], dict)
    assert receipt.grounds["lease"]["max_wall_seconds"] == 450


async def test_a_driver_on_a_spent_lease_refuses_and_performs_nothing() -> None:
    """The step was admitted with 600s left; by the time the driver reaches the act, none is."""
    world, clock = World(), FixedClock()
    events = await _run(ONE, Driver(world, clock, delay=601), clock)
    assert world.sent == [], "the driver acted on a lease that had run out"
    assert _acts(events) == []
    observed = [e.observation for e in events if isinstance(e, Observed) and e.step == "s1"]
    assert len(observed) == 1 and isinstance(observed[0], Refused)
    assert "time" in observed[0].reason
    assert isinstance(events[-1], Ended)


def test_exhausted_names_what_ran_out() -> None:
    """Steps are not the act's question — the step the act runs inside was admitted already — so a
    lease with no steps left but time and money is not exhausted *for an act*."""
    assert exhausted(Lease(Ceiling(0, 10, 5), Floor(0))) is None
    assert exhausted(Lease(Ceiling(3, 10, None), Floor(0))) is None, "no cost ceiling is no limit"
    assert "time" in (exhausted(Lease(Ceiling(3, 0, 5), Floor(0))) or "")
    assert "spend" in (exhausted(Lease(Ceiling(3, 10, 0), Floor(0))) or "")


# ---------------------------------------------------------------- the key


async def test_a_key_names_the_act_and_a_second_act_gets_its_own() -> None:
    """The key is what lets a world tell a retry from a second, distinct act.

    **This test used to assert the opposite of the runtime's job.** It said *LangGraph re-runs a
    node on resume, so a driver under `Await` acts twice for one step* — and asserted
    `["r-1/s1", "r-1/s1", "r-1/s2"]`, encoding BUG-010 as though it were a feature the key
    excused. D38 stopped the runtime from causing that retry: a parked step resumes where it
    parked, so one step is one act. The key still matters — a **device** or a network may retry on
    its own, and `r-1/s1` is how the world recognises it — but the harness no longer manufactures
    the case.
    """
    from langgraph.checkpoint.memory import InMemorySaver

    world, clock = World(), FixedClock()

    class Parks(Driver):
        async def invoke(self, r: RegistrationId, inputs: JsonValue) -> Observation:
            await super().invoke(r, inputs)
            return Pending("waiting-on-the-world")

    twice = Composition((Await("s1", SEND.id, ()), Invoke("s2", SEND.id, ())))
    options = RunOptions(lease=Lease(CEILING, Floor(0)), run_id="r-1", checkpointer=InMemorySaver())
    ports = _ports(Parks(world, clock), clock)
    async for _ in run(twice, ports, options=options):
        pass
    assert [key for key, _ in world.sent] == ["r-1/s1"], "parked after one act"
    async for _ in resume(twice, {"delivered": True}, ports, options=options):
        pass
    keys = [key for key, _ in world.sent]
    assert keys == ["r-1/s1", "r-1/s2"], f"one act per step, not {keys}"


async def test_the_step_is_known_only_inside_the_act() -> None:
    """`current_run().step` is the step being executed — and nothing while the catalogue is read,
    which happens once per step, *before* the step's own scope opens."""
    world, clock = World(), FixedClock()
    driver = Driver(world, clock)
    two = Composition((Invoke("s1", SEND.id, ()), Invoke("s2", SEND.id, ())))
    await _run(two, driver, clock)
    assert driver.seen_steps == [None, "s1", None, "s2"], driver.seen_steps


async def test_there_is_no_key_outside_an_act() -> None:
    """A key names an act; asked for one while reading the catalogue, the runtime refuses rather
    than mint something that attributes nothing."""
    world, clock = World(), FixedClock()
    driver = Driver(world, clock)
    await _run(ONE, driver, clock)
    assert driver.keys_outside == ["RuntimeError"], driver.keys_outside


def test_the_scope_closes_behind_the_act() -> None:
    """Invisible through a run — LangGraph gives each node its own context copy — so the exit of
    the scope is exercised where it lives. A step left set would name the wrong act next."""
    from shadow_hdk.runtime.bindings import _STEP, executing

    with executing("s1"):
        assert _STEP.get() == "s1"
    assert _STEP.get() is None


async def test_a_completed_step_is_not_an_act() -> None:
    """The observation kinds stay distinct: `Completed` carries an output, `Acted` a receipt."""
    world, clock = World(), FixedClock()
    events = await _run(ONE, Driver(world, clock), clock)
    assert not [
        e for e in events if isinstance(e, Observed) and isinstance(e.observation, Completed)
    ]
