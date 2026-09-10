"""Stopping a run from outside it (D15).

`Cancelled` and `EndReason("cancelled")` have existed since Phase 0 with nothing raising either.
What was missing was never the class but the answer to *who asks, and where the question is asked*.

A run already stops for reasons of exactly one shape: the executor asks, before it spends a step,
whether it may. The lease is asked that at the top of `invoke`. This is the same question from a
different asker — the host rather than the budget — so it is asked in the same place, and asked
**first**, because a cancelled run should not spend the step it was about to be refused for.

Two things this deliberately is not:

* **not a port.** A port is what the host implements *for* the runtime. This is the host reaching
  *in*, which is what `Lease` already is; as a port the runtime would poll the host every step for
  a value the host already holds.
* **not `task.cancel()`.** That works and says nothing — no `Ended`, no reason, no record, and a
  component halfway through a write cut in half. Cancellation lands on a step boundary: whatever is
  already running is left to finish, and the next step does not start.
"""

from __future__ import annotations

from shadow_hdk.runtime.errors import Cancelled

DEFAULT_REASON = "cancelled by the host"


class Cancellation:
    """A handle the host keeps. Passed in `RunOptions`, inherited by children unless replaced."""

    __slots__ = ("_reason",)

    def __init__(self) -> None:
        self._reason: str | None = None

    def cancel(self, reason: str = DEFAULT_REASON) -> None:
        """Ask the run to stop. Idempotent: the first reason is the one that is recorded."""
        if self._reason is None:
            self._reason = reason or DEFAULT_REASON

    @property
    def cancelled(self) -> bool:
        return self._reason is not None

    @property
    def reason(self) -> str | None:
        return self._reason

    def check(self) -> None:
        """Raise if the host has asked to stop. Called where the lease is checked."""
        if self._reason is not None:
            raise Cancelled(self._reason)


__all__ = ["Cancellation", "DEFAULT_REASON"]
