"""How a large catalogue is offered — D13's fourth mechanism.

*Above a threshold (a setting, default ~30) the model sees names and one-line descriptions and pulls
a schema on demand with `describe`.* Below it nothing changes, because a catalogue small enough to
read whole is cheaper read whole than fetched twice.

Two rules the thinning obeys, and both are about not lying to the model:

* **Thinning drops schemas, never components.** A model that cannot see a tool cannot ask about it,
  and a shorter list it cannot act on is worse than a long one it can.
* **A thinned entry says how to get the rest.** An input schema that is silently empty reads as
  *this takes no arguments*, which is a different and wrong statement.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from shadow_hdk.adapters.agent.pattern import DESCRIBE, Pattern

from shadow_hdk.kernel.components import Interface, Registration

HOW_TO_ASK = f"Call `{DESCRIBE}` with this name to see what it takes."


def thin(interfaces: Sequence[Interface], pattern: Pattern) -> tuple[Interface, ...]:
    """The catalogue as the model should see it, given how many components there are."""
    if len(interfaces) < pattern.catalogue_threshold:
        return tuple(interfaces)
    return tuple(
        Interface(
            name=interface.name,
            description=f"{interface.description or interface.name} {HOW_TO_ASK}".strip(),
            input_schema={},
            output_schema={},
        )
        for interface in interfaces
    )


def describe_for(name: str, visible: Iterable[Registration]) -> Interface | str:
    """The full interface for one component, or a sentence saying why not.

    Answers only from what was passed in, which is `visible()` — a describe that reached past it
    would be a way to read a registry a mode had closed.
    """
    for registration in visible:
        if registration.id == name or registration.component.interface.name == name:
            return registration.component.interface
    return f"no component called {name!r} is available to you"


__all__ = ["HOW_TO_ASK", "describe_for", "thin"]
