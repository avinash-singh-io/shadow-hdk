"""Append-only effect histories and the act-time transaction (D99-D104)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import JsonValue

from shadow_hdk.kernel.authority import EffectEntry, StagedEffect
from shadow_hdk.kernel.ports import AuthorityPort, AuthorizerPort, ClockPort, EffectJournalPort


class JournalConflict(RuntimeError):
    """The expected tail moved, a transition is illegal, or a grant was already consumed."""


class TransactionCrash(BaseException):
    """Deterministic test injector standing in for process loss at a named boundary."""


@dataclass(frozen=True)
class EffectState:
    status: str
    receipt: JsonValue = None
    reason: str | None = None
    authorization_id: str | None = None


_NEXT: dict[str | None, frozenset[str]] = {
    None: frozenset({"staged"}),
    "staged": frozenset({"authorized", "refused"}),
    "authorized": frozenset({"executing", "refused"}),
    "executing": frozenset({"receipt", "failed", "unknown"}),
    "unknown": frozenset({"reconciled"}),
    "receipt": frozenset(),
    "refused": frozenset(),
    "failed": frozenset(),
    "reconciled": frozenset(),
}


def fold_effect(entries: tuple[EffectEntry, ...]) -> EffectState:
    """Validate and fold facts; the fold never repairs or reorders history."""
    previous: str | None = None
    attempt: str | None = None
    stage: str | None = None
    receipt: JsonValue = None
    reason: str | None = None
    authorization_id: str | None = None
    for expected, entry in enumerate(entries):
        if entry.sequence != expected:
            raise ValueError(f"effect sequence {entry.sequence} is not the expected {expected}")
        if attempt is not None and entry.attempt_id != attempt:
            raise ValueError("one effect history cannot contain another attempt")
        if stage is not None and entry.stage_digest != stage:
            raise ValueError("one effect history cannot change its staged digest")
        if entry.kind not in _NEXT.get(previous, frozenset()):
            raise ValueError(f"illegal effect transition {previous!r} -> {entry.kind!r}")
        attempt = entry.attempt_id
        stage = entry.stage_digest
        previous = entry.kind
        if entry.authorization_id is not None:
            authorization_id = entry.authorization_id
        if entry.kind in {"receipt", "reconciled"}:
            receipt = entry.detail
        if entry.kind in {"refused", "failed", "unknown"}:
            if isinstance(entry.detail, dict):
                found = entry.detail.get("reason")
                reason = found if isinstance(found, str) else entry.kind
            elif isinstance(entry.detail, str):
                reason = entry.detail
            else:
                reason = entry.kind
    return EffectState(
        status=previous or "empty",
        receipt=receipt,
        reason=reason,
        authorization_id=authorization_id,
    )


class InMemoryEffectJournal(EffectJournalPort):
    """The reference journal: process-local, atomic under one asyncio lock."""

    def __init__(self) -> None:
        self._entries: dict[str, list[EffectEntry]] = {}
        self._authorizations: set[str] = set()
        self._lock = asyncio.Lock()

    async def read(self, attempt_id: str) -> tuple[EffectEntry, ...]:
        async with self._lock:
            return tuple(self._entries.get(attempt_id, ()))

    async def append(self, entry: EffectEntry, *, expected_length: int) -> None:
        async with self._lock:
            current = self._entries.get(entry.attempt_id, [])
            if len(current) != expected_length:
                raise JournalConflict(
                    f"effect history moved from expected length {expected_length} to {len(current)}"
                )
            if (
                entry.kind == "authorized"
                and entry.authorization_id is not None
                and entry.authorization_id in self._authorizations
            ):
                raise JournalConflict("effect authorization was already consumed")
            try:
                fold_effect((*current, entry))
            except ValueError as error:
                raise JournalConflict(str(error)) from error
            self._entries.setdefault(entry.attempt_id, []).append(entry)
            if entry.kind == "authorized" and entry.authorization_id is not None:
                self._authorizations.add(entry.authorization_id)


class EffectTransaction:
    """Implemented by Group 3; declared now so the frozen evaluator can collect."""

    def __init__(
        self,
        *,
        authority: AuthorityPort,
        authorizer: AuthorizerPort,
        journal: EffectJournalPort,
        clock: ClockPort,
        checkpoint: Callable[[str], None] | None = None,
    ) -> None:
        self.authority = authority
        self.authorizer = authorizer
        self.journal = journal
        self.clock = clock
        self.checkpoint = checkpoint

    async def execute(
        self, effect: StagedEffect, *, invoke: Callable[[], Awaitable[JsonValue]]
    ) -> EffectState:
        raise NotImplementedError


async def recover_effect(
    effect: StagedEffect,
    *,
    journal: EffectJournalPort,
    clock: ClockPort,
    idempotent: bool,
    reconcile: Callable[[str], Awaitable[JsonValue | None]] | None = None,
) -> EffectState:
    raise NotImplementedError


__all__ = [
    "EffectState",
    "EffectTransaction",
    "InMemoryEffectJournal",
    "JournalConflict",
    "TransactionCrash",
    "fold_effect",
    "recover_effect",
]
