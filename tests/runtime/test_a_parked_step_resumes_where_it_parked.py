"""A step that parked resumes where it parked (D38, BUG-010).

LangGraph re-runs a node from the top, and `interrupt()` returns the answer only at the point it
was raised — so everything above it happened a second time. **Reproduced before the fix:**

* an `Await` called its component **twice** and emitted `Invoked` twice for one step;
* a policy answering `Refuse` on the re-run **overrode the host's `Allow`**;
* a policy answering `Allow` on the re-run **dropped the host's `Refuse`** and ran the work — the
  worst of the three, because consent-before-effect is exactly what an Ask is for;
* two Asks in one `FanOut` took one resume each, and the already-answered branch ran again on the
  second — three invocations for two steps.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Await,
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
    Pending,
    Refused,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement, Refuse
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

SLOW = make_registration("slow")
WORK = make_registration("work")


class Counts:
    def __init__(self, answer: Observation | None = None) -> None:
        self.calls = 0
        self._answer = answer

    async def __call__(self, _inputs: JsonValue) -> Observation:
        self.calls += 1
        return self._answer if self._answer is not None else Completed(self.calls)


class Changes:
    """A policy that answers one way the first time it is asked about a step and another after."""

    def __init__(self, first: Judgement, later: Judgement, about: tuple[str, ...]) -> None:
        self.first, self.later, self.about = first, later, about
        self.asked = 0

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.step in self.about:
            self.asked += 1
            return self.first if self.asked == 1 else self.later
        return Allow()


def _ports(governance: Any, **components: Any) -> Ports:
    entries = [
        (SLOW, components.get("slow", Counts(Pending("job-1")))),
        (WORK, components.get("work", Counts())),
    ]
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents(entries),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )


def _options(saver: Any, run_id: str = "r") -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(20, 600, 100), Floor(0)), run_id=run_id, checkpointer=saver
    )


def _ended(events: list[Event]) -> list[Ended]:
    return [e for e in events if isinstance(e, Ended)]


# ---------------------------------------------------------------- the await


async def test_an_await_calls_its_component_once() -> None:
    """It answered `Pending`; the answer comes from whoever resumes, not from asking again."""
    slow = Counts(Pending("job-1"))
    saver = InMemorySaver()
    waiting = Composition((Await("w1", SLOW.id),))
    ports = _ports(Changes(Allow(), Allow(), ()), slow=slow)
    first = [e async for e in run(waiting, ports, options=_options(saver))]
    after = [e async for e in resume(waiting, {"done": True}, ports, options=_options(saver))]
    assert slow.calls == 1, f"the component was called {slow.calls} times for one step"
    invoked = [e for e in first + after if e.kind == "invoked" and e.step == "w1"]
    assert len(invoked) == 1, f"one step, {len(invoked)} Invoked events"
    assert _ended(after)[-1].reason == "completed"


async def test_the_awaited_answer_is_what_the_step_observed() -> None:
    slow = Counts(Pending("job-1"))
    saver = InMemorySaver()
    waiting = Composition((Await("w1", SLOW.id),))
    ports = _ports(Changes(Allow(), Allow(), ()), slow=slow)
    [e async for e in run(waiting, ports, options=_options(saver))]
    after = [e async for e in resume(waiting, {"result": "ok"}, ports, options=_options(saver))]
    observed = [e.observation for e in after if e.kind == "observed" and e.step == "w1"]
    assert observed == [Completed({"result": "ok"})]


# ---------------------------------------------------------------- the human's answer wins


async def test_a_later_refusal_does_not_override_the_answer_the_host_gave() -> None:
    """The host said `Allow`. A policy that changed its mind while the human was thinking does not
    get to overrule the human it asked."""
    work = Counts()
    saver = InMemorySaver()
    asking = Composition((Invoke("a1", WORK.id),))
    ports = _ports(Changes(Ask("may it?"), Refuse("changed my mind"), ("a1",)), work=work)
    [e async for e in run(asking, ports, options=_options(saver, "r2"))]
    after = [e async for e in resume(asking, Allow(), ports, options=_options(saver, "r2"))]
    refusals = [e for e in after if e.kind == "refused"]
    assert not refusals, f"the human's Allow was overruled: {[e.reason for e in refusals]}"
    assert work.calls == 1


async def test_a_later_allow_does_not_discard_the_refusal_the_host_gave() -> None:
    """The worst of the three: the host said no, and the work ran anyway. Consent before effect is
    the whole reason an Ask exists."""
    work = Counts()
    saver = InMemorySaver()
    asking = Composition((Invoke("a1", WORK.id),))
    ports = _ports(Changes(Ask("may it?"), Allow(), ("a1",)), work=work)
    [e async for e in run(asking, ports, options=_options(saver, "r3"))]
    after = [
        e
        async for e in resume(
            asking, Refuse("the human said no"), ports, options=_options(saver, "r3")
        )
    ]
    assert work.calls == 0, "the step ran after the host refused it"
    observed = [e.observation for e in after if e.kind == "observed" and e.step == "a1"]
    assert observed and isinstance(observed[0], Refused)
    assert "the human said no" in observed[0].reason


# ---------------------------------------------------------------- a fan-out that asks twice


async def test_one_answer_resumes_every_step_that_was_asked_about() -> None:
    """Two Asks in one superstep took one resume each, and the branch already answered ran again
    on the second — three invocations for two steps."""
    work = Counts()
    saver = InMemorySaver()
    fan = Composition((FanOut("fan", (Invoke("a1", WORK.id), Invoke("a2", WORK.id))),))
    ports = _ports(Changes(Ask("may it?"), Ask("may it?"), ("a1", "a2")), work=work)
    first = [e async for e in run(fan, ports, options=_options(saver, "r4"))]
    assert sorted(e.step for e in first if e.kind == "asked") == ["a1", "a2"]
    after = [e async for e in resume(fan, Allow(), ports, options=_options(saver, "r4"))]
    assert _ended(after), "one answer did not finish a fan-out that asked twice"
    assert _ended(after)[-1].reason == "completed"
    assert work.calls == 2, f"two steps ran {work.calls} times"


async def test_an_answer_can_be_addressed_to_each_step_by_name() -> None:
    """One answer for all of them is the common case; two different answers needs a way to say
    which is which, and the step id is the name the caller already has."""
    work = Counts()
    saver = InMemorySaver()
    fan = Composition((FanOut("fan", (Invoke("a1", WORK.id), Invoke("a2", WORK.id))),))
    ports = _ports(Changes(Ask("may it?"), Ask("may it?"), ("a1", "a2")), work=work)
    [e async for e in run(fan, ports, options=_options(saver, "r5"))]
    after = [
        e
        async for e in resume(
            fan, {"a1": Allow(), "a2": Refuse("not this one")}, ports, options=_options(saver, "r5")
        )
    ]
    assert _ended(after)[-1].reason == "completed"
    observed = {e.step: e.observation for e in after if e.kind == "observed"}
    assert isinstance(observed["a2"], Refused) and "not this one" in observed["a2"].reason
    assert work.calls == 1, "the refused branch ran"


async def test_a_run_that_never_parked_is_unchanged() -> None:
    work = Counts()
    saver = InMemorySaver()
    plain = Composition((Invoke("s1", WORK.id), Invoke("s2", WORK.id)))
    ports = _ports(Changes(Allow(), Allow(), ()), work=work)
    events = [e async for e in run(plain, ports, options=_options(saver, "r6"))]
    assert work.calls == 2
    assert _ended(events)[-1].reason == "completed"


async def test_a_step_resumes_once_even_when_it_runs_again_in_a_loop() -> None:
    """A step resumes at its interrupt **once**. Inside an `Until`, the same step id runs again on
    the very leg that resumed it — and a second visit is an ordinary step, judged like any other.
    Treating it as still-resuming would send it back to an interrupt that is no longer there."""
    from shadow_hdk.kernel import Condition, Until

    work = Counts(Completed({"ok": False}))
    saver = InMemorySaver()
    looping = Composition(
        (Until("loop", Invoke("a1", WORK.id), Condition("ok", True), max_iterations=3),)
    )
    ports = _ports(Changes(Ask("may it?"), Allow(), ("a1",)), work=work)
    first = [e async for e in run(looping, ports, options=_options(saver, "r7"))]
    assert [e.step for e in first if e.kind == "asked"] == ["a1"], "the first visit asked"
    after = [e async for e in resume(looping, Allow(), ports, options=_options(saver, "r7"))]
    assert _ended(after), "the loop never finished after its first step was answered"
    assert work.calls >= 2, f"the loop ran {work.calls} times; the later visits were not steps"
