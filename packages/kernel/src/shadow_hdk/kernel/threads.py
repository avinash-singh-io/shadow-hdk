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

ThreadId = str
TurnId = str


@dataclass(frozen=True)
class TurnRecord:
    """One turn as the thread remembers it: what was asked, which run did the work, how it ended."""

    id: TurnId
    run_id: str
    prompt: str
    at: str
    outcome: Literal["running", "completed", "failed", "refused", "cancelled", "parked"] = "running"
    text: str = ""
    """What the agent said back — the turn's own answer, kept here so a host lists a thread
    without replaying every run."""


@dataclass(frozen=True)
class ThreadRecord:
    """The container. `turns` is the order; `forked_from` and `seeded_turns` say where a fork or a
    rollback came from, because a provider's own transcript cannot be rewound and the new thread's
    first turn is seeded with the kept turns — the record says so rather than pretending."""

    id: ThreadId
    root: str
    created_at: str
    mode: str = ""
    provider: str = ""
    turns: tuple[TurnRecord, ...] = field(default_factory=tuple)
    archived: bool = False
    forked_from: ThreadId | None = None
    seeded_turns: int = 0
    session_id: str = ""
    """The provider's own session id, when it has one — what a resume hands back to it."""


__all__ = ["ThreadId", "ThreadRecord", "TurnId", "TurnRecord"]
