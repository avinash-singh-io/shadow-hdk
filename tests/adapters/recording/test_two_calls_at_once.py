"""A CLI that makes two tool calls at once gets two answers (BUG-024).

Measured 2026-09-12: `RecordingServer.call` reserved the parent's **entire** remaining cost for
one call, so a second call arriving while the first was still running was carved from nothing and
its child ended `lease_exhausted` before judging anything — the CLI was told *the call produced no
observation*. A model that issues its tool calls in parallel, which the coding CLIs all do, had
every call after the first fail whenever the run had a cost ceiling.

A call reserves what one step could plausibly cost, not everything; and two calls asked about at
once are two open questions, answered in any order, neither ending the other.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from shadow_hdk.adapters.recording import RecordingServer

from shadow_hdk.kernel import EffectProfile, Ended, ScopeSet
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Questions, RunContext

from .conftest import with_a_run

pytestmark = pytest.mark.anyio


async def test_two_allowed_calls_at_once_both_run() -> None:
    async def drive(context: RunContext) -> Any:
        holder = RecordingServer(context)
        return await asyncio.gather(holder.call("look", {}), holder.call("look", {}))

    (one, two), events = await with_a_run(drive, steps=40)

    assert not one.is_error and not two.is_error, (one.content[0].text, two.content[0].text)
    assert '"found"' in one.content[0].text and '"found"' in two.content[0].text
    exhausted = [e for e in events if isinstance(e, Ended) and e.reason == "lease_exhausted"]
    assert not exhausted, "a child was born exhausted"


class AsksAboutWrites:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        if effects.writes and not effects.writes <= ScopeSet.of("nothing"):
            return Ask(f"{context.step} wants to write; allow?")
        return Allow()


async def test_two_questions_at_once_answered_backwards() -> None:
    questions = Questions()
    order: list[str] = []

    async def the_host_answers_backwards() -> None:
        first = await asyncio.wait_for(questions.next(), 10)
        second = await asyncio.wait_for(questions.next(), 10)
        assert first.handle != second.handle
        questions.answer(second.handle, Allow())
        order.append("second")
        await asyncio.sleep(0.3)  # the first is still open while the second runs and returns
        assert questions.pending() == (first,), "the first question was lost"
        questions.answer(first.handle, Allow())
        order.append("first")

    async def drive(context: RunContext) -> Any:
        holder = RecordingServer(context)
        host = asyncio.create_task(the_host_answers_backwards())
        try:
            return await asyncio.gather(holder.call("wipe", {}), holder.call("wipe", {}))
        finally:
            await host

    (one, two), _ = await with_a_run(
        drive, governance=AsksAboutWrites(), questions=questions, steps=40
    )

    assert order == ["second", "first"]
    assert not one.is_error and not two.is_error, (one.content[0].text, two.content[0].text)
    assert '"wiped": true' in one.content[0].text and '"wiped": true' in two.content[0].text


async def test_two_questions_over_the_socket_answered_backwards() -> None:
    """The same, through the door a CLI actually uses: the relay, MCP, two concurrent requests."""
    import sys
    from pathlib import Path

    from shadow_hdk.adapters.recording import PORT_VARIABLE, TOKEN_VARIABLE, serve_over_socket
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    relay = str(Path(sys.executable).parent / "shadow-hdk-registry")
    questions = Questions()

    async def the_host_answers_backwards() -> None:
        first = await asyncio.wait_for(questions.next(), 20)
        second = await asyncio.wait_for(questions.next(), 20)
        questions.answer(second.handle, Allow())
        await asyncio.sleep(0.5)
        questions.answer(first.handle, Allow())

    async def drive(context: RunContext) -> Any:
        holder = RecordingServer(context)
        host = asyncio.create_task(the_host_answers_backwards())
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            parameters = StdioServerParameters(
                command=relay, args=[], env={PORT_VARIABLE: str(port), TOKEN_VARIABLE: token}
            )
            async with (
                stdio_client(parameters) as (incoming, outgoing),
                ClientSession(incoming, outgoing) as session,
            ):
                await session.initialize()
                try:
                    async with asyncio.timeout(30):
                        return await asyncio.gather(
                            session.call_tool("wipe", {}), session.call_tool("wipe", {})
                        )
                finally:
                    await host

    (one, two), _ = await with_a_run(
        drive, governance=AsksAboutWrites(), questions=questions, steps=40
    )
    assert not one.is_error and not two.is_error, (one.content[0].text, two.content[0].text)


async def test_a_call_the_cli_cancels_does_not_end_the_conversation() -> None:
    """A CLI gives up on a tool call it has waited too long for (its MCP timeout) and sends
    `notifications/cancelled`. Measured 2026-09-12 in the studio: one question left unanswered for
    a minute, and when the CLI cancelled it the step holding the conversation failed with
    *unhandled errors in a TaskGroup* and the run ended. The cancelled call's question is
    withdrawn, its child let go, and the registry keeps serving the calls that follow.
    """
    import sys
    from pathlib import Path

    from shadow_hdk.adapters.recording import PORT_VARIABLE, TOKEN_VARIABLE, serve_over_socket
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    relay = str(Path(sys.executable).parent / "shadow-hdk-registry")
    questions = Questions()

    async def drive(context: RunContext) -> Any:
        holder = RecordingServer(context)
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            parameters = StdioServerParameters(
                command=relay, args=[], env={PORT_VARIABLE: str(port), TOKEN_VARIABLE: token}
            )
            async with (
                stdio_client(parameters) as (incoming, outgoing),
                ClientSession(incoming, outgoing) as session,
            ):
                await session.initialize()
                async with asyncio.timeout(30):
                    # The CLI's side of a timeout: the SDK raises *and sends*
                    # `notifications/cancelled` — the same as the TypeScript SDK inside Claude Code.
                    doomed = asyncio.ensure_future(
                        session.call_tool("wipe", {}, read_timeout_seconds=1)
                    )
                    pending = await asyncio.wait_for(questions.next(), 10)
                    assert questions.pending() == (pending,)
                    with pytest.raises(Exception, match="[Tt]imed out|timeout"):
                        await doomed
                    await asyncio.sleep(0.5)
                    withdrawn = questions.pending() == ()
                    # The conversation goes on: the next call is served and answered.
                    after = asyncio.ensure_future(session.call_tool("wipe", {}))
                    next_question = await asyncio.wait_for(questions.next(), 10)
                    questions.answer(next_question.handle, Allow())
                    served = await after
                    return withdrawn, served

    (withdrawn, served), events = await with_a_run(
        drive, governance=AsksAboutWrites(), questions=questions, steps=40
    )
    assert withdrawn, "the cancelled call's question was still pending"
    assert not served.is_error and '"wiped": true' in served.content[0].text
    assert not [e for e in events if e.kind == "observed" and e.observation.kind == "failed"], (
        "the step holding the conversation failed"
    )


async def test_a_relay_that_dies_mid_question_does_not_end_the_conversation() -> None:
    """The other thing a CLI does after a tool timeout: restart the MCP server — kill the relay
    and spawn a fresh one. The old connection closes with a question still open; the new relay
    must be served as if nothing had happened."""
    import sys
    from pathlib import Path

    from shadow_hdk.adapters.recording import PORT_VARIABLE, TOKEN_VARIABLE, serve_over_socket
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    relay = str(Path(sys.executable).parent / "shadow-hdk-registry")
    questions = Questions()

    async def drive(context: RunContext) -> Any:
        holder = RecordingServer(context)
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            parameters = StdioServerParameters(
                command=relay, args=[], env={PORT_VARIABLE: str(port), TOKEN_VARIABLE: token}
            )
            async with asyncio.timeout(40):
                async with (
                    stdio_client(parameters) as (incoming, outgoing),
                    ClientSession(incoming, outgoing) as session,
                ):
                    await session.initialize()
                    doomed = asyncio.ensure_future(session.call_tool("wipe", {}))
                    await asyncio.wait_for(questions.next(), 10)
                    doomed.cancel()
                # The relay is gone with the question still open.
                await asyncio.sleep(0.5)
                async with (
                    stdio_client(parameters) as (incoming, outgoing),
                    ClientSession(incoming, outgoing) as session,
                ):
                    await session.initialize()
                    after = asyncio.ensure_future(session.call_tool("wipe", {}))
                    next_question = await asyncio.wait_for(questions.next(), 10)
                    questions.answer(next_question.handle, Allow())
                    return await after

    served, events = await with_a_run(
        drive, governance=AsksAboutWrites(), questions=questions, steps=40
    )
    assert not served.is_error and '"wiped": true' in served.content[0].text
    assert not [e for e in events if e.kind == "observed" and e.observation.kind == "failed"], (
        "the step holding the conversation failed"
    )


async def test_an_answer_to_a_connection_that_is_gone_does_not_end_the_conversation() -> None:
    """The shape that actually took the studio down (measured 2026-09-12): a question was left
    open past the CLI's MCP timeout, the CLI killed its relay and started another, and *then* the
    person answered. The child ran, and its result was written to a connection that no longer
    existed — which raised inside the registry's task group and failed the step holding the
    conversation. A dead connection is that connection's problem, not the conversation's.
    """
    import sys
    from pathlib import Path

    from shadow_hdk.adapters.recording import PORT_VARIABLE, TOKEN_VARIABLE, serve_over_socket
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    relay = str(Path(sys.executable).parent / "shadow-hdk-registry")
    questions = Questions()

    async def drive(context: RunContext) -> Any:
        holder = RecordingServer(context)
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            parameters = StdioServerParameters(
                command=relay, args=[], env={PORT_VARIABLE: str(port), TOKEN_VARIABLE: token}
            )
            async with asyncio.timeout(40):
                async with (
                    stdio_client(parameters) as (incoming, outgoing),
                    ClientSession(incoming, outgoing) as session,
                ):
                    await session.initialize()
                    doomed = asyncio.ensure_future(session.call_tool("wipe", {}))
                    late = await asyncio.wait_for(questions.next(), 10)
                    doomed.cancel()
                # The relay is gone. Now the person answers the question it was waiting on.
                await asyncio.sleep(0.3)
                questions.answer(late.handle, Allow())
                await asyncio.sleep(1.0)  # the child runs; its result has nowhere to go
                async with (
                    stdio_client(parameters) as (incoming, outgoing),
                    ClientSession(incoming, outgoing) as session,
                ):
                    await session.initialize()
                    after = asyncio.ensure_future(session.call_tool("wipe", {}))
                    next_question = await asyncio.wait_for(questions.next(), 10)
                    questions.answer(next_question.handle, Allow())
                    return await after

    served, events = await with_a_run(
        drive, governance=AsksAboutWrites(), questions=questions, steps=40
    )
    assert not served.is_error and '"wiped": true' in served.content[0].text
    failed = [e for e in events if e.kind == "observed" and e.observation.kind == "failed"]
    assert not failed, f"the step holding the conversation failed: {failed[0].observation}"
