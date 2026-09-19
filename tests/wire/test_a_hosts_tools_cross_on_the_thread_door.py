"""ENH-030: the thread door carries the host's components by inversion, as `run` always has (D21).

A host in any language keeps its tools as code on its own side of the wire. `thread/start
{host_components: true}` tells the runtime to add a `RemoteComponents` port for the calling peer to
that thread's registry: the agent sees the host's tools beside the served ones, a call comes back
over the wire as `components.invoke`, the host's function runs, and the record carries what it
returned — judged, admitted and recorded exactly as a local port's act would be.

A thread outlives a connection, so a host that goes away takes its tools with it **by name**, and a
new connection's `thread/resume {host_components: true}` brings its own.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.testing import ScriptedAgent
from shadow_hdk.wire.sides import loopback

from .test_a_thread_crosses_the_wire import AllowAll, ScriptedThreads, _keeper

pytestmark = pytest.mark.anyio

GREET = make_registration("greet", effects=EffectProfile())
# Irreversible and uncontained on the host's side: the runtime never held its authority boundary,
# so the record must say `observed`, not `controlled` (D99–D104, as `run` already does).
NOTIFY = make_registration(
    "notify", effects=EffectProfile(reaches=True, reversible=False, contained=False)
)
greeted: list[Any] = []


async def greet(inputs: Any) -> Any:
    greeted.append(inputs)
    return Completed({"greeting": f"hello, {inputs.get('name', 'stranger')}"})


async def notify(_inputs: Any) -> Any:
    return Completed({"sent": True})


def host_ports() -> Ports:
    """The host's side of the wire: its own tools, its own governance, its own sink."""
    return Ports(
        model=None,
        components=(InMemoryComponents([(GREET, greet), (NOTIFY, notify)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


class ToolCallingThreads(ScriptedThreads):
    """The runtime's side: a thread host whose scripted agent calls the tools it is told to, and
    which takes the peer's components the wire hands it — the new keyword of the protocol."""

    def __init__(self, tmp_path: Path, calls: list[tuple[str, dict[str, Any]]]) -> None:
        super().__init__(tmp_path)
        self.agent: Any = ScriptedAgent([(calls, "done"), (calls, "done again")])
        self.peer_components_seen: list[Any] = []

    async def open(  # type: ignore[override]
        self,
        *,
        root: str,
        mode: str,
        want: str | None,
        name: str,
        observer: Any,
        roots: Any = None,
        peer_components: Any = (),
    ) -> Thread:
        self.peer_components_seen.append(tuple(peer_components))
        ports = self._ports(observer)
        ports = Ports(
            model=ports.model,
            components=(*ports.components, *peer_components),
            governance=ports.governance,
            sink=ports.sink,
            clock=ports.clock,
            observer=ports.observer,
        )
        thread = await Thread.open(
            agent=cast(Any, self.agent),
            ports=ports,
            store=self.threads,
            root=root or str(self._tmp),
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            name=name,
            approvals=self.approvals,
            mode=mode,
            provider="scripted",
        )
        self.agent.reach = thread.registry.call
        return thread

    async def resume(  # type: ignore[override]
        self, thread_id: str, *, observer: Any, peer_components: Any = ()
    ) -> Thread:
        self.peer_components_seen.append(tuple(peer_components))
        ports = self._ports(observer)
        ports = Ports(
            model=ports.model,
            components=(*ports.components, *peer_components),
            governance=ports.governance,
            sink=ports.sink,
            clock=ports.clock,
            observer=ports.observer,
        )
        thread = await Thread.resume(
            thread_id,
            agent=cast(Any, self.agent),
            ports=ports,
            store=self.threads,
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            approvals=self.approvals,
        )
        self.agent.reach = thread.registry.call
        return thread


async def test_the_hosts_tool_is_offered_called_and_on_the_record(tmp_path: Path) -> None:
    greeted.clear()
    threads = ToolCallingThreads(tmp_path, [("greet", {"name": "ana"})])
    heard: list[tuple[str, dict[str, Any]]] = []
    async with loopback(ports=host_ports(), threads=threads) as (host, _runtime):
        await host.initialize()
        host.peer.hears("event", _keeper(heard, "event"))
        started = await host.peer.call(
            "thread/start",
            {"root": str(tmp_path), "mode": "workspace-write", "host_components": True},
        )
        tools = await host.peer.call("tools/list", {"thread_id": started["thread_id"]})
        by_id = {t["id"]: t for t in tools["tools"]}
        assert "greet" in by_id, "the host's tool is offered beside the served ones"
        assert by_id["greet"]["source"] == "host", by_id["greet"]["source"]
        assert by_id["greet"]["registration"]["component"]["provenance"][
            "registered_by"
        ].startswith("host:")
        assert "look" in by_id, "the served composition's own tools are still there"

        with anyio.fail_after(30):
            await host.peer.call(
                "turn/start", {"thread_id": started["thread_id"], "text": "greet ana"}
            )
        events = [p["event"] for _, p in heard]
        invoked = [e for e in events if e["kind"] == "invoked" and e["component"] == "greet"]
        assert invoked, [e["kind"] for e in events]
        observed = next(
            e for e in events if e["kind"] == "observed" and e["step"] == invoked[0]["step"]
        )
        assert observed["observation"] == {
            "kind": "completed",
            "output": {"greeting": "hello, ana"},
        }
        assert greeted == [{"name": "ana"}], "the function ran on the host's side, once"
        await host.peer.call("thread/close", {"thread_id": started["thread_id"]})


async def test_without_the_flag_no_host_port_is_added(tmp_path: Path) -> None:
    threads = ToolCallingThreads(tmp_path, [])
    async with loopback(ports=host_ports(), threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call("thread/start", {"root": str(tmp_path), "mode": "ask"})
        tools = await host.peer.call("tools/list", {"thread_id": started["thread_id"]})
        assert "greet" not in {t["id"] for t in tools["tools"]}
        assert threads.peer_components_seen == [()], "nothing handed in when nothing was asked"
        await host.peer.call("thread/close", {"thread_id": started["thread_id"]})


async def test_an_irreversible_host_tool_is_observed_not_controlled(tmp_path: Path) -> None:
    threads = ToolCallingThreads(tmp_path, [("notify", {})])
    heard: list[tuple[str, dict[str, Any]]] = []
    async with loopback(ports=host_ports(), threads=threads) as (host, _runtime):
        await host.initialize()
        host.peer.hears("event", _keeper(heard, "event"))
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "full", "host_components": True}
        )
        with anyio.fail_after(30):
            await host.peer.call("turn/start", {"thread_id": started["thread_id"], "text": "go"})
        events = [p["event"] for _, p in heard]
        step = next(
            e["step"] for e in events if e["kind"] == "invoked" and e["component"] == "notify"
        )
        observed = next(e for e in events if e["kind"] == "observed" and e["step"] == step)
        assert observed["posture"] == "observed", "the runtime never held the host's authority"
        assert observed["observation"]["kind"] == "completed"
        await host.peer.call("thread/close", {"thread_id": started["thread_id"]})


async def test_a_host_that_is_gone_takes_its_tools_with_it_by_name() -> None:
    """The unit of P44-2, on the port itself: a closed peer is an empty catalogue that says why,
    and an act in flight fails naming the host — never a hang, never a silent nothing."""
    from shadow_hdk.kernel.observations import Failed
    from shadow_hdk.wire.remote import RemoteComponents

    class ClosedPeer:
        async def call(self, method: str, params: Any) -> Any:
            from shadow_hdk.wire.peer import GONE, RemoteError

            raise RemoteError(GONE, "the other end closed", {"kind": "gone"})

    port = RemoteComponents(cast(Any, ClosedPeer()), session="s-1")
    assert await port.registrations() == []
    assert port.problem and "host" in port.problem and "s-1" in port.problem
    failed = await port.invoke("greet", {"name": "ana"})
    assert isinstance(failed, Failed) and "greet" in failed.reason and "gone" in failed.reason
