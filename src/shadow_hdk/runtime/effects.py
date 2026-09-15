"""Append-only effect histories and the act-time transaction (D99-D104)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import JsonValue

from shadow_hdk.kernel.authority import (
    AuthoritySnapshot,
    EffectAuthorization,
    EffectEntry,
    EffectEntryKind,
    StagedEffect,
)
from shadow_hdk.kernel.ports import (
    AuthorityPort,
    AuthorizerPort,
    EffectJournalPort,
    Refuse,
)


class EffectClock(Protocol):
    """The deliberately small slice of time an effect transaction needs."""

    def now(self) -> str: ...


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

    @property
    def kind(self) -> str:
        return self.status


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
    """One local coordinator over host ports; the journal remains the cross-process authority."""

    def __init__(
        self,
        *,
        authority: AuthorityPort,
        authorizer: AuthorizerPort,
        journal: EffectJournalPort,
        clock: EffectClock,
        checkpoint: Callable[[str], None] | None = None,
    ) -> None:
        self.authority = authority
        self.authorizer = authorizer
        self.journal = journal
        self.clock = clock
        self.checkpoint = checkpoint
        self._locks: dict[str, asyncio.Lock] = {}

    async def execute(
        self,
        effect: StagedEffect,
        *,
        invoke: Callable[[], Awaitable[JsonValue]],
        expected_authority: AuthoritySnapshot | None = None,
    ) -> EffectState:
        lock = self._locks.setdefault(effect.idempotency_key, asyncio.Lock())
        async with lock:
            existing = await self.journal.read(effect.idempotency_key)
            if existing:
                return fold_effect(existing)

            expected = expected_authority or await self.authority.current(
                run_id=effect.run_id, step=effect.step
            )
            await self._append(effect, "staged")
            self._checkpoint("staged")
            if expected.digest != effect.authority_digest:
                return await self._refuse(effect, 1, "authority_changed")

            decision = await self.authorizer.authorize(effect, expected)
            if isinstance(decision, Refuse):
                return await self._refuse(effect, 1, decision.reason)
            await self._append(
                effect,
                "authorized",
                sequence=1,
                authorization_id=decision.authorization_id,
            )
            self._checkpoint("authorized")

            current = await self.authority.current(run_id=effect.run_id, step=effect.step)
            reason = _grant_refusal(decision, effect, expected, current, self.clock.now())
            if reason is not None:
                return await self._refuse(effect, 2, reason)

            await self._append(
                effect,
                "executing",
                sequence=2,
                authorization_id=decision.authorization_id,
            )
            self._checkpoint("executing")
            try:
                receipt = await invoke()
                self._checkpoint("invoked")
            except Exception as error:  # noqa: BLE001 — an effect failure is journal data
                await self._append(
                    effect,
                    "failed",
                    sequence=3,
                    authorization_id=decision.authorization_id,
                    detail={"reason": _described(error)},
                )
                return fold_effect(await self.journal.read(effect.idempotency_key))
            await self._append(
                effect,
                "receipt",
                sequence=3,
                authorization_id=decision.authorization_id,
                detail=receipt,
            )
            return fold_effect(await self.journal.read(effect.idempotency_key))

    async def _append(
        self,
        effect: StagedEffect,
        kind: EffectEntryKind,
        *,
        sequence: int = 0,
        authorization_id: str | None = None,
        detail: JsonValue = None,
    ) -> None:
        await self.journal.append(
            EffectEntry(
                attempt_id=effect.idempotency_key,
                sequence=sequence,
                kind=kind,
                stage_digest=effect.digest,
                at=self.clock.now(),
                authorization_id=authorization_id,
                detail=detail,
            ),
            expected_length=sequence,
        )

    async def _refuse(self, effect: StagedEffect, sequence: int, reason: str) -> EffectState:
        await self._append(effect, "refused", sequence=sequence, detail={"reason": reason})
        return fold_effect(await self.journal.read(effect.idempotency_key))

    def _checkpoint(self, point: str) -> None:
        if self.checkpoint is not None:
            self.checkpoint(point)


async def recover_effect(
    effect: StagedEffect,
    *,
    journal: EffectJournalPort,
    clock: EffectClock,
    idempotent: bool,
    reconcile: Callable[[str], Awaitable[JsonValue | None]] | None = None,
) -> EffectState:
    history = await journal.read(effect.idempotency_key)
    state = fold_effect(history)
    if state.status in {"receipt", "refused", "failed", "reconciled"}:
        return state
    if state.status in {"staged", "authorized"}:
        await journal.append(
            EffectEntry(
                effect.idempotency_key,
                len(history),
                "refused",
                effect.digest,
                clock.now(),
                detail={"reason": "abandoned_before_execution"},
            ),
            expected_length=len(history),
        )
        return fold_effect(await journal.read(effect.idempotency_key))
    if state.status == "executing":
        await journal.append(
            EffectEntry(
                effect.idempotency_key,
                len(history),
                "unknown",
                effect.digest,
                clock.now(),
                authorization_id=state.authorization_id,
                detail={"reason": "outcome_unknown_after_execution_started"},
            ),
            expected_length=len(history),
        )
        history = await journal.read(effect.idempotency_key)
        state = fold_effect(history)
    if state.status == "unknown" and idempotent and reconcile is not None:
        receipt = await reconcile(effect.idempotency_key)
        if receipt is not None:
            await journal.append(
                EffectEntry(
                    effect.idempotency_key,
                    len(history),
                    "reconciled",
                    effect.digest,
                    clock.now(),
                    authorization_id=state.authorization_id,
                    detail=receipt,
                ),
                expected_length=len(history),
            )
            return fold_effect(await journal.read(effect.idempotency_key))
    return state


def _grant_refusal(
    grant: EffectAuthorization,
    effect: StagedEffect,
    expected: AuthoritySnapshot,
    current: AuthoritySnapshot,
    now: str,
) -> str | None:
    if current.digest != expected.digest:
        return "authority_changed"
    if not grant.permits(effect, current):
        return "authorization_invalid"
    try:
        if datetime.fromisoformat(grant.expires_at) <= datetime.fromisoformat(now):
            return "authorization_expired"
    except ValueError:
        return "authorization_invalid"
    return None


def _described(error: Exception) -> str:
    text = str(error).strip()
    return f"{type(error).__name__}: {text}" if text else type(error).__name__


__all__ = [
    "EffectState",
    "EffectTransaction",
    "InMemoryEffectJournal",
    "JournalConflict",
    "TransactionCrash",
    "fold_effect",
    "recover_effect",
]
