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
from collections.abc import Sequence
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Observation, Proposal
from shadow_hdk.kernel.ports import (
    Context,
    Judgement,
    ModelRequest,
    ModelResponse,
)
from shadow_hdk.wire.peer import Peer
from shadow_hdk.wire.protocol import COMPLETE, INVOKE, JUDGE, PROPOSE, REGISTRATIONS


def _run_id_of(context: Any) -> str:
    return str(context.run_id) if context is not None else ""


def _as_json(value: object, as_type: Any) -> JsonValue:
    parsed: JsonValue = json.loads(dump(value, as_type))
    return parsed


class RemoteGovernance:
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
        return load(json.dumps(answered), Judgement)


class RemoteModel:
    """The runtime asks; the host's model answers."""

    def __init__(self, peer: Peer) -> None:
        self._peer = peer

    async def complete(self, request: ModelRequest) -> ModelResponse:
        answered = await self._peer.call(COMPLETE, {"request": _as_json(request, ModelRequest)})
        return load(json.dumps(answered), ModelResponse)

    async def stream(self, request: ModelRequest) -> Any:
        """The port's own default — one chunk from `complete` (D14). Streaming over the wire is
        Phase 9's SSE work, and pretending to stream by chopping a finished answer into fake deltas
        would be worse than saying it arrives at once."""
        from shadow_hdk.kernel.ports import ModelChunk

        response = await self.complete(request)

        async def one() -> Any:
            yield ModelChunk(
                text=response.text,
                tool_calls=response.tool_calls,
                usage=response.usage,
                done=True,
            )

        return one()


class RemoteComponents:
    """The registry lives on the host; the runtime asks what is there and asks it to act."""

    def __init__(self, peer: Peer, holder: Any = None) -> None:
        self._peer = peer
        self._holder = holder

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

    async def registrations(self) -> Sequence[Registration]:
        listed = await self._peer.call(REGISTRATIONS, {})
        return [load(json.dumps(entry), Registration) for entry in listed]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        # **No guard here, deliberately.** The obvious thing is to catch a `RemoteError` and
        # return `Failed` — D7, a component is untrusted and its raising is data. But `step.py`
        # already catches every exception out of a component port and observes it as `Failed`, so a
        # second catch
        # cannot change any outcome: a mutation deleting this one left every test green, which is
        # what redundant handling looks like from outside. A guard that cannot change an outcome
        # claims something is handled where nothing is, so the only guard is the one in `step.py`.
        answered = await self._peer.call(
            INVOKE,
            {
                "registration": registration,
                "inputs": inputs,
                "run_id": _run_id_of(self._live()),
            },
        )
        return load(json.dumps(answered), Observation)


class RemoteSink:
    """A proposal made inside the runtime, offered to the host's record."""

    def __init__(self, peer: Peer) -> None:
        self._peer = peer

    async def propose(self, proposal: Proposal) -> None:
        await self._peer.call(PROPOSE, {"proposal": _as_json(proposal, Proposal)})


__all__ = ["RemoteComponents", "RemoteGovernance", "RemoteModel", "RemoteSink"]
