"""The same harness, with nothing stubbed.

`bare.py` proves the *shape* with a scripted model and a hand-written server. This proves the
**seams**: a real model over a real HTTP wire, a real MCP server in a real subprocess, and a real
policy that refuses things — still with zero lines of any product's code.

    export INTENT_HF_TOKEN=…            # or any provider LangChain integrates
    uv run python examples/real.py

What it shows, and what `bare.py` cannot:

* an agent choosing its own tool calls, rather than reading a script;
* tools whose **effect profiles were derived from what a server declared** — and one, `mystery`,
  that declared nothing and is therefore treated as the worst case;
* a **mode** that lets the agent look things up and refuses to let it wipe or reach outside, so the
  refusal is a real policy decision about real effects rather than a demonstration.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TextIO

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import StdoutObserver, StdoutSink, SystemClock
from shadow_hdk.adapters.langchain import LangChainModel
from shadow_hdk.adapters.mcp import McpComponents, StdioServerParameters
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.runtime import Ports, RunOptions, run

EVERYTHING = ScopeSet(everything=True)

#: Looking is fine; changing the world is not. `contained=False` permits uncontained
#: components, which is the truthful setting for a laptop with no sandbox.
LOOKING = Mode(
    "looking",
    ceiling=EffectProfile(reads=EVERYTHING, contained=False, costs=True),
)

ANALYST = Pattern(
    name="analyst",
    system=(
        "Answer the question using the tools you have. Look things up rather than guessing. "
        "When you have the answer, call `propose` with what you found, then call `done`."
    ),
    max_turns=6,
)

BRIEF = "How heavy is the lathe on line 3, and when was that measured? Look it up."

SERVER = StdioServerParameters(command=sys.executable, args=["tests/adapters/mcp/server.py"])


def a_model() -> LangChainModel:
    """Any provider LangChain integrates. The default is HuggingFace Inference Providers, which is
    OpenAI-compatible — the same code path as OpenAI, Together, Groq, vLLM and most self-hosted."""
    token = os.environ.get("INTENT_HF_TOKEN")
    if not token:
        raise SystemExit("set INTENT_HF_TOKEN (or edit a_model to point at your own provider)")
    return LangChainModel(
        os.environ.get("SHADOW_HDK_LIVE_MODEL_ID", "deepseek-ai/DeepSeek-V4-Flash:deepinfra"),
        model_provider="openai",
        base_url=os.environ.get("SHADOW_HDK_LIVE_BASE_URL", "https://router.huggingface.co/v1"),
        api_key=token,
        temperature=0,
    )


async def real_harness(out: TextIO | None = None) -> list[Event]:
    stream = out if out is not None else sys.stdout
    agent = AgentComponent(
        pattern=ANALYST,
        effects=EffectProfile(reads=EVERYTHING, contained=False, costs=True),
        name="analyst",
        at="2026-09-10T00:00:00+00:00",
    )
    async with McpComponents(
        SERVER, source="reference-server", at="2026-09-10T00:00:00+00:00"
    ) as tools:
        ports = Ports(
            model=a_model(),
            components=(tools, agent),
            governance=ModeGovernance({LOOKING.name: LOOKING}, default=LOOKING.name),
            sink=StdoutSink(stream),
            clock=SystemClock(),
            observer=StdoutObserver(stream),
        )
        composition = Composition((Invoke("analyst", "analyst", (Binding("brief", value=BRIEF),)),))
        options = RunOptions(lease=Lease(Ceiling(30, 300, None), Floor(0)))
        return [event async for event in run(composition, ports, options=options)]


if __name__ == "__main__":
    asyncio.run(real_harness())
