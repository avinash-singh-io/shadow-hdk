"""What a held child waits on.

D16 makes a held child a **parked run**, and a run parks where a step says it is waiting. So a child
that is to be kept between messages needs one step that waits — and this is it: a component whose
whole behaviour is to answer `Pending`, so an `Await` on it parks the run until somebody sends
something.

It is shipped rather than left to each host because it is a **convention, not a capability**. Every
holder would otherwise write the same three lines and name them differently, and a held child's
shape would be private to whoever built it. Its effect profile is empty and truthfully so: waiting
reads nothing, writes nothing and reaches nowhere.

    child = Composition((Invoke("brief", ...), Await("inbox", Mailbox.NAME)))
    handle, _ = await context.children.spawn(child, Ceiling(10, 600, 1000))
    await context.children.send(handle, {"say": "what did you find?"})
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Failed, Observation, Pending
from shadow_hdk.kernel.ports import ComponentPort


class Mailbox(ComponentPort):
    """One component: wait here until somebody sends something."""

    NAME = "mailbox"

    def __init__(self, *, name: RegistrationId = NAME, registered_by: str = "host") -> None:
        self.name = name
        self._registration = Registration(
            id=name,
            component=Component(
                interface=Interface(
                    name=name,
                    description="Wait here until somebody sends a message.",
                    input_schema={"type": "object", "properties": {}},
                    output_schema={},
                ),
                # Waiting reads nothing, writes nothing, reaches nowhere. The default profile says
                # exactly that, and saying it by default rather than by argument is the point.
                effects=EffectProfile(),
                provenance=Provenance(registered_by=registered_by, adapter="mailbox", at=""),
                labels=frozenset({"state"}),
            ),
        )

    async def registrations(self) -> Sequence[Registration]:
        return [self._registration]

    async def invoke(self, registration: RegistrationId, _inputs: JsonValue) -> Observation:
        if registration != self.name:
            return Failed(f"no component registered as {registration!r}")
        # The handle names the run's own waiting place. Whoever holds this child sends to the
        # child, not to the handle, so this is for the record rather than for addressing.
        return Pending(f"{self.name}:waiting")


__all__ = ["Mailbox"]
