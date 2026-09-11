"""Where the reasoning comes from — the host's choice, and the run does not care.

Three brains, one run:

* `scripted()` — a model that says what it was told to say. The proof, and costs nothing.
* `by_key()` — any provider LangChain integrates, from a key in the environment (`ModelPort`).
* `by_subscription()` — whatever CLI is installed and signed in on this machine, driven through
  `AgentPort` with **this run's tools** offered back to it over the registry socket (D42, D52). No
  credential is read; detection reports and never installs (D41).

`Brain` is what the host gets back: what to put in `Ports.model` (or `None` — D39: a provider's
reasoning is its own) and which extra component, if any, holds the conversation.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.agent import AgentComponent, Pattern

from shadow_hdk.kernel import (
    Binding,
    Completed,
    Composition,
    EffectProfile,
    Invoke,
    Observation,
    ScopeSet,
)
from shadow_hdk.kernel.ports import ComponentPort, ModelPort, ModelResponse, ToolCall, Usage
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.testing import InMemoryComponents, ScriptedModel, make_registration

AT = "2026-09-11T00:00:00+00:00"

WORKER = Pattern(
    name="worker",
    system=(
        "Do what the brief asks using the tools you have, inside the workspace you were given. "
        "Say what you found by calling `propose` with kind 'finding', then call `done`."
    ),
    max_turns=8,
)


@dataclass(frozen=True)
class Brain:
    model: ModelPort | None
    components: tuple[ComponentPort, ...]
    plan: Composition
    called: str
    reaches: bool = False
    """Whether the reasoning itself is a network reach the policy must allow. A CLI by
    subscription talks to its own service and declares so on its step; a model port is not a
    component and is not judged as one, so a brain by key says nothing here."""


def _says(*calls: ToolCall, reasoning: str = "", cents: int = 1) -> ModelResponse:
    return ModelResponse(
        text="", tool_calls=calls, usage=Usage(100, 20, cents), reasoning=reasoning
    )


def _call(name: str, cid: str, **arguments: Any) -> ToolCall:
    return ToolCall(id=cid, name=name, arguments=dict(arguments))


def _worker(brief: str) -> tuple[tuple[ComponentPort, ...], Composition]:
    worker = AgentComponent(
        pattern=WORKER,
        effects=EffectProfile(
            reads=ScopeSet(everything=True), writes=ScopeSet.of("workspace"), costs=True
        ),
        name="worker",
        at=AT,
    )
    plan = Composition((Invoke("worker", "worker", (Binding("brief", value=brief),)),))
    return (worker,), plan


def scripted(brief: str) -> Brain:
    """The model reads a script: look at the workspace, think, write one file, propose, stop.

    What the script shows that a live model would too — reasoning on the stream before each act,
    a write judged by the host's policy, a proposal reaching the host's ledger."""
    script = [
        _says(
            _call("list_dir", "s1", path="."),
            reasoning="First I should see what is already in the workspace.",
        ),
        _says(
            _call("write_file", "s2", path="NOTES.md", content=f"# Notes\n\n{brief}\n"),
            reasoning="Nothing there yet; I will write the brief down as notes.",
        ),
        _says(_call("propose", "s3", kind="finding", payload={"wrote": "NOTES.md"})),
        _says(_call("done", "s4", summary="Wrote NOTES.md with the brief.")),
    ]
    components, plan = _worker(brief)
    return Brain(model=ScriptedModel(script), components=components, plan=plan, called="scripted")


def by_key(brief: str) -> Brain:
    """Any provider LangChain integrates. HuggingFace's router by default — OpenAI-compatible, the
    same path as OpenAI, Together, Groq, vLLM and most self-hosted servers."""
    from shadow_hdk.adapters.langchain import LangChainModel

    token = os.environ.get("INTENT_HF_TOKEN")
    if not token:
        raise NoBrain("by_key needs INTENT_HF_TOKEN in the environment (or edit by_key)")
    model = LangChainModel(
        os.environ.get("SHADOW_HDK_LIVE_MODEL_ID", "deepseek-ai/DeepSeek-V4-Flash:deepinfra"),
        model_provider="openai",
        base_url=os.environ.get("SHADOW_HDK_LIVE_BASE_URL", "https://router.huggingface.co/v1"),
        api_key=token,
        temperature=0,
    )
    components, plan = _worker(brief)
    return Brain(model=model, components=components, plan=plan, called="by key")


class NoBrain(RuntimeError):
    """Nothing here can do the reasoning, and this says why."""


RESIDENT = make_registration(
    "resident",
    effects=EffectProfile(
        reads=ScopeSet(everything=True),
        writes=ScopeSet.of("workspace"),
        reaches=True,  # the CLI talks to its own service
        reversible=False,
        costs=True,
    ),
    description="One turn with the provider signed in on this machine, using this run's tools.",
)

RELAY = "shadow-hdk-registry"


async def by_subscription(brief: str, *, workspace: Path, want: str | None = None) -> Brain:
    """The CLI on this machine, one turn, its tools ours. Everything it does lands on the run."""
    from shadow_hdk.adapters.recording import (
        PORT_VARIABLE,
        TOKEN_VARIABLE,
        RecordingServer,
        serve_over_socket,
    )

    from shadow_hdk.kernel.ports import ToolSource
    from shadow_hdk.providers import detect, environment_for, open_with, search_dirs, shipped

    library = shipped()
    wanted = [library[want]] if want else list(library.values())
    ready = [
        it for it in await detect(wanted) if it.status == "ready" and it.provider.injects_tools
    ]
    if not ready:
        rows = [f"  {it.provider.called:12} {it.status}" for it in await detect(wanted)]
        raise NoBrain("no provider on this machine is ready:\n" + "\n".join(rows))
    available = ready[0]
    binary = available.binary
    assert binary is not None, "a provider reported ready has a binary"

    async def resident(inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        holder = RecordingServer(context, withhold={"resident"})
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            opened = await open_with(
                available.provider,
                binary=binary,
                env=environment_for(available.provider, base={}, search=search_dirs()),
                workspace=workspace,
            )
            relay = ToolSource(
                kind="mcp",
                address=shutil.which(RELAY) or RELAY,
                env=((PORT_VARIABLE, str(port)), (TOKEN_VARIABLE, token)),
            )
            session = await opened.open(tools=(relay,), workspace=str(workspace))
            try:
                asked = inputs.get("brief", "") if isinstance(inputs, dict) else str(inputs)
                turn = await session.turn(str(asked))
            finally:
                await session.close()
        return Completed({"text": turn.text, "stop_reason": turn.stop_reason})

    plan = Composition((Invoke("resident", "resident", (Binding("brief", value=brief),)),))
    return Brain(
        model=None,
        components=(InMemoryComponents([(RESIDENT, resident)]),),
        plan=plan,
        called=f"by subscription ({available.provider.called})",
        reaches=True,
    )


__all__ = ["Brain", "NoBrain", "RESIDENT", "WORKER", "by_key", "by_subscription", "scripted"]
