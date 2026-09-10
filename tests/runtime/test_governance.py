"""Every step is judged before it runs, over effects, never over a name.

The Refuse path and the context handed to the policy are asserted here, directly on the executor.
The Ask path needs a graph to `interrupt()` inside, so it is asserted in `test_compile.py`.
"""

from __future__ import annotations

from shadow_hdk.kernel import (
    Allow,
    Binding,
    Completed,
    EffectProfile,
    Invoke,
    Refuse,
    Refused,
    ScopeSet,
)
from shadow_hdk.runtime.state import initial_state
from shadow_hdk.runtime.testing import Judge, make_registration
from tests.runtime.conftest import executor_over

REACHES = EffectProfile(reaches=True, reversible=False)


async def test_a_refusal_never_reaches_the_component() -> None:
    reg = make_registration("send_email", effects=REACHES)
    ex, components, emitter = executor_over(
        [(reg, "ok")], judge=Judge(lambda e, c: Refuse("not in this mode"))
    )
    observation = await ex.invoke(Invoke("s1", reg.id), initial_state())
    assert observation == Refused("not in this mode")
    assert components.calls == []


async def test_a_refusal_is_on_the_record_as_an_event() -> None:
    reg = make_registration("send_email", effects=REACHES)
    ex, _, emitter = executor_over([(reg, "ok")], judge=Judge(lambda e, c: Refuse("no")))
    await ex.invoke(Invoke("s1", reg.id), initial_state())
    emitter.close()
    kinds = [e.kind async for e in emitter.stream()]
    assert kinds == ["refused"]


async def test_an_allowed_step_runs_and_is_observed() -> None:
    reg = make_registration("search")
    ex, components, emitter = executor_over([(reg, {"hits": 3})])
    observation = await ex.invoke(
        Invoke("s1", reg.id, (Binding("q", value="lathe"),)), initial_state()
    )
    assert observation == Completed({"hits": 3})
    assert components.calls == [(reg.id, {"q": "lathe"})]
    emitter.close()
    assert [e.kind async for e in emitter.stream()] == ["invoked", "observed"]


async def test_the_policy_is_judged_on_effects_and_told_who_is_asking() -> None:
    reg = make_registration("write", effects=EffectProfile(writes=ScopeSet.of("workspace")))
    judge = Judge(lambda e, c: Allow())
    ex, _, _ = executor_over(
        [(reg, "ok")], judge=judge, context={"mode": "build"}, principal="person:7"
    )
    await ex.invoke(Invoke("s1", reg.id), initial_state())
    effects, context = judge.calls[0]
    assert effects == reg.component.effects
    assert (context.step, context.principal) == ("s1", "person:7")
    # The run's own context, and — since D30 — what is being judged: its id and its posture.
    assert context.attributes == {"mode": "build", "posture": "controlled", "component": "write"}
    assert context.run_id == "run-under-test"


async def test_a_component_the_policy_would_always_refuse_is_not_visible() -> None:
    """Absent, not greyed out — and through a run, because `RunContext.visible()` is the one
    computation the model's catalogue comes from; the executor has no second one."""
    from pydantic import JsonValue

    from shadow_hdk.kernel import Ceiling, Completed, Composition, Floor, Lease, Observation
    from shadow_hdk.runtime import RunOptions, current_run, run
    from tests.runtime.conftest import ports_over

    shown = make_registration("read", effects=EffectProfile(reads=ScopeSet.of("workspace")))
    hidden = make_registration("send_email", effects=REACHES)
    asks = make_registration("asks")
    seen: list[set[str]] = []

    async def looks(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        seen.append({r.id for r in await context.visible()})
        return Completed(None)

    judge = Judge(lambda e, c: Refuse("no reaching") if e.reaches else Allow())
    ports, _ = ports_over([(shown, "ok"), (hidden, "ok"), (asks, looks)], judge=judge)
    async for _ in run(
        Composition((Invoke("s1", asks.id),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(5, 600, 10), Floor(0))),
    ):
        pass
    assert seen == [{"read", "asks"}], seen
