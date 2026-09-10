"""A minimal, conformant ACP agent — the other end of the pipe, so J1 can be measured.

**What this proves and what it does not.** It is our own agent, so its *behaviour* is our choice and
measuring that would be circular. What is not circular is everything between the two processes: that
a denial travels, that the agent can tell a denial from a rejection from an approval, that a turn's
end is observable by the client with a stop reason, and that usage arrives — both mid-turn and at
the end. That is the client half of the ACP bridge (Phase 4) validated before it is written.

What Codex and Claude Code do when refused is a different question, and it stays open.

Behaviour is chosen by the prompt text, so one agent covers every shape:

* `tool`     — ask permission, then do as told and end
* `refuse`   — end the turn with `stop_reason="refusal"` without asking
* `no-usage` — ask permission, end without reporting usage at all
* `loop`     — ask permission; if denied, ask again, forever. The shape J1 fears
* `write`    — call the client back to write a file, so the bridge's own governance is exercised
* `read`     — call the client back to read one
* `terminal` — ask the client for a terminal
"""

from __future__ import annotations

import asyncio
from typing import Any

import acp
from acp import schema


class SpikeAgent(acp.Agent):
    def __init__(self, client: acp.Client) -> None:
        self._client = client
        self._sessions = 0

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: schema.ClientCapabilities | None = None,
        client_info: schema.Implementation | None = None,
        **kwargs: Any,
    ) -> schema.InitializeResponse:
        return schema.InitializeResponse(
            protocol_version=protocol_version,
            agent_capabilities=schema.AgentCapabilities(),
            agent_info=schema.Implementation(name="shadow-hdk-spike-agent", version="0.0.1"),
        )

    async def new_session(
        self,
        cwd: str,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        **kwargs: Any,
    ) -> schema.NewSessionResponse:
        self._sessions += 1
        return schema.NewSessionResponse(session_id=f"spike-{self._sessions}")

    async def prompt(
        self, session_id: str, prompt: list[Any], **kwargs: Any
    ) -> schema.PromptResponse:
        asked = _text_of(prompt)

        if "refuse" in asked:
            return schema.PromptResponse(stop_reason="refusal", usage=_usage())

        # The client half of ACP is a governance surface, and these are the doors. The agent calls
        # *back* into the client, which is where our own policy meets somebody else's agent.
        if "write" in asked:
            return await self._through_the_client(
                session_id,
                self._client.write_text_file(session_id, "from-the-child.md", "# hello\n"),
            )
        if "read" in asked:
            return await self._through_the_client(
                session_id, self._client.read_text_file(session_id, "from-the-child.md")
            )
        if "terminal" in asked:
            return await self._through_the_client(
                session_id, self._client.create_terminal(session_id, "echo hi")
            )

        outcome = await self._ask_to_run(session_id, "call-1")

        if "loop" in asked:
            # The failure J1 is really about: an agent that treats a refusal as a retry. It is
            # here so the *test* can prove a timeout catches it — an assertion cannot catch a hang.
            while _denied(outcome):
                outcome = await self._ask_to_run(session_id, "call-again")
            return schema.PromptResponse(stop_reason="end_turn", usage=_usage())

        if _denied(outcome):
            # A conformant agent stops. `cancelled` is the stop reason ACP gives for "the client
            # would not let me", and it is distinct from `refusal`, which means the agent declined.
            return schema.PromptResponse(stop_reason="cancelled", usage=_usage())

        await self._client.session_update(
            session_id=session_id,
            update=schema.UsageUpdate(
                session_update="usage_update",
                used=1200,
                size=200_000,
                cost=schema.Cost(amount=0.004, currency="USD"),
            ),
        )
        return schema.PromptResponse(
            stop_reason="end_turn", usage=None if "no-usage" in asked else _usage()
        )

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        return None

    async def _through_the_client(self, session_id: str, call: Any) -> schema.PromptResponse:
        """Do something that needs the client's permission, and say plainly how it went.

        A refusal arrives as a JSON-RPC error, which is what a governed no looks like from this end.
        The agent reports it as a completed turn carrying the reason — an agent that crashed on
        being told no would be a badly behaved agent, and the bridge should not need one.
        """
        await self._client.session_update(
            session_id=session_id,
            update=schema.AgentMessageChunk(
                session_update="agent_message_chunk",
                content=schema.TextContentBlock(type="text", text="trying it"),
            ),
        )
        try:
            await call
        except Exception as refused:  # noqa: BLE001 — a refusal is a normal answer here
            await self._client.session_update(
                session_id=session_id,
                update=schema.AgentMessageChunk(
                    session_update="agent_message_chunk",
                    content=schema.TextContentBlock(type="text", text=f" — refused: {refused}"),
                ),
            )
            return schema.PromptResponse(stop_reason="refusal", usage=_usage())
        await self._client.session_update(
            session_id=session_id,
            update=schema.AgentMessageChunk(
                session_update="agent_message_chunk",
                content=schema.TextContentBlock(type="text", text=" — done"),
            ),
        )
        return schema.PromptResponse(stop_reason="end_turn", usage=_usage())

    async def _ask_to_run(self, session_id: str, call_id: str) -> Any:
        answer = await self._client.request_permission(
            session_id=session_id,
            tool_call=schema.ToolCallUpdate(tool_call_id=call_id, title="rm -rf /tmp/spike"),
            options=[
                schema.PermissionOption(option_id="yes", name="Allow once", kind="allow_once"),
                schema.PermissionOption(option_id="no", name="Reject once", kind="reject_once"),
            ],
        )
        return answer.outcome


def _denied(outcome: Any) -> bool:
    """Two ways to be told no, and an agent has to understand both.

    `DeniedOutcome` is the client refusing to answer at all. `AllowedOutcome` carrying the option id
    of a `reject_*` option is the client *answering* — with a no. An agent that checks only the
    first treats a considered rejection as consent.
    """
    if getattr(outcome, "outcome", None) == "cancelled":
        return True
    return getattr(outcome, "option_id", None) in {"no", "never"}


def _usage() -> schema.Usage:
    return schema.Usage(total_tokens=1400, input_tokens=1200, output_tokens=200, thought_tokens=40)


def _text_of(prompt: list[Any]) -> str:
    return " ".join(getattr(block, "text", "") for block in prompt).lower()


if __name__ == "__main__":
    asyncio.run(acp.run_agent(SpikeAgent))  # type: ignore[arg-type]
