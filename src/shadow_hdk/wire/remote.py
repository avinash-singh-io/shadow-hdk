"""The inverted ports: what the runtime holds when its ports live on the other side.

`wire.md` lists four callbacks — judge, complete, invoke, propose — and the event stream. Two of the
six ports are deliberately **not** here:

* **The clock stays runtime-side.** Every event carries an `at`, so inverting the clock would add a
  round-trip per stamp — the most frequent call in the system — to learn the time, which is not a
  policy and not the host's to decide. A host that needs deterministic time replays the record,
  which already carries it.
* **The observer is the event stream.** Inverting it as well would deliver every event twice, once
  as a callback and once as a notification, and a host would have to know they were the same thing.

Everything crossing here is a kernel contract type, encoded with `dump` and decoded with `load`, so
what travels is exactly what `tests/kernel/test_contracts_round_trip.py` already pins.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import replace
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Observation, Proposal
from shadow_hdk.kernel.ports import (
    ComponentPort,
    Context,
    GovernancePort,
    Judgement,
    ModelChunk,
    ModelPort,
    ModelRequest,
    ModelResponse,
    SinkPort,
)
from shadow_hdk.wire.peer import GONE, Peer, RemoteError
from shadow_hdk.wire.protocol import COMPLETE, INVOKE, JUDGE, PROPOSE, REGISTRATIONS


def _run_id_of(context: Any) -> str:
    return str(context.run_id) if context is not None else ""


def _step_of(context: Any) -> str:
    return str(context.step or "") if context is not None else ""


def _as_json(value: object, as_type: Any) -> JsonValue:
    parsed: JsonValue = json.loads(dump(value, as_type))
    return parsed


class RemoteGovernance(GovernancePort):
    """The runtime asks; the host's policy answers."""

    def __init__(self, peer: Peer) -> None:
        self._peer = peer

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        answered = await self._peer.call(
            JUDGE,
            {
                "effects": _as_json(effects, EffectProfile),
                "context": _as_json(context, Context),
            },
        )
        judgement: Judgement = load(json.dumps(answered), Judgement)
        return judgement


class RemoteModel(ModelPort):
    """The runtime asks; the host's model answers."""

    def __init__(self, peer: Peer) -> None:
        self._peer = peer

    async def complete(self, request: ModelRequest) -> ModelResponse:
        answered = await self._peer.call(COMPLETE, {"request": _as_json(request, ModelRequest)})
        return load(json.dumps(answered), ModelResponse)

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]:
        """The port's own default — one chunk from `complete` (D14). Streaming over the wire is
        Phase 9's SSE work, and pretending to stream by chopping a finished answer into fake deltas
        would be worse than saying it arrives at once. An async generator, as the port is: the
        first version returned a coroutine around one, and `async for` raised on it."""
        response = await self.complete(request)
        yield ModelChunk(
            text=response.text,
            tool_calls=response.tool_calls,
            usage=response.usage,
            done=True,
            reasoning=response.reasoning,
        )


class RemoteComponents(ComponentPort):
    """The registry lives on the host; the runtime asks what is there and asks it to act.

    On the thread door (ENH-030) the port is *one connection's*: `session` is the transport's
    own id for it (the same one `admin/sessions` shows — one connection, one name, D77), and
    when the connection is gone the port says so by name — its catalogue raises (the registry
    lists it as unreachable, so the tools vanish rather than linger) and an act in flight ends
    `Failed` naming the host, never a hang and never a silent nothing (P44-2).

    **The registration is not rewritten.** A host may sign what it registers (D27), and the
    signature covers provenance; a port that stamped `registered_by` would have every signed
    registration refused as tampered. What this port adds about itself it *declares* — `source`,
    which the registry reads beside the registration — it never edits the host's object.
    """

    source = "host"
    """How a tool of this port presents in the offer: the other side of the wire's own."""

    def __init__(self, peer: Peer, holder: Any = None, *, session: str = "") -> None:
        self._peer = peer
        self._holder = holder
        self.session = session
        self.problem: str | None = None
        """Why this port has no catalogue, when it has none: the host is gone."""

    def _live(self) -> Any:
        """The run this invoke is inside.

        Captured **here** and nowhere else, because here is the only place it exists: `invoke` is
        called from within the step, in the run's own task, where the contextvar is set. The first
        version read it from the loop consuming the event stream — a different task, where it is
        always `None`, which is why nothing a component proposed ever reached the sink.
        """
        from shadow_hdk.runtime import current_run

        context = current_run()
        if context is not None and self._holder is not None:
            self._holder.live = context
        return context

    @staticmethod
    def _gone(exc: BaseException) -> bool:
        """The other end went away — the wire's typed code, never its wording."""
        return isinstance(exc, RemoteError) and exc.code == GONE

    def _who(self) -> str:
        return f"host {self.session!r}" if self.session else "the host"

    async def registrations(self) -> Sequence[Registration]:
        try:
            listed = await self._peer.call(REGISTRATIONS, {})
        except Exception as exc:
            if self._gone(exc):
                self.problem = f"{self._who()} that offered these tools is gone: {exc}"
                raise RuntimeError(self.problem) from exc
            raise
        self.problem = None
        registrations = [load(json.dumps(entry), Registration) for entry in listed]
        # The remote host performs the invocation after this runtime asks it to. Until authority,
        # authorization and journal ports cross that boundary, an irreversible remote operation
        # is evidence we observed, not an act this runtime controlled (D99-D104).
        return [_observed_if_remote_effect(registration) for registration in registrations]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        # **One guard here, and only for a host that is gone.** `step.py` already catches every
        # exception out of a component port and observes it as `Failed`, so a general catch could
        # not change any outcome — a mutation deleting one left every test green. A gone host is
        # different: what the record says matters, and *"RemoteError: the other end closed"*
        # names nothing a reader can act on, where *"the host 'p-1' that offered 'greet' is gone"*
        # does (P44-2). Every other failure keeps flowing to the one guard in `step.py`.
        try:
            return await self._invoke(registration, inputs)
        except Exception as exc:
            if self._gone(exc):
                from shadow_hdk.kernel.observations import Failed

                return Failed(f"{self._who()} that offered {registration!r} is gone: {exc}")
            raise

    async def _invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        answered = await self._peer.call(
            INVOKE,
            {
                "registration": registration,
                "inputs": inputs,
                "run_id": _run_id_of(self._live()),
                # The **step**, not the registration: a thought the component puts on the record
                # has to fold under the step that was thinking, and the registration id is the
                # tool's name rather than the step's (Phase 21, found by the projection).
                "step": _step_of(self._live()),
            },
        )
        observation: Observation = load(json.dumps(answered), Observation)
        return observation


class RemoteSink(SinkPort):
    """A proposal made inside the runtime, offered to the host's record."""

    def __init__(self, peer: Peer) -> None:
        self._peer = peer

    async def propose(self, proposal: Proposal) -> None:
        await self._peer.call(PROPOSE, {"proposal": _as_json(proposal, Proposal)})


def _observed_if_remote_effect(registration: Registration) -> Registration:
    if registration.component.effects.reversible:
        return registration
    return replace(
        registration,
        component=replace(
            registration.component,
            provenance=replace(registration.component.provenance, posture="observed"),
        ),
    )


__all__ = ["RemoteComponents", "RemoteGovernance", "RemoteModel", "RemoteSink"]
