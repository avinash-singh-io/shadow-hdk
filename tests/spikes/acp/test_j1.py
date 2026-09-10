"""J1, measured over a real ACP pipe.

Two processes, real stdio, the SDK on both ends. What this proves is the **protocol and the
transport**: that a denial travels, that an agent can tell a denial from a rejection from consent,
that a turn's end reaches the client with a stop reason, and that usage arrives both mid-turn and at
the end. That is the client half of the Phase 4 bridge, validated before it is written.

What it does **not** prove is what Codex or Claude Code do when refused. Our agent's behaviour is
our choice, and measuring your own choice is not measurement. That half of J1 stays open, and the
command that would close it is in `history.md`.

Every test is bounded by `asyncio.wait_for`, because the failure J1 fears is a **hang**, and an
assertion cannot catch one — a hanging test hangs.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import acp
import pytest
from acp import schema

TIMEOUT = 20.0
AGENT = ["-m", "spikes.acp.agent"]


class Answering(acp.Client):
    """A client that answers permission requests a chosen way, and records what it saw."""

    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.asked: list[schema.ToolCallUpdate] = []
        self.updates: list[Any] = []

    async def request_permission(
        self,
        session_id: str,
        tool_call: schema.ToolCallUpdate,
        options: list[schema.PermissionOption],
        **kwargs: Any,
    ) -> schema.RequestPermissionResponse:
        self.asked.append(tool_call)
        if self._answer == "deny":
            return schema.RequestPermissionResponse(
                outcome=schema.DeniedOutcome(outcome="cancelled")
            )
        chosen = "no" if self._answer == "reject" else "yes"
        return schema.RequestPermissionResponse(
            outcome=schema.AllowedOutcome(option_id=chosen, outcome="selected")
        )

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        self.updates.append(update)

    # ------------------------------------------------------------------ the rest of the surface
    #
    # **`acp.Client` is fourteen methods, not two**, and mypy is what said so. Refusing a
    # capability is a legitimate answer — a client that offers no terminal says so when asked — but
    # it has to be *answered*, and this is the list Phase 4's bridge inherits. Written out rather
    # than stubbed with `# type: ignore`, because the list is the finding.

    async def read_text_file(
        self,
        session_id: str,
        path: str,
        line: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError("this spike offers no filesystem")

    async def write_text_file(self, session_id: str, path: str, content: str, **kwargs: Any) -> Any:
        raise NotImplementedError("this spike offers no filesystem")

    async def create_terminal(
        self,
        session_id: str,
        command: str,
        args: list[str] | None = None,
        env: list[Any] | None = None,
        cwd: str | None = None,
        output_byte_limit: int | None = None,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError("this spike offers no terminal")

    async def terminal_output(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise NotImplementedError("this spike offers no terminal")

    async def wait_for_terminal_exit(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise NotImplementedError("this spike offers no terminal")

    async def kill_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise NotImplementedError("this spike offers no terminal")

    async def release_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise NotImplementedError("this spike offers no terminal")

    async def create_elicitation(self, message: str, mode: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("this spike asks nobody anything")

    async def complete_elicitation(self, elicitation_id: str, **kwargs: Any) -> None:
        raise NotImplementedError("this spike asks nobody anything")

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"no extension method {method!r}")

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        return None

    def on_connect(self, conn: Any) -> None:
        return None


@asynccontextmanager
async def driving(answer: str) -> AsyncIterator[tuple[Any, Answering, str]]:
    client = Answering(answer)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        *AGENT,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        # **Named from the agent's side.** `input_stream` is what goes *into* the agent — the
        # writer — and `output_stream` is what comes out of it. Passing them the intuitive way
        # round raises a bare `TypeError` from inside the SDK with no hint which argument is wrong.
        agent = acp.connect_to_agent(client, process.stdin, process.stdout)
        await asyncio.wait_for(agent.initialize(protocol_version=1), TIMEOUT)
        session = await asyncio.wait_for(agent.new_session(cwd="/tmp"), TIMEOUT)
        yield agent, client, session.session_id
    finally:
        process.terminate()
        await process.wait()


async def ask(agent: Any, session_id: str, text: str) -> schema.PromptResponse:
    answer: schema.PromptResponse = await asyncio.wait_for(
        agent.prompt(
            session_id=session_id, prompt=[schema.TextContentBlock(type="text", text=text)]
        ),
        TIMEOUT,
    )
    return answer


# ---------------------------------------------------------------- J1(a): refusal


async def test_a_denied_tool_call_ends_the_turn_rather_than_hanging() -> None:
    """The question R2 rests on. Bounded, so a hang fails in twenty seconds instead of forever."""
    async with driving("deny") as (agent, client, session):
        answer = await ask(agent, session, "tool")
    assert client.asked, "the agent never asked"
    assert answer.stop_reason == "cancelled"


async def test_a_rejection_option_is_also_a_no_and_also_ends_the_turn() -> None:
    """Two ways to say no, and they are **not** the same message.

    `DeniedOutcome` is the client declining to answer. `AllowedOutcome` carrying a `reject_once`
    option id is the client *answering*, with a no — and an agent that checks only for the first
    reads a considered rejection as consent. Our bridge must send whichever the host means.
    """
    async with driving("reject") as (agent, client, session):
        answer = await ask(agent, session, "tool")
    assert answer.stop_reason == "cancelled"


async def test_consent_lets_the_turn_finish() -> None:
    async with driving("allow") as (agent, client, session):
        answer = await ask(agent, session, "tool")
    assert answer.stop_reason == "end_turn"


async def test_an_agent_may_refuse_on_its_own_and_says_so_distinctly() -> None:
    """`refusal` means the agent declined; `cancelled` means it was not allowed. A meter that
    collapses the two cannot tell a governed refusal from a model changing its mind."""
    async with driving("allow") as (agent, _client, session):
        answer = await ask(agent, session, "refuse")
    assert answer.stop_reason == "refusal"


async def test_an_agent_that_retries_a_refusal_forever_is_caught_by_the_clock() -> None:
    """The failure J1 exists to rule out, staged deliberately so the *detection* is proven.

    Nothing in ACP stops an agent looping on a denial. A driver of somebody else's CLI therefore
    needs a wall clock of its own — which our lease already is.
    """
    with pytest.raises(TimeoutError):
        async with driving("deny") as (agent, _client, session):
            await asyncio.wait_for(
                agent.prompt(
                    session_id=session, prompt=[schema.TextContentBlock(type="text", text="loop")]
                ),
                2.0,
            )


# ---------------------------------------------------------------- J1(b): usage


async def test_usage_arrives_at_the_end_of_a_turn() -> None:
    async with driving("allow") as (agent, _client, session):
        answer = await ask(agent, session, "tool")
    assert answer.usage is not None
    assert answer.usage.input_tokens == 1200
    assert answer.usage.output_tokens == 200
    assert answer.usage.total_tokens == 1400


async def test_usage_also_arrives_mid_turn_with_a_price_on_it() -> None:
    """`UsageUpdate` carries `cost: Cost(amount, currency)` — the one money-shaped thing in ACP,
    and the only place any protocol in this design quotes a price rather than a token count."""
    async with driving("allow") as (agent, client, session):
        await ask(agent, session, "tool")
    usage_updates = [
        u for u in client.updates if getattr(u, "session_update", "") == "usage_update"
    ]
    assert usage_updates, (
        f"no usage update in {[getattr(u, 'session_update', u) for u in client.updates]}"
    )
    cost = usage_updates[0].cost
    assert cost is not None and cost.currency == "USD" and cost.amount == pytest.approx(0.004)


async def test_an_agent_may_report_no_usage_at_all() -> None:
    """`PromptResponse.usage` is optional, so a conformant agent can say nothing. That is the case
    the meter must call **unknown** rather than zero (`10` §5 R2)."""
    async with driving("allow") as (agent, _client, session):
        answer = await ask(agent, session, "no-usage")
    assert answer.usage is None
