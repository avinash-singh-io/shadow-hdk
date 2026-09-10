"""A parked run resumes over the wire, and the wire says what it does not do (BUG-006).

Four separate failures under one row, each reproduced here before it was fixed: a resume that
always raised, a `run` that never needed `initialize`, an omitted protocol version that counted as
a match, and a host that could hang a run past its own wall ceiling by never answering a callback.
"""

from __future__ import annotations

import json
from typing import Any

import anyio
import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Ended,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Ports, RunOptions
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.protocol import PROTOCOL_VERSION, RUN
from shadow_hdk.wire.sides import loopback

WORK = make_registration("work")
THREE = Composition(tuple(Invoke(f"s{i}", WORK.id) for i in range(1, 4)))


class AsksOnce:
    def __init__(self, at: str = "s2") -> None:
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


def _ports(governance: Any, ran: Any) -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, ran)]),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )


def _options() -> RunOptions:
    return RunOptions(lease=Lease(Ceiling(10, 600, 100), Floor(0)), run_id="over-the-wire")


# ---------------------------------------------------------------- the resume


async def test_a_run_parked_over_the_wire_can_be_resumed() -> None:
    """The whole point of an Ask crossing the wire: somebody answers it."""
    ran = Ran()
    ports = _ports(AsksOnce(), ran)
    async with loopback(ports) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(30):
            await host.run(THREE, _options())
        assert not [e for e in host.events if isinstance(e, Ended)], "the run parked"
        host.events.clear()
        with anyio.fail_after(30):
            await host.resume(THREE, "yes", _options())
    ended = [e for e in host.events if isinstance(e, Ended)]
    assert ended and ended[-1].reason == "completed", host.events
    assert ran.count == 3


async def test_the_resumed_run_keeps_the_lease_it_was_parked_with() -> None:
    """D33 over the wire: the second leg is the same run, not a new one."""
    ran = Ran()
    ports = _ports(AsksOnce(), ran)
    async with loopback(ports) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(30):
            await host.run(THREE, _options())
        with anyio.fail_after(30):
            await host.resume(THREE, "yes", _options())
    ended = [e for e in host.events if isinstance(e, Ended)]
    assert ended[-1].steps_taken == 3, "the wire's resume started the meter again"


# ---------------------------------------------------------------- the handshake


async def test_a_run_before_initialize_is_refused() -> None:
    """`initialized` was set and never read. Two peers that have not agreed a version are two
    peers that do not yet know what a message means."""
    ran = Ran()
    async with loopback(_ports(AsksOnce("never"), ran)) as (host, _runtime):
        with pytest.raises(RemoteError) as refused:
            await host.peer.call(
                RUN,
                {
                    "composition": json.loads(dump(THREE, Composition)),
                    "lease": json.loads(dump(_options().lease, Lease)),
                },
            )
    assert "initialize" in str(refused.value)
    assert ran.count == 0, "the run started before the peers had agreed anything"


async def test_an_omitted_protocol_version_is_a_mismatch_not_a_match() -> None:
    """It defaulted to `PROTOCOL_VERSION` — so a peer that said nothing was treated as agreeing.
    Refuse, never degrade: silence is not agreement."""
    async with loopback() as (host, _runtime):
        with pytest.raises(RemoteError) as refused:
            await host.peer.call("initialize", {})
    assert PROTOCOL_VERSION in str(refused.value)


async def test_the_version_that_is_offered_is_still_checked() -> None:
    async with loopback() as (host, _runtime):
        with pytest.raises(RemoteError):
            await host.peer.call("initialize", {"protocol_version": "0.0.1-not-this"})
        assert await host.peer.call("initialize", {"protocol_version": PROTOCOL_VERSION})


# ---------------------------------------------------------------- the host that never answers


async def test_a_host_that_never_answers_a_callback_ends_the_run() -> None:
    """A run whose wall ceiling is 600s must not wait forever on a host that hangs in `judge`.
    The timeout belongs to the wire, not to the lease: the lease bounds the *run*, and a run that
    is not running cannot notice it."""

    class Hangs:
        async def judge(self, _effects: EffectProfile, _context: Context) -> Judgement:
            await anyio.sleep(3600)
            return Allow()

    ran = Ran()
    ports = _ports(Hangs(), ran)
    async with loopback(ports, timeout=0.25) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(30):
            await host.run(THREE, _options())
    ended = [e for e in host.events if isinstance(e, Ended)]
    assert ended and ended[-1].reason == "failed", host.events
    assert "judge" in (ended[-1].detail or ""), ended[-1].detail
    assert ran.count == 0


# ---------------------------------------------------------------- what serve admits


async def test_a_session_is_issued_to_anyone_only_on_loopback() -> None:
    """With no token the door is open, which is why it may only face loopback."""
    import httpx

    from shadow_hdk.wire import served_over_http

    async with served_over_http() as address:
        assert address.startswith("http://127.0.0.1:")
        async with (
            httpx.AsyncClient(timeout=10.0) as client,
            client.stream("GET", f"{address}/rpc") as response,
        ):
            assert response.status_code == 200


async def test_a_token_is_required_when_one_is_set() -> None:
    import httpx

    from shadow_hdk.wire import served_over_http

    async with (
        served_over_http(token="a-test-token") as address,
        httpx.AsyncClient(timeout=10.0) as client,
    ):
        async with client.stream("GET", f"{address}/rpc") as bare:
            assert bare.status_code == 401
        posted = await client.post(f"{address}/rpc", json={}, headers={"x-shadow-hdk-session": "x"})
        assert posted.status_code == 401
        async with client.stream(
            "GET", f"{address}/rpc", headers={"authorization": "Bearer a-test-token"}
        ) as allowed:
            assert allowed.status_code == 200


async def test_serving_beyond_loopback_without_a_token_is_refused() -> None:
    """Refused before anything binds — the check is the point, not the socket."""
    from shadow_hdk.wire import served_over_http

    with pytest.raises(ValueError, match="not built"):
        async with served_over_http(host="0.0.0.0", token=None):  # noqa: S104
            pass
