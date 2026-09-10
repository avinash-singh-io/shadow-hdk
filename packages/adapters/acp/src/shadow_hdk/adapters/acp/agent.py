"""Another agent, driven as a component.

`09` §8: *driving a locally installed agent over ACP is the harness's business; whether this
deployment allows it, and whose plan covers it, is the product's.* This is the harness's half.

Three things it owns, each because Phase 2 measured that somebody had to:

* **Residency.** One process and one handshake for the session, not one per step. A child agent is
  expensive to start, and a five-step composition should not be five cold starts.
* **A clock.** Nothing in ACP stops an agent looping on a denial, so the bridge bounds every turn by
  `min(its own timeout, what the lease has left)` — an adapter cannot be constructed generously
  enough to outlive the run that invoked it.
* **A purse.** What the child spent comes back in the shape `_usage_of` reads, so the parent's meter
  charges it without knowing ACP exists.
"""

from __future__ import annotations

import asyncio
import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.acp.client import BridgeClient
from pydantic import JsonValue

import acp
from acp import schema
from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort, ToolSource, Turn, Usage
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.processes import stop_or_kill

BRIEF_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {"brief": {"type": "string"}},
    "required": ["brief"],
}


def mcp_servers_from(tools: Sequence[ToolSource]) -> list[Any]:
    """Turn the run's tool sources into what ACP's `session/new` takes (D42).

    **This adapter never learns whose registry it is.** `ToolSource` is a kernel type; whoever opens
    the session builds it. That is what lets the registry's address travel in here without this
    package importing the one that serves it, which rule 4 of the stands-alone invariant would fail
    the build for.

    A kind nothing here can serve is **refused, naming it**. Dropping it silently would launch the
    child with no tools at all, which looks exactly like a model that chose not to use any — the
    most expensive possible way to fail, because it fails after the turn is paid for.
    """
    made: list[Any] = []
    for source in tools:
        match source.kind:
            case "mcp":
                command, *arguments = shlex.split(source.address)
                made.append(
                    schema.McpServerStdio(
                        name="shadow-hdk", command=command, args=list(arguments), env=[]
                    )
                )
            case "mcp-http":
                made.append(
                    schema.HttpMcpServer(
                        type="http", name="shadow-hdk", url=source.address, headers=[]
                    )
                )
            case other:
                raise ValueError(
                    f"nothing here serves a tool source of kind {other!r}; the child would be "
                    "launched with no tools and look like a model that chose not to use any"
                )
    return made


class AcpAgent(ComponentPort):
    def __init__(
        self,
        command: str,
        args: Sequence[str] = (),
        *,
        name: str = "acp_agent",
        effects: EffectProfile,
        description: str = "Hand a brief to another agent and get back what it did.",
        workspace: Path | None = None,
        tools: Sequence[ToolSource] = (),
        contained: bool = False,
        network: bool = False,
        currency: str = "USD",
        timeout_s: float = 300.0,
        grace_s: float = 5.0,
        cwd: Path | None = None,
        at: str = "",
        source: str = "acp",
    ) -> None:
        self._command = command
        self._args = list(args)
        self._cwd = cwd
        self._timeout_s = timeout_s
        self._workspace = workspace
        self._tools = tuple(tools)
        self.client = BridgeClient(
            workspace=workspace, contained=contained, network=network, currency=currency
        )
        self._grace_s = grace_s
        self.had_to_be_killed = False
        """Whether the last `stop()` had to go past `SIGTERM`. A child that never goes quietly
        is worth a host's attention, and reading that off a log line is not recording it."""
        self._process: asyncio.subprocess.Process | None = None
        self._agent: Any = None
        self._session: str | None = None
        self.sessions_opened = 0
        self._registration = Registration(
            id=name,
            component=Component(
                interface=Interface(
                    name=name,
                    description=description,
                    input_schema=BRIEF_SCHEMA,
                    output_schema={"type": "object"},
                ),
                effects=effects,
                provenance=Provenance(registered_by=source, adapter="acp", at=at),
                labels=frozenset({"agent"}),
            ),
        )

    # ------------------------------------------------------------------ residency

    async def start(self) -> None:
        self._process = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            cwd=self._cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            # Its own session, so `stop()` can end the whole tree (D35). A coding agent spawns
            # compilers, test runners and language servers; without this they are in *our* group
            # and survive the child that started them.
            start_new_session=True,
        )
        # Named from the agent's side: `input_stream` is what goes *into* it — the writer.
        self._agent = acp.connect_to_agent(self.client, self._process.stdin, self._process.stdout)
        await asyncio.wait_for(self._agent.initialize(protocol_version=1), self._timeout_s)
        opened = await asyncio.wait_for(
            self._agent.new_session(
                cwd=str(self._workspace or Path.cwd()),
                mcp_servers=mcp_servers_from(self._tools),
            ),
            self._timeout_s,
        )
        self._session = opened.session_id
        self.sessions_opened += 1

    async def stop(self) -> None:
        """Ask the child to go, and make it go if it will not (BUG-011, D35).

        It used to `terminate()` and then `wait()` with no deadline, so a child that ignores
        `SIGTERM` — which a busy agent mid-tool-call may well do — wedged the caller forever. The
        grace period is real: an agent asked politely gets to flush its transcript and close what
        it had open. After it, the **group** goes, because by then the child has proven it is not
        cooperating and everything it started is still ours to account for.
        """
        if self._process is not None:
            self.had_to_be_killed = await stop_or_kill(self._process, grace_s=self._grace_s)
        self._process, self._agent, self._session = None, None, None

    async def __aenter__(self) -> AcpAgent:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    @property
    def process_is_running(self) -> bool:
        """Whether the child is still alive. A timed-out child that is merely *ignored* is a leaked
        process holding a subscription seat, so this is asserted rather than assumed."""
        return self._process is not None and self._process.returncode is None

    # ------------------------------------------------------------------ the agent seam (D39)

    async def turn(self, prompt: str) -> Turn:
        """One turn of the provider's own loop.

        **No tool calls come back.** They left through the injected registry and landed on the run's
        graph, judged and charged and recorded (D42). What is here is what only the provider knows:
        what it said, what it spent, and why it stopped.
        """
        if self._agent is None or self._session is None:
            await self.start()
        assert self._agent is not None and self._session is not None

        said_before = len(self.client.said)
        with self.client.governed_by(current_run()):
            answered = await asyncio.wait_for(
                self._agent.prompt(
                    session_id=self._session,
                    prompt=[schema.TextContentBlock(type="text", text=prompt)],
                ),
                self._clock(),
            )
        self.client.spend.add_tokens(getattr(answered, "usage", None))
        charge = self.client.spend.take()
        return Turn(
            text="".join(self.client.said[said_before:]),
            usage=Usage(
                input_tokens=charge.input_tokens or None,
                output_tokens=charge.output_tokens or None,
                cost_cents=charge.cents or None,
            ),
            stop_reason=str(getattr(answered, "stop_reason", "") or ""),
        )

    async def close(self) -> None:
        """Ending the session ends everything it opened — terminals included (D35)."""
        await self.client.end_every_terminal()
        await self.stop()

    # ------------------------------------------------------------------ the port

    async def registrations(self) -> Sequence[Registration]:
        return [self._registration]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        if registration != self._registration.id:
            return Failed(f"no component registered as {registration!r}")
        if self._agent is None or self._session is None:
            return Failed(f"{self._registration.id!r} is not started")
        brief = inputs.get("brief") if isinstance(inputs, dict) else None
        if not isinstance(brief, str):
            return Failed("a child agent needs a brief: a string saying what to work on")

        said_before = len(self.client.said)
        try:
            # The client's callbacks run on the SDK's own reader task, whose context was captured
            # when the session opened — so it is told which run governs it rather than looking.
            with self.client.governed_by(current_run()):
                reply = await asyncio.wait_for(
                    self._agent.prompt(
                        session_id=self._session,
                        prompt=[schema.TextContentBlock(type="text", text=brief)],
                    ),
                    self._clock(),
                )
        except TimeoutError:
            # A child that will not stop is stopped. Killing it is the point: leaving a wedged
            # process behind would make the next step inherit somebody else's problem.
            await self.stop()
            return Failed(f"the child agent did not finish within {self._clock():g}s")
        except Exception as broken:  # noqa: BLE001 — a child is untrusted like any component (D7)
            return Failed(f"{type(broken).__name__}: {broken}")

        return Completed(
            {
                "text": "".join(self.client.said[said_before:]),
                "stop_reason": reply.stop_reason,
                "usage": self._usage(reply.usage),
                "refusals": list(self.client.refusals),
            }
        )

    def _clock(self) -> float:
        """`min(what this adapter was told, what the lease has left)`.

        An adapter constructed with a generous timeout cannot outlive the run that invoked it.
        """
        context = current_run()
        if context is None:
            return self._timeout_s
        return min(self._timeout_s, float(context.remaining().ceiling.max_wall_seconds))

    def _usage(self, reported: Any) -> dict[str, JsonValue]:
        """In the shape `_usage_of` reads, so the parent's meter charges without knowing ACP.

        **What this turn spent, never what the session holds** (BUG-011). The purse is cumulative
        because a session is, and `step.py` adds what it is handed once per step — so reporting the
        running total charged the first turn again on the second and twice more on the third.
        """
        self.client.spend.add_tokens(reported)
        charge = self.client.spend.take()
        usage: dict[str, JsonValue] = {
            "input_tokens": charge.input_tokens,
            "output_tokens": charge.output_tokens,
            "cost_cents": charge.cents,
        }
        if charge.foreign:
            # Not converted, and not hidden: a host with a rate can do the sum itself.
            usage["uncounted_currencies"] = {
                currency: str(amount) for currency, amount in charge.foreign.items()
            }
        return usage


__all__ = ["AcpAgent"]
