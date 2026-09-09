"""A component raising is data; a port raising is a failure (D7).

A component arrives from anywhere and is untrusted: its exception becomes a `Failed` observation the
agent can see and route around. A port is the host, and a broken host is not something the runtime
can reason past.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import Binding, Context, EffectProfile, Failed, Invoke, Judgement
from shadow_hdk.runtime.errors import PortFailure
from shadow_hdk.runtime.state import initial_state
from shadow_hdk.runtime.testing import Judge, make_registration
from tests.runtime.conftest import executor_over


async def test_a_component_raising_is_a_failed_observation() -> None:
    reg = make_registration("flaky")

    async def boom(inputs: object) -> object:
        raise RuntimeError("the vendor is down")

    ex, _, emitter = executor_over([(reg, boom)])
    observation = await ex.invoke(Invoke("s1", reg.id), initial_state())
    assert isinstance(observation, Failed)
    assert "RuntimeError: the vendor is down" in observation.error
    emitter.close()
    assert [e.kind async for e in emitter.stream()] == ["invoked", "observed"]


async def test_an_unknown_component_is_a_failed_observation_not_a_crash() -> None:
    ex, _, _ = executor_over([])
    observation = await ex.invoke(Invoke("s1", "nobody"), initial_state())
    assert isinstance(observation, Failed)
    assert "nobody" in observation.error


async def test_a_dangling_reference_is_a_failed_observation() -> None:
    reg = make_registration("search")
    ex, components, _ = executor_over([(reg, "ok")])
    step = Invoke("s2", reg.id, (Binding("q", ref="s1"),))
    observation = await ex.invoke(step, initial_state())
    assert isinstance(observation, Failed)
    assert "s1" in observation.error
    assert components.calls == []


async def test_a_governance_port_raising_ends_the_run() -> None:
    reg = make_registration("search")

    def explode(effects: EffectProfile, context: Context) -> Judgement:
        raise ConnectionError("policy service unreachable")

    ex, _, _ = executor_over([(reg, "ok")], judge=Judge(explode))
    with pytest.raises(PortFailure) as caught:
        await ex.invoke(Invoke("s1", reg.id), initial_state())
    assert caught.value.port == "governance"
    assert caught.value.reason == "failed"
