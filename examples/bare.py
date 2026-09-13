"""The bare-harness demo — a composition, an MCP-shaped server, a model and a sub-agent.

This is the definition of *generic* (`09` §1): everything below runs with **zero lines of any
product's code**. If this file ever needs a product import, the decoupling was a claim.

What it demonstrates, in the order the events come out:

1. a **component arriving from outside** — tools described the way an MCP server describes them,
   with `readOnlyHint` and friends, turned into effect profiles by the kernel rather than trusted;
2. an **agent authoring a composition** and the runtime running it, governed step by step;
3. a **sub-agent** — a component with the `agent` label, whose run is carved from its parent's
   lease and whose events arrive in the parent's stream;
4. a **proposal** leaving through the sink, because the runtime never writes anything itself.

Phase 0 drives it with a scripted model and a stub server, so it costs nothing and cannot flake.
Phase 1 swaps in a real MCP server and Ollama and asserts the same shape — the point of the stub is
that the *swap* is a different `Ports`, not a different program.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from typing import TextIO

from pydantic import JsonValue

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import AllowAll, StdoutObserver, StdoutSink, SystemClock
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Component,
    Composition,
    EffectProfile,
    Event,
    Failed,
    Floor,
    Interface,
    Invoke,
    Lease,
    Observation,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.ports import ComponentPort, ModelResponse, ToolCall, Usage
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import ScriptedModel

# ---------------------------------------------------------------- a component from outside


class McpShapedServer(ComponentPort):
    """What an MCP server looks like from here: named tools carrying annotations, nothing else.

    The effect profile is **derived** from those annotations by the kernel and hardened where they
    say nothing — `contained` and `costs` stay at their worst until a deployment says otherwise. We
    never trust a component's self-description for a field that matters (`09` §2).
    """

    def __init__(self, name: str = "reference-server") -> None:
        self._name = name
        self._answers: dict[str, JsonValue] = {
            "lathe": {"asset": "LATHE-3", "mass_kg": 12, "line": 3},
            "lathe mass": {"mass_kg": 12, "measured": "2026-08-01"},
        }

    async def registrations(self) -> Sequence[Registration]:
        return [
            Registration(
                id="look_up",
                component=Component(
                    interface=Interface(
                        name="look_up",
                        description="Look a topic up in the reference server.",
                        input_schema={
                            "type": "object",
                            "properties": {"topic": {"type": "string"}},
                            "required": ["topic"],
                        },
                    ),
                    effects=EffectProfile.from_mcp_annotations(
                        read_only_hint=True, open_world_hint=False
                    ),
                    provenance=Provenance(
                        registered_by=self._name, adapter="mcp", at="2026-09-10T00:00:00+00:00"
                    ),
                ),
            )
        ]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        if registration != "look_up":
            return Failed(f"no component registered as {registration!r}")
        topic = inputs.get("topic") if isinstance(inputs, dict) else None
        return Completed(self._answers.get(str(topic), {"unknown": topic}))


# ---------------------------------------------------------------- what the model says

RESEARCHER = Pattern(
    name="researcher",
    system="Find what is asked and say it plainly. Use the reference server.",
    tool_names=frozenset({"look_up"}),
    max_turns=4,
)

LEAD = Pattern(
    name="lead",
    system="Answer the brief. Delegate research. Propose what is worth keeping.",
    tool_names=frozenset({"look_up", "researcher"}),
    max_turns=6,
)


def _call(name: str, cid: str, **arguments: JsonValue) -> ToolCall:
    return ToolCall(id=cid, name=name, arguments=dict(arguments))


def _says(*calls: ToolCall, text: str = "", cents: int = 1) -> ModelResponse:
    return ModelResponse(text=text, tool_calls=calls, usage=Usage(120, 30, cents))


SCRIPT = [
    # the lead looks the asset up …
    _says(_call("look_up", "t1", topic="lathe")),
    # … then hands the detail to a sub-agent
    _says(_call("researcher", "t2", brief="what is the mass of the lathe?")),
    #   the sub-agent's own two turns
    _says(_call("look_up", "r1", topic="lathe mass")),
    _says(_call("done", "r2", summary="12 kg, measured 2026-08-01")),
    # the lead keeps what came back …
    _says(_call("propose", "t3", kind="claim", payload={"asset": "LATHE-3", "mass_kg": 12})),
    # … and stops
    _says(_call("done", "t4", summary="LATHE-3 on line 3 weighs 12 kg, measured 2026-08-01")),
]


# ---------------------------------------------------------------- the run


def bare_ports(out: TextIO | None = None) -> Ports:
    """Everything wired, and not one line of it belongs to a product."""
    stream = out if out is not None else sys.stdout
    researcher = AgentComponent(
        pattern=RESEARCHER,
        effects=EffectProfile(costs=True),
        name="researcher",
        description="Look something up and report it.",
        at="2026-09-10T00:00:00+00:00",
    )
    lead = AgentComponent(
        pattern=LEAD,
        effects=EffectProfile(costs=True),
        name="lead",
        at="2026-09-10T00:00:00+00:00",
    )
    return Ports(
        model=ScriptedModel(SCRIPT),
        components=(McpShapedServer(), researcher, lead),
        governance=AllowAll(),
        sink=StdoutSink(stream),
        clock=SystemClock(),
        observer=StdoutObserver(stream),
    )


BRIEF = "How heavy is the lathe on line 3, and when was that measured?"


async def bare_harness(out: TextIO | None = None) -> list[Event]:
    composition = Composition((Invoke("lead", "lead", (Binding("brief", value=BRIEF),)),))
    options = RunOptions(lease=Lease(Ceiling(40, 600, 500), Floor(0)))
    return [event async for event in run(composition, bare_ports(out), options=options)]


async def _main() -> None:
    await bare_harness()


if __name__ == "__main__":
    asyncio.run(_main())
