"""A provider that speaks without a CLI (D91): what a product's tests open a `Conversation` or
a `Thread` on, so a test of the product's governance, its verbs or its record spends nothing.

    agent = ScriptedAgent([([("write_file", {"path": "a.txt"})], "wrote it"), ([], "done")])
    thread = await Thread.open(agent=agent, ports=..., store=..., root=..., lease=...)
    agent.reach = thread.registry.call   # the offer's door, the way a CLI reaches it over MCP

Each turn calls the tools it was scripted to, through `reach`, then says its line; every prompt
it was handed and every answer a tool gave it are kept, so a test reads what the agent was told
(a folded note, D80) and what it heard back.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import Any, cast

from pydantic import JsonValue

from shadow_hdk.kernel import Turn
from shadow_hdk.kernel.ports import AgentSession, ToolSource, TurnChunk
from shadow_hdk.kernel.usage import Usage

Calls = list[tuple[str, Mapping[str, JsonValue]]]
Reach = Callable[[str, Mapping[str, JsonValue]], Awaitable[Any]]


class ScriptedAgent:
    """An `AgentPort` double. `turns` is what each turn does: the tool calls it makes, in order,
    and the line it says; `usage`, when given, is what every turn reports."""

    def __init__(self, turns: list[tuple[Calls, str]], *, usage: Usage | None = None) -> None:
        self.turns = list(turns)
        self.usage = usage
        self.reach: Reach | None = None
        self.prompts: list[str] = []
        self.answers: list[Any] = []
        self.opened = 0
        self.closed = 0
        self.behaviours: list[Any] = []
        self.resumed: list[str | None] = []
        self.session_id = "scripted-session"

    async def open(
        self,
        *,
        tools: tuple[ToolSource, ...] = (),
        workspace: str | None = None,
        behaviour: Any = None,
        resume: str | None = None,
    ) -> AgentSession:
        self.opened += 1
        self.behaviours.append(behaviour)
        self.resumed.append(resume)
        return cast(AgentSession, _Session(self))


class _Session:
    def __init__(self, agent: ScriptedAgent) -> None:
        self.agent = agent
        self.session_id = agent.session_id

    async def turn(self, prompt: str) -> Turn:
        self.agent.prompts.append(prompt)
        if not self.agent.turns:
            raise AssertionError("the scripted agent ran out of turns")
        calls, line = self.agent.turns.pop(0)
        if self.agent.reach is None and calls:
            raise AssertionError(
                "set `agent.reach = thread.registry.call` before a turn that calls"
            )
        for name, arguments in calls:
            assert self.agent.reach is not None
            self.agent.answers.append(await self.agent.reach(name, arguments))
        return Turn(text=line, usage=self.agent.usage)

    async def steer(self, text: str) -> bool:
        return False

    async def interrupt(self) -> bool:
        return True

    async def close(self) -> None:
        self.agent.closed += 1

    async def stream(self, prompt: str) -> AsyncIterator[TurnChunk]:
        """One piece: the scripted line arrives whole, as the port's default has it."""
        done = await self.turn(prompt)
        yield TurnChunk(text=done.text, usage=done.usage, done=True)


__all__ = ["ScriptedAgent"]
