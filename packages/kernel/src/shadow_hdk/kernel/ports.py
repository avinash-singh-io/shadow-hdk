"""The six ports — the seams a host or an adapter plugs into (09 §3, §7).

Every argument and return is a frozen dataclass that round-trips through JSON, which is what makes
a service form of the runtime a composition root later rather than a rewrite. The runtime must
never know: any product's schema, what a proposal *means*, where events go, whether a human is on
the other end of ``ask``, what a mode is.

The six, as read from 09 (models · components · governance · sink · events, plus the one
non-determinism the runtime has, time and identity, behind a port so a replay costs $0):

    ModelPort       complete(request) -> response        what thinks
    ComponentPort   registrations() · invoke(id, inputs) what can be invoked, and invoking it
    GovernancePort  judge(effects, context) -> judgement may this step run: Allow | Ask | Refuse
    SinkPort        propose(proposal)                    where results go; the host decides
    ObserverPort    on(event)                            the only channel out; fire-and-forget
    ClockPort       now() · new_id()                     so two runs of the same inputs compare

Six is the starting set, not a ceiling (09 §3). A port is added the way an effect field or a
step kind is: a kernel change with an ADR and a minor version, and a default the runtime applies
when a host does not implement it — refuse the steps that need it, never crash. A host or adapter
that ignores a new port keeps working.

Sandboxes have no port of their own: a sandbox is an adapter that registers a component with
``contained: true`` (09 §5), and it is absent on deployments that have none.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import Field, JsonValue

from shadow_hdk.kernel.components import Interface, Registration, RegistrationId
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.observations import Observation, Proposal

# ---------------------------------------------------------------- model


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: JsonValue


@dataclass(frozen=True)
class Usage:
    """What the call cost. A model adapter that cannot say reports ``None`` for the field it does
    not know — *unknown*, never zero (10 §5 R2)."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cents: int | None = None


@dataclass(frozen=True)
class ModelRequest:
    messages: tuple[Message, ...]
    tools: tuple[Interface, ...] = ()
    model: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage | None = None


@dataclass(frozen=True)
class ModelChunk:
    """A piece of an answer as it arrives.

    ``text`` is the **delta**, never the accumulation: concatenating every chunk's text gives what
    `complete` would have returned. ``usage`` arrives on the last chunk, because what a call cost
    cannot be known until it ends.
    """

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage | None = None
    done: bool = False


@runtime_checkable
class ModelPort(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse: ...

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]:
        """Tokens as they arrive — with a default, so growing this port broke no adapter (D14).

        `09` §3 gives a **port** a refuse-not-crash default when it is added. A *method* added to an
        existing port follows the same rule one level down: this implementation calls `complete` and
        yields the whole answer as one chunk. That is honest rather than pretend — a provider that
        answers all at once really does produce one chunk, and the default does not chop it into
        fake deltas to look like streaming. An adapter that can do better overrides it.
        """
        response = await self.complete(request)
        yield ModelChunk(
            text=response.text,
            tool_calls=response.tool_calls,
            usage=response.usage,
            done=True,
        )


# ---------------------------------------------------------------- components


@runtime_checkable
class ComponentPort(Protocol):
    """One adapter's worth of components — an MCP server, a CLI, a set of callables, another
    agent. The registry is the union of every component port, recomputed every step."""

    async def registrations(self) -> Sequence[Registration]: ...

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation: ...


# ---------------------------------------------------------------- governance


@dataclass(frozen=True)
class Context:
    """Opaque to the runtime. A product's adapter interprets it; the runtime only carries it."""

    run_id: str
    step: str
    principal: str | None = None
    attributes: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class Allow:
    kind: Literal["allow"] = "allow"


@dataclass(frozen=True)
class Ask:
    question: str
    kind: Literal["ask"] = "ask"


@dataclass(frozen=True)
class Refuse:
    reason: str
    kind: Literal["refuse"] = "refuse"


Judgement = Annotated[Allow | Ask | Refuse, Field(discriminator="kind")]


@runtime_checkable
class GovernancePort(Protocol):
    """One function, called before every step. A product supplies the policy; the runtime
    supplies the enforcement point."""

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement: ...


# ---------------------------------------------------------------- sink, observer, clock


@runtime_checkable
class SinkPort(Protocol):
    async def propose(self, proposal: Proposal) -> None: ...


@runtime_checkable
class ObserverPort(Protocol):
    async def on(self, event: Event) -> None: ...


@runtime_checkable
class ClockPort(Protocol):
    def now(self) -> str: ...

    def new_id(self) -> str: ...
