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

from shadow_hdk.adapters.agent import (
    AgentComponent,
    Pattern,
    SkillComponents,
    SkillRegistry,
    SkillSource,
    shipped_skills,
)

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
        "If a skill fits the work, use it. If you work out a procedure worth repeating, mint it. "
        "Say what you found by calling `propose` with kind 'finding', then call `done`."
    ),
    max_turns=10,
)


@dataclass(frozen=True)
class Brain:
    model: ModelPort | None
    components: tuple[ComponentPort, ...]
    plan: Composition
    called: str
    reaches: bool = False
    skills: SkillRegistry | None = None
    """The registry this run offers — shipped, the host's kept ones, and what it mints — as a
    component (`SkillComponents`), so choosing and minting are steps on the record and reach a
    CLI by subscription through the registry socket the same as the in-process worker."""
    """Whether the reasoning itself is a network reach the policy must allow. A CLI by
    subscription talks to its own service and declares so on its step; a model port is not a
    component and is not judged as one, so a brain by key says nothing here."""


def _says(*calls: ToolCall, reasoning: str = "", cents: int = 1) -> ModelResponse:
    return ModelResponse(
        text="", tool_calls=calls, usage=Usage(100, 20, cents), reasoning=reasoning
    )


def _call(tool: str, cid: str, **arguments: Any) -> ToolCall:
    return ToolCall(id=cid, name=tool, arguments=dict(arguments))


def a_registry(*kept: SkillSource) -> SkillRegistry:
    """Shipped first, the host's kept skills after (they shadow), minted last (the registry's
    own). Fresh per brain, so what one run mints is scoped to it unless the host keeps it."""
    return SkillRegistry((shipped_skills(), *kept))


def _worker(brief: str, *, skills: SkillRegistry) -> tuple[tuple[ComponentPort, ...], Composition]:
    worker = AgentComponent(
        pattern=WORKER,
        effects=EffectProfile(
            reads=ScopeSet(everything=True), writes=ScopeSet.of("workspace"), costs=True
        ),
        name="worker",
        at=AT,
    )
    plan = Composition((Invoke("worker", "worker", (Binding("brief", value=brief),)),))
    return (worker, SkillComponents(skills, minting=True, at=AT)), plan


def scripted(brief: str, *, kept: SkillSource | None = None) -> Brain:
    """The model reads a script: choose a shipped skill, look, write one file, mint a procedure,
    propose, stop.

    What the script shows that a live model would too — a skill chosen by its line and loaded on
    choice, reasoning on the stream before each act, a write judged by the host's policy, a
    minted skill proposed for keeping, a proposal reaching the host's ledger."""
    script = [
        _says(
            _call("use_skill", "s0", name="look-before-you-change"),
            reasoning="I will change something, so I should take the procedure for that first.",
        ),
        _says(
            _call("list_dir", "s1", path="."),
            reasoning="First I should see what is already in the workspace.",
        ),
        _says(
            _call("write_file", "s2", path="NOTES.md", content=f"# Notes\n\n{brief}\n"),
            reasoning="Nothing there yet; I will write the brief down as notes.",
        ),
        _says(
            _call(
                "mint_skill",
                "s3",
                name="notes-first",
                description="Start any piece of work by writing the brief into NOTES.md.",
                prompt="List the workspace, then write the brief into NOTES.md before anything.",
                needs=["list_dir", "write_file"],
            ),
            reasoning="That is a procedure worth keeping; I will write it down.",
        ),
        _says(_call("propose", "s4", kind="finding", payload={"wrote": "NOTES.md"})),
        _says(_call("done", "s5", summary="Wrote NOTES.md with the brief.")),
    ]
    registry = a_registry(*([kept] if kept is not None else []))
    components, plan = _worker(brief, skills=registry)
    return Brain(
        model=ScriptedModel(script),
        components=components,
        plan=plan,
        called="scripted",
        skills=registry,
    )


def by_key(brief: str, *, kept: SkillSource | None = None) -> Brain:
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
    registry = a_registry(*([kept] if kept is not None else []))
    components, plan = _worker(brief, skills=registry)
    return Brain(model=model, components=components, plan=plan, called="by key", skills=registry)


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


async def by_subscription(
    brief: str, *, workspace: Path, want: str | None = None, kept: SkillSource | None = None
) -> Brain:
    """The CLI on this machine, one turn, its tools ours — the skill registry among them, so a
    subscription provider chooses and mints through the same socket its file tools go through.
    Everything it does lands on the run."""
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
    registry = a_registry(*([kept] if kept is not None else []))
    return Brain(
        model=None,
        components=(
            InMemoryComponents([(RESIDENT, resident)]),
            SkillComponents(registry, minting=True, at=AT),
        ),
        plan=plan,
        called=f"by subscription ({available.provider.called})",
        reaches=True,
        skills=registry,
    )


__all__ = ["Brain", "NoBrain", "RESIDENT", "WORKER", "by_key", "by_subscription", "scripted"]
