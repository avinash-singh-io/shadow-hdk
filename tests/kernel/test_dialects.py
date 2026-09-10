"""How to read one CLI's line-delimited JSON, as data (D40).

Claude Code and Codex both answer on stdout as newline-delimited JSON events. They disagree about
every name — which key holds the event type, which type carries assistant text, where the text is,
what ends a turn — and about nothing else. That is the observation this record is built on: the
*shape* is shared and only the *names* differ, so the names belong in the provider file.

**It is deliberately not a query language.** Ten fields, each a literal event name or a dotted path,
and no expressions, no conditionals, no arithmetic. A CLI whose stream does not fit is a CLI that
gets code — the same cut open-design makes with its `streamFormat` enum, except the fields here are
data where theirs are hand-written parsers.

The claim to watch, and the reason two dialects ship rather than one: **if two CLIs this different
fit the same ten fields, the cut is in about the right place.**
"""

from __future__ import annotations

from shadow_hdk.kernel import Dialect


def test_a_dialect_names_where_everything_is() -> None:
    claude = Dialect(
        say_on=("assistant",),
        say_at="message.content[].text",
        done_on=("result",),
        done_at="result",
        failed_at="is_error",
        cost_usd_at="total_cost_usd",
    )

    assert claude.type_key == "type", "the common case is a default, not a required field"
    assert claude.say_at == "message.content[].text"
    assert claude.done_on == ("result",)


def test_a_bare_dialect_reads_nothing_rather_than_guessing() -> None:
    """The conservative default again: a dialect that named no event must not silently match one.
    A stream nobody described is a stream nobody can read, and saying so is better than inventing a
    reading of it."""
    bare = Dialect()

    assert bare.say_on == ()
    assert bare.done_on == ()
    assert bare.say_at == ""
    assert bare.cost_usd_at == ""


def test_a_dialect_is_frozen() -> None:
    import pytest

    with pytest.raises(Exception):  # noqa: B017
        Dialect().type_key = "kind"  # type: ignore[misc]


def test_how_a_turn_is_written_is_part_of_the_dialect() -> None:
    """Claude Code wants a JSON envelope on stdin; a plainer CLI wants the words. Both are the
    dialect's business, because both are a fact about that CLI rather than about this runtime."""
    assert Dialect().prompt_shape == "text"
    assert Dialect(prompt_shape="stream-json-user").prompt_shape == "stream-json-user"
