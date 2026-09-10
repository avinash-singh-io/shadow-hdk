"""Reading a value out of an event by the path a provider file names.

The whole of the mapping language: dotted keys, and `[]` meaning *each element of this list*. No
expressions, no conditionals, no arithmetic. Small enough to state in one sentence, which is the
point — it makes the line between *a file* and *code* obvious rather than arguable.

**Every failure is nothing, never a raise.** These events are untrusted input from somebody else's
program: a CLI that adds a field, drops one, or emits a shape nobody expected must not end a turn
that is otherwise going fine.
"""

from __future__ import annotations

from typing import Any


def read_at(event: Any, path: str) -> Any:
    """One value, or `None`.

    An empty path reads nothing rather than the root: a dialect that left the field blank said *do
    not look*, and reading the whole event instead would put an entire JSON object where a string
    was expected.
    """
    if not path:
        return None
    here: Any = event
    for part in path.split("."):
        if not isinstance(here, dict) or part not in here:
            return None
        here = here[part]
    return here


def texts_at(event: Any, path: str) -> list[str]:
    """Every string a `[]` path reaches, in order.

    An element that has not got the field is skipped rather than counted as empty — a content block
    of another kind (a tool call, an image) is not text, and a blank in its place would put gaps in
    what the agent is recorded as having said.
    """
    if not path:
        return []
    if "[]" not in path:
        found = read_at(event, path)
        return [found] if isinstance(found, str) else []

    before, after = path.split("[]", 1)
    items = read_at(event, before.rstrip(".")) if before.rstrip(".") else event
    if not isinstance(items, list):
        return []
    rest = after.lstrip(".")
    found: list[str] = []
    for item in items:
        value = read_at(item, rest) if rest else item
        if isinstance(value, str):
            found.append(value)
    return found


__all__ = ["read_at", "texts_at"]
