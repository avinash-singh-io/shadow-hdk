"""Activity: what is *happening*, beside the record of what *happened* (principle 6, D63).

A token of thinking as it streams, a token of text, a line a running command just printed,
"composing a tool call" — the things a person watches a run do in real time. None of it is the
record: the record is durable, complete and replayable, and a thousand deltas per turn would make
it noise. Activity is ephemeral — delivered to the observer if one is listening, bounded and
dropped-oldest if the observer is slow, never checkpointed, never required for correctness.

The kinds are open. Four are named because every product renders them; a host may emit its own.
"""

from __future__ import annotations

from dataclasses import dataclass

THINKING = "thinking"
"""A delta of the model's reasoning, as it streams."""
TEXT = "text"
"""A delta of the model's answer, as it streams."""
OUTPUT = "output"
"""A chunk a running command printed, as it printed it."""
COMPOSING = "composing"
"""The model is composing a tool call; nothing has arrived whole yet."""


@dataclass(frozen=True)
class Activity:
    run_id: str
    step: str
    kind: str
    text: str
    at: str


__all__ = ["COMPOSING", "OUTPUT", "TEXT", "THINKING", "Activity"]
