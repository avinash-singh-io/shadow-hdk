"""A Python function becomes a component — how a host registers its own operations.

This is the adapter behind *"plugging your record in"* (`specs/architecture/adapters.md`). Intent
Studio's record verbs are this: ordinary callables that declare `writes: {record}` and, inside,
hand a `Proposal` to the sink through `current_run()`. The runtime never learns what a claim is.

Three things it does, and each is a rule rather than a convenience:

* **The schema comes from the signature**, so the interface the model sees and the function that
  runs cannot drift apart.
* **Inputs are validated before the call**, and a bad shape is a `Failed` observation rather than a
  `TypeError` the agent cannot read.
* **Effects must be passed in.** There is no default: a function cannot be asked what it does to
  the world, and guessing is how a component gets a permission nobody granted it.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from typing import Any, get_type_hints

from pydantic import JsonValue, ValidationError, create_model

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort

AnyCallable = Callable[..., Any]
Validator = Callable[[JsonValue], dict[str, Any]]


def _model_for(fn: AnyCallable) -> Any:
    """A pydantic model of the function's parameters, used for both the schema and validation."""
    signature = inspect.signature(fn)
    hints = get_type_hints(fn)
    fields: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if name.startswith("_") or parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        annotation = hints.get(name, Any)
        default = ... if parameter.default is inspect.Parameter.empty else parameter.default
        fields[name] = (annotation, default)
    return create_model(f"{fn.__name__}_input", **fields)


def callable_component(
    fn: AnyCallable,
    *,
    effects: EffectProfile,
    name: str | None = None,
    description: str | None = None,
    labels: frozenset[str] = frozenset({"tool"}),
    registration_id: RegistrationId | None = None,
    registered_by: str = "host",
    at: str = "",
    licence: str | None = None,
    signed_by: str | None = None,
) -> tuple[Registration, AnyCallable, Any]:
    """Build a registration for `fn`. Returns it with the function and its input model."""
    model = _model_for(fn)
    interface = Interface(
        name=name or fn.__name__,
        description=description or (inspect.getdoc(fn) or "").split("\n\n")[0].strip(),
        input_schema=model.model_json_schema(),
        output_schema={},
    )
    registration = Registration(
        id=registration_id or interface.name,
        component=Component(
            interface=interface,
            effects=effects,
            provenance=Provenance(
                registered_by=registered_by,
                adapter="callable",
                at=at,
                signed_by=signed_by,
                licence=licence,
            ),
            labels=labels,
        ),
    )
    return registration, fn, model


class CallableComponents(ComponentPort):
    """Several callables behind one component port."""

    def __init__(self, *, registered_by: str = "host", at: str = "") -> None:
        self._registered_by = registered_by
        self._at = at
        self._entries: dict[RegistrationId, tuple[Registration, AnyCallable, Any]] = {}

    def add(self, fn: AnyCallable, *, effects: EffectProfile, **kw: Any) -> Registration:
        kw.setdefault("registered_by", self._registered_by)
        kw.setdefault("at", self._at)
        registration, function, model = callable_component(fn, effects=effects, **kw)
        self._entries[registration.id] = (registration, function, model)
        return registration

    async def registrations(self) -> Sequence[Registration]:
        return [registration for registration, _, _ in self._entries.values()]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        entry = self._entries.get(registration)
        if entry is None:
            return Failed(f"no component registered as {registration!r}")
        _, function, model = entry
        try:
            arguments = model(**(inputs if isinstance(inputs, dict) else {})).model_dump()
        except ValidationError as invalid:
            return Failed(
                f"inputs do not fit {registration!r}: {invalid.errors(include_url=False)}"
            )
        try:
            result = function(**arguments)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001 — a component is untrusted (D7)
            return Failed(f"{type(exc).__name__}: {exc}")
        # A callable that wants to refuse, ask or report pending says so by returning one.
        if isinstance(result, Completed | Failed) or hasattr(result, "kind"):
            observation: Observation = result
            return observation
        return Completed(result)


__all__ = ["CallableComponents", "callable_component"]
