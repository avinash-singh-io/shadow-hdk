"""The client half of ACP — a governance surface with fourteen doors.

Phase 2 measured that `acp.Client` is fourteen methods, and several of them are **governable effects
in their own right**: a child asking to `write_text_file` or `create_terminal` is asking to do
something our six fields already describe. So the bridge does not answer those questions itself. It
turns each into an `EffectProfile`, asks the governance port — the same port the runtime asks before
its own steps — and does what it is told.

The consequence: a mode written for the harness governs a child agent **without knowing that child
exists**. Nobody had to enumerate Codex's tools.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.acp.kinds import (
    effects_for,
    opening_a_terminal,
    reading_a_file,
    writing_a_file,
)

import acp
from acp import schema
from acp.exceptions import RequestError
from shadow_hdk.kernel.components import Provenance
from shadow_hdk.kernel.effects import ASSUME_WORST, EffectProfile
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import Ask, Refuse
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.leash import HeldProcess, start_leashed

REFUSED = 403
"""The JSON-RPC code a refusal travels back on. ACP has no refusal shape for the non-permission
methods — a client either answers or errors — so a governed no is an error the child can read."""


@dataclass(frozen=True)
class Charge:
    """What **one turn** spent — the delta a meter can add without re-charging the last one.

    `None` is *nobody told us*, and it is not the same as `0`, which is *told, and it was nothing*.
    A meter that reads the two the same way reports a total it cannot support.
    """

    input_tokens: int | None
    output_tokens: int | None
    cents: int | None
    foreign: dict[str, Decimal]


class Spend:
    """What a child cost, accumulated across a whole session.

    **Money is accumulated as `Decimal` and converted once.** `Cost.amount` is a float and our
    `cost_cents` is an integer, so converting per call would round `0.004 USD` to zero and a
    thousand such calls would still be zero. Two hundred of them are eighty cents, and that is what
    the meter is told.

    A currency the bridge was not configured for is **not converted** — an exchange rate is policy
    about a tenant's contract, and guessing one would be inventing money. It comes back `None`,
    which the meter reads as *unknown*, with the currency reported so a host can do the sum itself.

    **The totals are the session's; the meter is told the difference.** `step.py` charges what an
    observation reports, once per step, so handing it the running total charges every earlier turn
    again — two 100-token prompts cost 300 (BUG-011). `take()` is the only way the meter reads this
    purse, and it answers *since you last asked*. Cents are the difference of the **rounded totals**
    rather than each charge rounded on its own, which is what keeps the paragraph above true all the
    way to the meter: a sub-cent charge stays in `amount` and is charged on the turn the total
    crosses a cent, never more than half a cent adrift and never adrift for long.
    """

    def __init__(self, currency: str = "USD") -> None:
        self.currency = currency
        self.amount = Decimal(0)
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.foreign: dict[str, Decimal] = {}
        self.tokens_seen = False
        self.cost_seen = False
        self._taken_input = 0
        self._taken_output = 0
        self._taken_cents = 0
        self._taken_foreign: dict[str, Decimal] = {}
        self._tokens_since_take = False
        self._cost_since_take = False

    def add_tokens(self, usage: Any) -> None:
        if usage is None:
            return
        self.tokens_seen = self._tokens_since_take = True
        self.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)

    def add_cost(self, cost: Any) -> None:
        if cost is None:
            return
        self.cost_seen = self._cost_since_take = True
        amount = Decimal(str(cost.amount))
        if cost.currency == self.currency:
            self.amount += amount
        else:
            self.foreign[cost.currency] = self.foreign.get(cost.currency, Decimal(0)) + amount

    @property
    def cents(self) -> int | None:
        """The session's money so far. `None` when nothing priceable arrived, or when it came in a
        currency we cannot read.

        `cost_seen` rather than `amount == 0`, because a charge that arrived and was genuinely zero
        is *known* to be nothing, and reporting it as unknown makes a meter stop claiming a total it
        could have supported.
        """
        if self.foreign:
            return None
        if not self.cost_seen:
            return None
        return int((self.amount * 100).to_integral_value())

    def take(self) -> Charge:
        """What has accrued **since the last take** — one turn's spend, for one charge of a meter.

        Mutating on read is deliberate and is why this is a method rather than a property: the
        delta only means anything if exactly one caller consumes it, and a second read of the same
        turn must charge nothing rather than charge it twice.
        """
        charge = Charge(
            input_tokens=self.input_tokens - self._taken_input if self._tokens_since_take else None,
            output_tokens=(
                self.output_tokens - self._taken_output if self._tokens_since_take else None
            ),
            cents=self._cents_since_take(),
            foreign={
                currency: amount - self._taken_foreign.get(currency, Decimal(0))
                for currency, amount in self.foreign.items()
                if amount != self._taken_foreign.get(currency, Decimal(0))
            },
        )
        self._taken_input, self._taken_output = self.input_tokens, self.output_tokens
        self._taken_cents = self.cents if self.cents is not None else self._taken_cents
        self._taken_foreign = dict(self.foreign)
        self._tokens_since_take = self._cost_since_take = False
        return charge

    def _cents_since_take(self) -> int | None:
        """The difference of the *rounded totals*, so no fraction of a cent is rounded away."""
        if not self._cost_since_take or self.cents is None:
            return None
        return self.cents - self._taken_cents


class BridgeClient(acp.Client):
    """Answers a child agent's requests, having asked our own governance first."""

    def __init__(
        self,
        *,
        workspace: Path | None = None,
        contained: bool = False,
        network: bool = False,
        currency: str = "USD",
        terminal_timeout_s: float = 120.0,
        terminal_output_limit: int = 64_000,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else None
        self._terminal_timeout_s = terminal_timeout_s
        self._terminal_output_limit = terminal_output_limit
        self._terminals: dict[str, HeldProcess] = {}
        self._opened = 0
        self._contained = contained
        self._network = network
        self.spend = Spend(currency)
        self.asked: list[tuple[str, str]] = []
        self.refusals: list[str] = []
        self.updates: list[Any] = []
        self.said: list[str] = []
        self.thought: list[str] = []
        self._thought_taken = 0
        self.overheard: list[Proposal] = []
        self._run: Any = None

    def take_thought(self) -> str:
        """What this turn thought, and clear it — the purse's shape, for the purse's reason: a
        session accumulates and a turn does not."""
        taken = "".join(self.thought[self._thought_taken :])
        self._thought_taken = len(self.thought)
        return taken

    # ------------------------------------------------------------------ governance

    @contextmanager
    def governed_by(self, context: Any) -> Iterator[None]:
        """Say which run this client's callbacks belong to, for as long as a turn lasts.

        **The ambient lookup does not reach here**, and that is not a bug in D2 — it is its edge.
        A contextvar is copied when a task is created, and the ACP SDK creates its reader task in
        `connect_to_agent`, which happens when the session opens and not when a turn runs. Every
        callback the child makes therefore arrives on a task whose context was captured before any
        run existed, and `current_run()` in it is `None`.

        So the bridge **tells** the client which run a prompt belongs to rather than hoping a
        contextvar propagates through somebody else's task. Any adapter whose callbacks are driven
        by a foreign event loop has the same problem and needs the same answer.
        """
        previous, self._run = self._run, context
        try:
            yield
        finally:
            self._run = previous

    async def _judge(self, effects: EffectProfile, what: str) -> str | None:
        """`None` means go ahead; a string is the reason it may not.

        Outside a run there is no governance to ask, and the answer to *may this untrusted child
        write to your disk* with nobody to ask is no.
        """
        context = self._run or current_run()
        if context is None:
            return "there is no run to govern this"
        judgement = await context.ports.governance.judge(effects, context.context(what))
        match judgement:
            case Refuse(reason=reason):
                self.refusals.append(f"{what}: {reason}")
                return reason
            case Ask(question=question):
                # **A child holding an open request cannot wait for a person.** Our `Ask` is an
                # `interrupt()` that ends the parent's step, and the child's JSON-RPC call would be
                # abandoned mid-flight — so the honest answer here is no, with the question said.
                # A host that wants a person in the loop for a child agent pre-authorises through a
                # mode. Lifting this needs ACP to gain a "hold" or the bridge to gain a permission
                # cache a host can fill ahead of time; recorded rather than papered over.
                self.asked.append((what, question))
                self.refusals.append(f"{what}: would have asked — {question}")
                return f"this needs a person to allow it first: {question}"
        return None

    # ------------------------------------------------------------------ permission

    async def request_permission(
        self,
        session_id: str,
        tool_call: schema.ToolCallUpdate,
        options: list[schema.PermissionOption],
        **kwargs: Any,
    ) -> schema.RequestPermissionResponse:
        kind = getattr(tool_call, "kind", None)
        effects = effects_for(kind, contained=self._contained, network=self._network)
        refused = await self._judge(effects, f"tool:{kind or 'unknown'}")
        if refused is None:
            return schema.RequestPermissionResponse(
                outcome=self._choose(options, allow=True)
                or schema.AllowedOutcome(option_id="", outcome="selected")
            )
        chosen = self._choose(options, allow=False)
        # **Prefer the agent's own rejection option.** Choosing one it offered is answering in
        # its vocabulary — it can tell "not this time" from "never" and adapt. `DeniedOutcome` is
        # the blunter "I will not answer", and it is the fallback for an agent that offered no way
        # to say no. `reject_once` rather than `reject_always`: our governance was asked about this
        # call, not every future one, and claiming permanence would assert a policy nobody wrote.
        return schema.RequestPermissionResponse(
            outcome=chosen or schema.DeniedOutcome(outcome="cancelled")
        )

    @staticmethod
    def _choose(
        options: list[schema.PermissionOption], *, allow: bool
    ) -> schema.AllowedOutcome | None:
        wanted = ("allow_once", "allow_always") if allow else ("reject_once", "reject_always")
        for kind in wanted:
            for option in options:
                if option.kind == kind:
                    return schema.AllowedOutcome(option_id=option.option_id, outcome="selected")
        return None

    # ------------------------------------------------------------------ the filesystem

    def _inside(self, path: str) -> Path:
        if self.workspace is None:
            raise RequestError(REFUSED, "this bridge offers no filesystem")
        target = (self.workspace / path).resolve()
        if target != self.workspace and not target.is_relative_to(self.workspace):
            raise RequestError(REFUSED, f"{path!r} resolves outside the workspace")
        return target

    async def read_text_file(
        self,
        session_id: str,
        path: str,
        line: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> schema.ReadTextFileResponse:
        if refused := await self._judge(reading_a_file(), "read_text_file"):
            raise RequestError(REFUSED, refused)
        try:
            return schema.ReadTextFileResponse(content=self._inside(path).read_text())
        except OSError as broken:
            raise RequestError(REFUSED, f"{type(broken).__name__}: {broken}") from broken

    async def write_text_file(
        self, session_id: str, path: str, content: str, **kwargs: Any
    ) -> schema.WriteTextFileResponse:
        if refused := await self._judge(writing_a_file(), "write_text_file"):
            raise RequestError(REFUSED, refused)
        target = self._inside(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return schema.WriteTextFileResponse()

    # ------------------------------------------------------------------ terminals

    async def create_terminal(
        self,
        session_id: str,
        command: str,
        args: list[str] | None = None,
        env: list[Any] | None = None,
        cwd: str | None = None,
        output_byte_limit: int | None = None,
        **kwargs: Any,
    ) -> schema.CreateTerminalResponse:
        """Grant a terminal, on our leash and inside the workspace (D42).

        Judged **before anything starts**: a refusal that had already run the command would be a
        report rather than a refusal. The effects are those of opening a terminal at all — reading
        and writing the workspace, reaching the network unless containment says otherwise,
        irreversible — so a mode that permits no writes refuses this without knowing the word
        *terminal*.

        The process itself is the runtime's `HeldProcess`: its own group, a capped output, a
        timeout that runs whether or not anybody waits, and a kill that takes the group (D35). This
        adapter borrows all of it, which is why granting a terminal does not make the ACP adapter
        import the sandbox adapter — rule 4 stays green because the leash sits below both.
        """
        effects = opening_a_terminal(contained=self._contained, network=self._network)
        if refused := await self._judge(effects, "create_terminal"):
            raise RequestError(REFUSED, refused)
        if self.workspace is None:
            raise RequestError(
                REFUSED,
                "this bridge has no workspace, and nowhere to run it is not somewhere to run it",
            )
        where = self._inside(cwd) if cwd else self.workspace
        try:
            held = await start_leashed(
                [command, *(args or [])],
                cwd=where,
                timeout_s=self._terminal_timeout_s,
                output_limit=output_byte_limit or self._terminal_output_limit,
            )
        except OSError as broken:
            raise RequestError(REFUSED, f"{type(broken).__name__}: {broken}") from broken
        self._opened += 1
        terminal_id = f"terminal-{self._opened}"
        self._terminals[terminal_id] = held
        return schema.CreateTerminalResponse(terminalId=terminal_id)

    # The follow-ups are **not re-judged**: the grant was at creation, and asking again for every
    # read of a terminal that was already allowed is noise, not safety.
    def _terminal(self, terminal_id: str) -> HeldProcess:
        if (held := self._terminals.get(terminal_id)) is None:
            raise RequestError(REFUSED, f"no terminal {terminal_id!r}")
        return held

    async def terminal_output(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> schema.TerminalOutputResponse:
        text, truncated = self._terminal(terminal_id).captured()
        status = self._terminal(terminal_id).exit_status
        return schema.TerminalOutputResponse(
            output=text,
            truncated=truncated,
            exitStatus=(
                schema.TerminalExitStatus(exitCode=status.exit_code, signal=status.signal)
                if status
                else None
            ),
        )

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> schema.WaitForTerminalExitResponse:
        ended = await self._terminal(terminal_id).wait()
        return schema.WaitForTerminalExitResponse(exitCode=ended.exit_code, signal=ended.signal)

    async def kill_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> schema.KillTerminalResponse:
        await self._terminal(terminal_id).kill()
        return schema.KillTerminalResponse()

    async def release_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> schema.ReleaseTerminalResponse:
        """The child is finished with it. Anything still running is **ended** rather than left
        behind — a step owns the process tree it starts (D35)."""
        await self._terminal(terminal_id).release()
        del self._terminals[terminal_id]
        return schema.ReleaseTerminalResponse()

    async def end_every_terminal(self) -> None:
        """Everything this bridge opened, ended. Called when the session closes, so a child that
        forgot to release leaves nothing running."""
        for terminal_id in list(self._terminals):
            with suppress(Exception):
                await self._terminals.pop(terminal_id).release()

    # ------------------------------------------------------------------ asking a person

    async def create_elicitation(self, message: str, mode: Any, **kwargs: Any) -> Any:
        """A child asking a person directly. Refused for the same reason `Ask` is: there is nobody
        on this end of the pipe, and pretending otherwise would answer for them."""
        self.asked.append(("elicitation", message))
        raise RequestError(REFUSED, "there is no person on this end of the bridge")

    async def complete_elicitation(self, elicitation_id: str, **kwargs: Any) -> None:
        raise RequestError(REFUSED, "there is no person on this end of the bridge")

    # ------------------------------------------------------------------ everything else

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        self.updates.append(update)
        kind = getattr(update, "session_update", None)
        if kind == "usage_update":
            self.spend.add_cost(getattr(update, "cost", None))
        elif kind == "tool_call":
            # **Work we did not gate.** The child did this on its own and is telling us afterwards,
            # so it is recorded as `observed` — we could not have refused it, and saying otherwise
            # would make an ungated effect indistinguishable from a consented one (`08` §9 R9).
            self.overheard.append(
                Proposal(
                    kind="tool_call",
                    payload={
                        "tool_call_id": getattr(update, "tool_call_id", None),
                        "title": getattr(update, "title", None),
                        "kind": getattr(update, "kind", None),
                    },
                    provenance=Provenance(
                        registered_by=session_id,
                        adapter="acp",
                        at="",
                        posture="observed",
                    ),
                )
            )
        elif kind == "agent_message_chunk":
            text = getattr(getattr(update, "content", None), "text", None)
            if isinstance(text, str):
                self.said.append(text)
        elif kind == "agent_thought_chunk":
            # **Why before what** (D45): on the record as it arrives, because the calls it led to
            # are landing through this bridge's doors as they happen. Kept apart from `said` —
            # a thought reported as speech would put words in the child's mouth.
            text = getattr(getattr(update, "content", None), "text", None)
            if isinstance(text, str):
                self.thought.append(text)
                context = self._run or current_run()
                if context is not None:
                    await context.reasoning(text)

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """An extension nobody vouched for. `ASSUME_WORST` and, by default, no."""
        if refused := await self._judge(ASSUME_WORST, f"ext:{method}"):
            raise RequestError(REFUSED, refused)
        raise RequestError(REFUSED, f"no extension method {method!r}")

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        return None

    def on_connect(self, conn: Any) -> None:
        return None


__all__ = ["REFUSED", "BridgeClient", "Spend"]
