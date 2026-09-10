"""What a run has spent survives the park (D33, BUG-004).

`run` and `resume` each built a fresh `Session`, `LeaseMeter` and `Emitter`, and `RunState` said
nothing about spend — so a lease of three steps admitted five, `seq` restarted at 0 for one run id,
and `Ended.steps_taken` counted the last leg. An Ask is the ordinary way a governed run pauses, so
this was the lease failing in its commonest case.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    FanOut,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

WORK = make_registration("work")
COSTLY = make_registration("costly")
FIVE = Composition(tuple(Invoke(f"s{i}", WORK.id) for i in range(1, 6)))


class AsksOnce:
    """Governance that parks the run once, at a named step — an Ask, the ordinary pause."""

    def __init__(self, at: str = "s3") -> None:
        self.at, self.asked = at, 0

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.step == self.at and self.asked == 0:
            self.asked += 1
            return Ask("may it?")
        return Allow()


class Ran:
    def __init__(self) -> None:
        self.count = 0

    async def __call__(self, _inputs: JsonValue) -> Observation:
        self.count += 1
        return Completed(self.count)


async def _costly(_inputs: JsonValue) -> Observation:
    return Completed({"usage": {"input_tokens": 1, "output_tokens": 1, "cost_cents": 40}})


async def _unpriced(_inputs: JsonValue) -> Observation:
    return Completed({"usage": {"input_tokens": 1, "output_tokens": 1, "cost_cents": None}})


def _ports(ran: Any, governance: Any, clock: FixedClock | None = None) -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, ran), (COSTLY, ran)]),),
        governance=governance,
        sink=ListSink(),
        clock=clock or FixedClock(),
    )


def _options(steps: int = 3, *, seconds: int = 600, cents: int | None = 100) -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(steps, seconds, cents), Floor(0)),
        run_id="r",
        checkpointer=InMemorySaver(),
    )


async def _two_legs(
    composition: Composition, ports: Ports, options: RunOptions
) -> tuple[list[Event], list[Event]]:
    first = [e async for e in run(composition, ports, options=options)]
    after = [e async for e in resume(composition, "yes", ports, options=options)]
    return first, after


def _ended(events: list[Event]) -> Ended:
    ended = [e for e in events if isinstance(e, Ended)]
    assert len(ended) == 1, ended
    return ended[0]


# ---------------------------------------------------------------- the lease


async def test_a_lease_of_three_steps_admits_three_across_a_park() -> None:
    """The filed reproduction: five steps, a ceiling of three, an Ask on the third."""
    ran = Ran()
    ports = _ports(ran, AsksOnce())
    first, after = await _two_legs(FIVE, ports, _options())
    assert not [e for e in first if isinstance(e, Ended)], (
        "the first leg parked, so it has not ended"
    )
    assert ran.count == 3, f"a lease of three steps admitted {ran.count} invocations"
    assert _ended(after).reason == "lease_exhausted"


async def test_steps_taken_counts_the_run_not_the_last_leg() -> None:
    ran = Ran()
    ports = _ports(ran, AsksOnce())
    _, after = await _two_legs(FIVE, ports, _options(steps=10))
    assert ran.count == 5
    assert _ended(after).steps_taken == 5


async def test_the_sequence_does_not_restart_for_one_run() -> None:
    """Two events with the same `(run_id, seq)` are two different events on one record."""
    ran = Ran()
    ports = _ports(ran, AsksOnce())
    first, after = await _two_legs(FIVE, ports, _options(steps=10))
    seqs = [e.seq for e in first + after]
    assert seqs == sorted(seqs), seqs
    assert len(set(seqs)) == len(seqs), f"a seq was reused: {seqs}"


# ---------------------------------------------------------------- what else the meter holds


async def test_money_spent_before_the_park_is_still_spent_after_it() -> None:
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, _costly)]),),
        governance=AsksOnce(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    first, after = await _two_legs(FIVE, ports, _options(steps=10, cents=100))
    assert not [e for e in first if isinstance(e, Ended)]
    assert _ended(after).reason == "lease_exhausted", "40c a step under a 100c ceiling ran on"


async def test_a_price_nobody_could_report_is_still_unknown_after_the_park() -> None:
    """`cost_is_known` is the meter's honesty about its own total. One call the provider would not
    price makes the remaining budget unknowable, and a park must not restore false confidence."""
    seen: list[bool] = []

    class Unpriced:
        """Charges an unpriced call on the first leg, then reports what the meter believes."""

        async def __call__(self, _inputs: JsonValue) -> Observation:
            from shadow_hdk.runtime import current_run

            context = current_run()
            assert context is not None
            if not seen:
                return Completed(
                    {"usage": {"input_tokens": 1, "output_tokens": 1, "cost_cents": None}}
                )
            seen.append(context.remaining().ceiling.max_cost_cents is None)
            return Completed(None)

    unpriced = Unpriced()
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, unpriced)]),),
        governance=AsksOnce(at="s2"),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = _options(steps=10)
    first = [e async for e in run(FIVE, ports, options=options)]
    assert not [e for e in first if isinstance(e, Ended)]
    seen.append(True)  # the first leg is over; from here the component reports
    after = [e async for e in resume(FIVE, "yes", ports, options=options)]
    assert _ended(after).reason == "completed"
    assert seen[1:] and all(seen[1:]), "the meter forgot that a call it charged for was unpriced"


async def test_time_spent_waiting_for_a_person_is_not_spent() -> None:
    """A run parked on an Ask is not running. A person who takes a day must not find it gone —
    and the seconds the run itself used must still count."""
    clock = FixedClock()
    ran = Ran()
    ports = _ports(ran, AsksOnce(), clock)
    options = _options(steps=10, seconds=60)
    first = [e async for e in run(FIVE, ports, options=options)]
    assert not [e for e in first if isinstance(e, Ended)]
    clock.advance(86_400)  # a day at the human's end of the Ask
    after = [e async for e in resume(FIVE, "yes", ports, options=options)]
    assert _ended(after).reason == "completed", "the wait was charged to the run"
    assert ran.count == 5


async def test_seconds_the_run_itself_used_survive_the_park() -> None:
    """The other half: what the run spent before parking is still spent."""
    clock = FixedClock()
    slow = Ran()

    async def _slow(inputs: JsonValue) -> Observation:
        clock.advance(20)
        return await slow(inputs)

    ports = _ports(_slow, AsksOnce(), clock)
    options = _options(steps=10, seconds=50)
    first = [e async for e in run(FIVE, ports, options=options)]
    assert not [e for e in first if isinstance(e, Ended)]
    after = [e async for e in resume(FIVE, "yes", ports, options=options)]
    assert _ended(after).reason == "lease_exhausted", "40s spent before the park was forgotten"


async def test_a_fan_out_merges_in_any_order() -> None:
    """The reducer has to be commutative: branches write concurrently."""
    ran = Ran()
    branches = Composition(
        (
            FanOut("fan", tuple(Invoke(f"b{i}", WORK.id) for i in range(1, 5))),
            Invoke("after", WORK.id),
        )
    )
    ports = _ports(ran, AsksOnce(at="after"))
    options = _options(steps=10)
    first = [e async for e in run(branches, ports, options=options)]
    assert not [e for e in first if isinstance(e, Ended)]
    after = [e async for e in resume(branches, "yes", ports, options=options)]
    assert _ended(after).steps_taken == 5, "four branches and the step after them"
    assert ran.count == 5


async def test_a_run_that_never_parks_is_unchanged() -> None:
    ran = Ran()

    class Allows:
        async def judge(self, _e: EffectProfile, _c: Context) -> Judgement:
            return Allow()

    ports = _ports(ran, Allows())
    events = [e async for e in run(FIVE, ports, options=_options(steps=10))]
    assert ran.count == 5
    ended = _ended(events)
    assert ended.reason == "completed" and ended.steps_taken == 5
    observed = [e for e in events if isinstance(e, Observed)]
    assert len(observed) == 5


async def test_the_sequence_does_not_restart_after_an_await_parks() -> None:
    """The other parking path: an `Await` told to wait emits its `Observed(Pending)` after the
    last node returned, exactly as an ask emits `Asked`."""
    from shadow_hdk.kernel import Await, Pending

    slow = make_registration("slow")
    answers: list[Observation] = [Pending("job-1"), Completed("done")]

    async def _pop(_inputs: JsonValue) -> Observation:
        return answers.pop(0) if len(answers) > 1 else answers[0]

    class Allows:
        async def judge(self, _e: EffectProfile, _c: Context) -> Judgement:
            return Allow()

    waiting = Composition((Invoke("s1", WORK.id), Await("w1", slow.id), Invoke("s2", WORK.id)))
    ran = Ran()
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, ran), (slow, _pop)]),),
        governance=Allows(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = _options(steps=10)
    first = [e async for e in run(waiting, ports, options=options)]
    assert not [e for e in first if isinstance(e, Ended)], "the await parked"
    after = [e async for e in resume(waiting, {"result": "ok"}, ports, options=options)]
    seqs = [e.seq for e in first + after]
    assert seqs == sorted(seqs), seqs
    assert len(set(seqs)) == len(seqs), f"a seq was reused across an await: {seqs}"
    assert _ended(after).reason == "completed"


async def test_a_step_charged_before_the_park_is_not_charged_again() -> None:
    """The meter counts what ran. A resumed leg must not re-count the legs before it."""
    ran = Ran()
    ports = _ports(ran, AsksOnce())
    first, after = await _two_legs(FIVE, ports, _options(steps=10))
    assert _ended(after).steps_taken == ran.count, "the meter and the world disagree"


async def test_a_new_run_on_a_used_thread_does_not_inherit_its_spend() -> None:
    """`run` starts a run; `resume` continues one. A host that reuses a run id — a retry after a
    crash, a fixed id in a test — must not be handed the last run's meter."""

    class Allows:
        async def judge(self, _e: EffectProfile, _c: Context) -> Judgement:
            return Allow()

    ran = Ran()
    ports = _ports(ran, Allows())
    saver = InMemorySaver()
    options = RunOptions(
        lease=Lease(Ceiling(6, 600, 100), Floor(0)), run_id="reused", checkpointer=saver
    )
    first = [e async for e in run(FIVE, ports, options=options)]
    assert _ended(first).steps_taken == 5
    again = [e async for e in run(FIVE, ports, options=options)]
    assert _ended(again).reason == "completed", "the second run inherited the first run's spend"
    assert _ended(again).steps_taken == 5


def test_the_reducer_does_not_care_which_branch_arrives_first() -> None:
    """A `FanOut` writes concurrently, so the total must be the same in any order — and a mark
    must be the furthest any branch reached, not whichever landed last."""
    from shadow_hdk.runtime.state import merge_spent, no_spend

    early = {"steps": 1, "cost_cents": 5, "unpriced": 0, "elapsed_seconds": 9.0, "seq": 11}
    late = {"steps": 1, "cost_cents": 7, "unpriced": 1, "elapsed_seconds": 2.0, "seq": 4}
    assert merge_spent(early, late) == merge_spent(late, early)
    assert merge_spent(early, late) == {
        "steps": 2,
        "cost_cents": 12,
        "unpriced": 1,
        "elapsed_seconds": 9.0,
        "seq": 11,
    }
    third = {"steps": 1, "cost_cents": 1, "unpriced": 0, "elapsed_seconds": 20.0, "seq": 2}
    assert merge_spent(merge_spent(early, late), third) == merge_spent(
        early, merge_spent(late, third)
    )
    assert merge_spent(no_spend(), early) == {**no_spend(), **early}


def test_a_restore_never_moves_the_record_backwards() -> None:
    """The numbering only goes forward. A checkpoint older than what this emitter has already
    stamped would otherwise hand two events the same number."""
    from shadow_hdk.runtime.emit import Emitter

    emitter = Emitter("r", FixedClock(), None)
    emitter.restore(9)
    assert emitter.seq == 9
    emitter.restore(4)
    assert emitter.seq == 9, "a stale mark pulled the numbering back"
