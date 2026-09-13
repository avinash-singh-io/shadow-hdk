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

from shadow_hdk.kernel.activity import Activity
from shadow_hdk.kernel.components import Interface, Registration, RegistrationId
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.observations import Observation, Proposal
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.kernel.threads import ThreadRecord
from shadow_hdk.kernel.usage import Usage as Usage

"""Re-exported: `Usage` lived here until `events.UsageReported` needed it too, and `ports`
already imports `events`. It moved beneath both rather than breaking every `from ...ports import
Usage`."""

# ---------------------------------------------------------------- model


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: JsonValue


@dataclass(frozen=True)
class Message:
    """One turn in a transcript.

    `tool_calls` is what an **assistant** message asked for, and it is not optional decoration: a
    tool result carries a `tool_call_id`, and every provider rejects a result whose call is in no
    preceding message. Without it the model is also never shown which tool it called with what
    arguments, so its next turn reasons about a step it cannot see.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


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
    reasoning: str = ""
    """What the model thought before it answered, where the provider exposes it (D45). Empty is
    *did not reason* or *did not say*, and no adapter that never heard of the field breaks."""


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
    reasoning: str = ""
    """A delta of thinking, like `text` — the pieces concatenate, never accumulate."""


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
            reasoning=response.reasoning,
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
class ActivityObserver(Protocol):
    """An observer that also hears what is *happening*, beside the record (D63).

    Its own protocol rather than a method on `ObserverPort`, so growing the seam breaks no
    observer (D14): one that only knows `on` is still an `ObserverPort`, hears no activity, and
    works; one that implements this hears it. The emitter checks which it was handed.
    """

    async def on_activity(self, activity: Activity) -> None: ...


@runtime_checkable
class ClockPort(Protocol):
    def now(self) -> str: ...

    def new_id(self) -> str: ...


# ---------------------------------------------------------------- agents


@dataclass(frozen=True)
class ToolSource:
    """Where a provider's tools are — and under D42 they are always **ours**.

    `kind` is an open string for the same reason `Provider.transport` is: teaching this runtime a
    new way to hand a registry over must not change the kernel's contract.
    """

    kind: str
    address: str
    env: tuple[tuple[str, str], ...] = ()
    """What the tool source needs told. A registry served on a loopback port has to hand the port
    to whatever the child launches, and there is nowhere else for it to travel."""


@dataclass(frozen=True)
class Turn:
    """What one turn of an agent provider produced.

    **The tool calls are deliberately absent.** They did not come back through this port; they left
    through the injected registry and landed on the run's own graph, where they were judged,
    charged and recorded (D42). What is here is what only the provider knows: what it said, what it
    spent, and why it stopped.
    """

    text: str = ""
    usage: Usage | None = None
    stop_reason: str = ""
    reasoning: str = ""
    """What the provider's agent thought, where its transport exposes it (D45)."""
    failed: bool = False
    """The provider said this turn did not work.

    Read from what it reported, never inferred from an exit code: these CLIs exit non-zero for
    reasons that are not failures and zero for failures that are. Measured — an expired session
    answers `is_error: true` inside a result whose own subtype still says `success`.
    """


@dataclass(frozen=True)
class TurnChunk:
    """A piece of a turn as it arrives. `text` is the delta, never the accumulation."""

    text: str = ""
    usage: Usage | None = None
    done: bool = False


@runtime_checkable
class AgentSession(Protocol):
    """A provider that owns its own loop, held open across turns.

    Residency is in the contract rather than in one adapter because Phase 4 measured why: a child
    agent is expensive to start, and a five-step composition must not be five cold starts.
    """

    async def turn(self, prompt: str) -> Turn: ...

    async def close(self) -> None: ...

    async def stream(self, prompt: str) -> AsyncIterator[TurnChunk]:
        """Tokens as they arrive — with a default, so growing this port breaks no adapter (D14).

        The same argument as `ModelPort.stream`, one level down: the default calls `turn` and yields
        the whole answer as one chunk, which is honest rather than pretend. A provider that answers
        all at once really does produce one chunk, and this does not chop it into fake deltas to
        look like streaming.
        """
        done = await self.turn(prompt)
        yield TurnChunk(text=done.text, usage=done.usage, done=True)

    async def steer(self, text: str) -> bool:
        """Say something to the agent *while a turn is running* (Codex's `turn/steer`, D63).

        `True` if the provider took it mid-turn; `False` if it cannot, in which case the thread
        keeps the text for the next turn and says so. The default cannot.
        """
        return False

    async def interrupt(self) -> bool:
        """Stop the turn that is running (Codex's `turn/interrupt`). `True` if the provider was
        told and stops on its own; `False` if it cannot be told, in which case the thread ends the
        turn's run and the session is closed. The default cannot be told.
        """
        return False


@runtime_checkable
class Store(Protocol):
    """Where a product's live data lives (D66, principle 10): collections of JSON rows by key,
    and a **version per collection that moves on every write**, so a registry can ask "has
    anything changed?" for the price of one read and reload only when it has. Modes, rules,
    skills, which components are on, providers — each registry takes a store as one more source.
    A product implements it over its own database or takes the shipped sqlite."""

    async def put(self, collection: str, key: str, row: JsonValue) -> None: ...

    async def get(self, collection: str, key: str) -> JsonValue | None: ...

    async def delete(self, collection: str, key: str) -> None: ...

    async def list(self, collection: str) -> tuple[tuple[str, JsonValue], ...]: ...

    async def version(self, collection: str) -> int: ...


@runtime_checkable
class ThreadStore(Protocol):
    """Where threads live (D62). A port, so a product keeps them in its own tables — or does not
    use threads at all and drives turns directly; the runtime never requires one.

    **One thread, one holder** (D81): the store that keeps a thread says who holds it. A hold is
    a lease — a holder's name and a time to live — taken at open, renewed while the thread is
    open, released at close, and lapsed when the process that held it died without releasing.
    The store's own clock decides a lapse: two processes cannot agree on one of theirs.
    """

    async def create(self, thread: ThreadRecord) -> None: ...

    async def get(self, thread_id: str) -> ThreadRecord | None: ...

    async def save(self, thread: ThreadRecord) -> None: ...

    async def list(self, *, include_archived: bool = False) -> tuple[ThreadRecord, ...]: ...

    async def archive(self, thread_id: str) -> None: ...

    async def hold(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        """Take the thread for `holder`, or keep it: `True` when it is free, lapsed, or already
        this holder's; `False` when another holder has it and the hold has not lapsed."""
        ...

    async def renew(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        """Extend a hold this holder has. `False` means it was lost — lapsed and taken."""
        ...

    async def release(self, thread_id: str, holder: str) -> None:
        """Let go, if this holder has it; another's hold is not touched."""
        ...

    async def held_by(self, thread_id: str) -> str | None:
        """Who holds the thread now, or `None` when nobody does or the hold has lapsed."""
        ...


@runtime_checkable
class AgentPort(Protocol):
    """The second provider seam (D39): agency rather than inference.

    One method, because everything else a provider needs to be told — where its tools are, which
    directory it works in — is an argument to it rather than a second call.
    """

    async def open(
        self,
        *,
        tools: tuple[ToolSource, ...] = (),
        workspace: str | None = None,
        behaviour: Behaviour | None = None,
        resume: str | None = None,
    ) -> AgentSession:
        """Open a session. `behaviour` (D64) is who the model should be — mapped to this CLI's
        flags by the provider file; `resume` (D76) is the provider's own session id to pick up
        where it left off — what a thread hands back when it reopens the provider after a mode
        change or a resume, so the agent keeps its memory of the conversation; a default of
        `None` keeps every existing opener working (D14). A session says its id through a
        `session_id` attribute, when the provider has one."""
        ...
