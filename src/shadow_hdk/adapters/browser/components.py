"""The optional browser vocabulary, declared as ordinary governed components."""

from __future__ import annotations

from typing import Protocol

from pydantic import JsonValue

from shadow_hdk.adapters.browser.arguments import READ_ACTIONS, WRITE_ACTIONS, parse, schema
from shadow_hdk.kernel import (
    Component,
    EffectProfile,
    Interface,
    Observation,
    Provenance,
    Registration,
    ScopeSet,
)
from shadow_hdk.kernel.observations import Refused
from shadow_hdk.runtime import current_run


class BrowserEngine(Protocol):
    async def execute(self, action: str, inputs: JsonValue, resource_scope: str) -> Observation: ...

    async def release_run(self, resource_scope: str) -> None: ...


class BrowserComponents:
    def __init__(self, *, engine: BrowserEngine | None = None) -> None:
        if engine is None:
            from shadow_hdk.adapters.browser.engine import PlaywrightEngine

            engine = PlaywrightEngine()
        self._engine = engine
        self._licence = getattr(engine, "licence", None)

    async def registrations(self) -> list[Registration]:
        return [
            Registration(
                id=f"browser_{action}",
                component=Component(
                    interface=Interface(
                        name=f"browser_{action}",
                        description=(
                            f"Browser {action.replace('_', ' ')} "
                            "in this session's isolated profile."
                        ),
                        input_schema=schema(action),
                        output_schema={"type": "object"},
                    ),
                    effects=EffectProfile(
                        reads=ScopeSet.of("browser"),
                        writes=ScopeSet.of("browser", "network")
                        if action in WRITE_ACTIONS
                        else ScopeSet(),
                        reaches=action in WRITE_ACTIONS,
                        reversible=action not in WRITE_ACTIONS,
                    ),
                    provenance=Provenance("host", "browser", "", licence=self._licence),
                ),
            )
            for action in (*READ_ACTIONS, *WRITE_ACTIONS)
        ]

    async def invoke(self, registration: str, inputs: JsonValue) -> Observation:
        if registration not in {f"browser_{action}" for action in (*READ_ACTIONS, *WRITE_ACTIONS)}:
            return Refused(f"unknown browser action: {registration}")
        action = registration.removeprefix("browser_")
        try:
            parse(action, inputs)
        except ValueError as error:
            return Refused(f"invalid browser inputs: {error}")
        context = current_run()
        if context is None:
            return Refused("browser actions require a governed execution scope")
        return await self._engine.execute(action, inputs, context.resource_scope)

    async def release_run(self, resource_scope: str) -> None:
        await self._engine.release_run(resource_scope)
