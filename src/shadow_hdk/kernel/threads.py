"""A thread: the durable container every product has, in the words every product uses (D62).

Codex, OpenAI and LangGraph call it a thread; ACP and Claude Code a session. A thread holds
**turns**; each turn is one **run** — one execution under a lease, with the record that run
already keeps — so Thread → Turn → Item is Thread → Run → Step with nothing invented (D62; the
OpenAI Assistants API's own shape). The thread is resumable, forkable, listable and archivable
through a `ThreadStore` a host may implement over its own tables or not use at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import JsonValue

from shadow_hdk.kernel.capabilities import ExecutionRequirements
from shadow_hdk.kernel.leases import Ceiling
from shadow_hdk.kernel.workspace import Root

ThreadId = str
TurnId = str

RECORD_VERSION = 3
"""The shape of `ThreadRecord` as this kit writes it: 1 was every record before 0.28.0; 2 added
pending, identity, budget, spend and `version`; 3 keeps accepted execution requirements. A record
read without the field is 1 and every later field defaults, so old records still load."""


@dataclass(frozen=True)
class TurnRecord:
    """One turn as the thread remembers it: what was asked, which run did the work, how it ended."""

    id: TurnId
    run_id: str
    prompt: str
    at: str
    outcome: Literal["running", "completed", "failed", "refused", "cancelled", "parked"] = "running"
    """`parked`: the host went away while a question of this turn was open (D80); the question is
    on the thread's `pending` until it is settled, and the turn stays `parked` — the agent's
    transcript cannot be rewound, so the outcome is told to it at the next turn, not rewritten."""
    text: str = ""
    """What the agent said back — the turn's own answer, kept here so a host lists a thread
    without replaying every run."""


@dataclass(frozen=True)
class Spent:
    """What a thread has spent across its turns (D84): the meter's counters, kept on the record
    so a resumed thread starts from them. `unpriced` says a model call nobody could price is in
    the total — cents is then a floor, not the amount."""

    steps: int = 0
    seconds: float = 0.0
    """The turns' running time (D90): a thread sitting open spends nothing."""
    cents: int = 0
    unpriced: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    """Tokens counted across the turns (D90) — a subscription's own measure."""
    unmetered: bool = False
    """A model call reported no tokens: the counts are a floor, never the amount."""


@dataclass(frozen=True)
class PendingQuestion:
    """A question of a turn nobody has answered yet, on the record so it survives the process
    that asked it (D80): an approval the policy asked for — with the run that parked on it, which
    a new host resumes from the checkpointer — or the agent's own question to the person."""

    handle: str
    turn: TurnId
    step: str
    question: str
    kind: Literal["approval", "input"] = "approval"
    component: str | None = None
    inputs: JsonValue | None = None
    run_id: str = ""
    """The run parked on this question — a child of the turn's run — when there is one to resume;
    an input question has none, its answer is text the agent is told."""


@dataclass(frozen=True)
class ThreadRecord:
    """The container. `turns` is the order; `forked_from` and `seeded_turns` say where a fork or a
    rollback came from, because a provider's own transcript cannot be rewound and the new thread's
    first turn is seeded with the kept turns — the record says so rather than pretending."""

    id: ThreadId
    root: str
    """The primary root's path — what a one-root reader expects; `roots` is the whole workspace."""
    created_at: str
    mode: str = ""
    provider: str = ""
    turns: tuple[TurnRecord, ...] = field(default_factory=tuple)
    archived: bool = False
    forked_from: ThreadId | None = None
    seeded_turns: int = 0
    session_id: str = ""
    """The provider's own session id, when it has one — what a resume hands back to it."""
    roots: tuple[Root, ...] = ()
    """The workspace (D76): one or many roots, the first the primary. Empty means the one root
    `root` names — a record written before roots were kept."""
    environment: str = ""
    """The environment's own mode — what the sandbox enforces — beside `mode`, the policy's."""
    pending: tuple[PendingQuestion, ...] = ()
    """The questions open right now (D80): put here when asked, taken off when answered — by the
    process that asked, or by the one that resumed the thread after it."""
    principal: str = ""
    """Who the thread is for (D82): the product's name for the person — on every judgement's
    context, and what a rule made at this thread's card is scoped to. Empty: nobody named."""
    attributes: dict[str, JsonValue] = field(default_factory=dict)
    """The product's words about the thread (D82) — a tenant, a workspace id — on every
    judgement's context beside the runtime's own keys, where a rule's or a mode's `scope` reads
    them."""
    budget: Ceiling | None = None
    """This thread's own ceiling (D84) — steps, seconds, cents — over the host's default when it
    was opened with one; `None` means the host's default, which is not repeated here."""
    spent: Spent = field(default_factory=Spent)
    """What the thread has spent (D84), saved at the end of every turn; `remaining` is the
    budget less this, however many times the thread is resumed."""
    requirements: ExecutionRequirements = field(default_factory=ExecutionRequirements)
    """The execution properties accepted when this thread opened, kept so a resume rechecks them
    instead of silently falling back to the host's current defaults."""
    version: int = 1
    """The shape this record was written with (D93): `RECORD_VERSION` for this kit's writes, 1
    for a record from before the field existed. A product mapping the record to columns reads
    it before it reads the rest."""


__all__ = [
    "RECORD_VERSION",
    "PendingQuestion",
    "Spent",
    "ThreadId",
    "ThreadRecord",
    "TurnId",
    "TurnRecord",
]
