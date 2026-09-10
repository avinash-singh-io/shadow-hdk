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
from shadow_hdk.kernel.effects import ASSUME_WORST, EffectProfile
from shadow_hdk.kernel.ports import Ask, Refuse
from shadow_hdk.runtime import current_run

REFUSED = 403
"""The JSON-RPC code a refusal travels back on. ACP has no refusal shape for the non-permission
methods — a client either answers or errors — so a governed no is an error the child can read."""


class Spend:
    """What a child cost, accumulated across a whole session.

    **Money is accumulated as `Decimal` and converted once.** `Cost.amount` is a float and our
    `cost_cents` is an integer, so converting per call would round `0.004 USD` to zero and a
    thousand such calls would still be zero. Two hundred of them are eighty cents, and that is what
    the meter is told.

    A currency the bridge was not configured for is **not converted** — an exchange rate is policy
    about a tenant's contract, and guessing one would be inventing money. It comes back `None`,
    which the meter reads as *unknown*, with the currency reported so a host can do the sum itself.
    """

    def __init__(self, currency: str = "USD") -> None:
        self.currency = currency
        self.amount = Decimal(0)
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.foreign: dict[str, Decimal] = {}
        self.tokens_seen = False

    def add_tokens(self, usage: Any) -> None:
        if usage is None:
            return
        self.tokens_seen = True
        self.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)

    def add_cost(self, cost: Any) -> None:
        if cost is None:
            return
        amount = Decimal(str(cost.amount))
        if cost.currency == self.currency:
            self.amount += amount
        else:
            self.foreign[cost.currency] = self.foreign.get(cost.currency, Decimal(0)) + amount

    @property
    def cents(self) -> int | None:
        """`None` when nothing priceable arrived, or when it came in a currency we cannot read."""
        if self.foreign:
            return None
        if self.amount == 0:
            return None
        return int((self.amount * 100).to_integral_value())


class BridgeClient(acp.Client):
    """Answers a child agent's requests, having asked our own governance first."""

    def __init__(
        self,
        *,
        workspace: Path | None = None,
        contained: bool = False,
        network: bool = False,
        currency: str = "USD",
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else None
        self._contained = contained
        self._network = network
        self.spend = Spend(currency)
        self.asked: list[tuple[str, str]] = []
        self.refusals: list[str] = []
        self.updates: list[Any] = []

    # ------------------------------------------------------------------ governance

    async def _judge(self, effects: EffectProfile, what: str) -> str | None:
        """`None` means go ahead; a string is the reason it may not.

        Outside a run there is no governance to ask, and the answer to *may this untrusted child
        write to your disk* with nobody to ask is no.
        """
        context = current_run()
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
        effects = opening_a_terminal(contained=self._contained, network=self._network)
        if refused := await self._judge(effects, "create_terminal"):
            raise RequestError(REFUSED, refused)
        raise RequestError(REFUSED, "this bridge grants no terminals yet — Phase 11")

    # The follow-ups are **not re-judged**: the grant was at creation, and asking again for every
    # read of a terminal that was already allowed is noise, not safety. They refuse here only
    # because no terminal is ever created.
    async def terminal_output(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise RequestError(REFUSED, f"no terminal {terminal_id!r}")

    async def wait_for_terminal_exit(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise RequestError(REFUSED, f"no terminal {terminal_id!r}")

    async def kill_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise RequestError(REFUSED, f"no terminal {terminal_id!r}")

    async def release_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        raise RequestError(REFUSED, f"no terminal {terminal_id!r}")

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
        if getattr(update, "session_update", None) == "usage_update":
            self.spend.add_cost(getattr(update, "cost", None))

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
