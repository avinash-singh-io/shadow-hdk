"""What a call cost.

Its own module because two things need it and one of them cannot import the other: `ports.Message`
and friends describe a model call, and `events.UsageReported` records what one cost — and
`ports` already imports `events` for `ObserverPort`. A value type shared by both belongs beneath
both.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    """What the call cost. A model adapter that cannot say reports ``None`` for the field it does
    not know — *unknown*, never zero (10 §5 R2)."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cents: int | None = None


__all__ = ["Usage"]
