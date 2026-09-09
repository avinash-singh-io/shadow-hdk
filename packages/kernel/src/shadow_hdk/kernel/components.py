"""A component is anything with three things (09 §4): an interface, an effect profile, provenance.

"Tool", "agent", "feedback", "program", "state" are labels carried for discovery and display. The
runtime never branches on them, and a sixth label costs nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import JsonValue

from shadow_hdk.kernel.effects import EffectProfile

RegistrationId = str


@dataclass(frozen=True)
class Interface:
    """What the agent can invoke: a name, a description, typed input, typed output."""

    name: str
    description: str
    input_schema: dict[str, JsonValue] = field(default_factory=dict)
    output_schema: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class Provenance:
    """Who registered it, what adapter it came through, who signed it, when.

    ``at`` is whatever the registering side's clock said, as text — the kernel has no clock.
    ``licence`` is recorded here because an open-source component is whatever it is, behind an
    adapter, with its licence in provenance (09 §4).
    """

    registered_by: str
    adapter: str
    at: str
    signed_by: str | None = None
    licence: str | None = None


@dataclass(frozen=True)
class Component:
    interface: Interface
    effects: EffectProfile
    provenance: Provenance
    labels: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Registration:
    """``register(Component) -> RegistrationId``, as a value. The registry is a set of these."""

    id: RegistrationId
    component: Component
