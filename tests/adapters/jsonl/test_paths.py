"""Reading a value out of an event, by the path its provider file names (D40).

The whole of the mapping language, and it is deliberately tiny: dotted keys, and `[]` meaning *each
element of this list*. No expressions, no conditionals, no arithmetic. If a CLI needs more than
this, it needs code — and knowing exactly where that line is, is the point of keeping the language
small enough to state in one sentence.

Every failure is **nothing**, never a raise: a stream is untrusted input from somebody else's
program, and one unexpected event must not end a turn that is otherwise going fine.
"""

from __future__ import annotations

from shadow_hdk.adapters.jsonl.paths import read_at, texts_at

EVENT = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "text", "text": "the lathe"},
            {"type": "text", "text": " weighs 12kg"},
        ],
        "usage": {"input_tokens": 120, "output_tokens": 30},
    },
    "total_cost_usd": 0.0031,
}


def test_a_plain_key() -> None:
    assert read_at(EVENT, "type") == "assistant"


def test_a_dotted_path() -> None:
    assert read_at(EVENT, "message.usage.input_tokens") == 120


def test_a_list_walk_collects_every_element() -> None:
    assert texts_at(EVENT, "message.content[].text") == ["the lathe", " weighs 12kg"]


def test_a_list_walk_skips_an_element_that_has_not_got_it() -> None:
    """A content block of another kind — a tool call, an image — is not text and is not an error."""
    mixed = {"content": [{"type": "tool_use", "id": "t1"}, {"type": "text", "text": "hello"}]}

    assert texts_at(mixed, "content[].text") == ["hello"]


def test_a_path_that_is_not_there_is_nothing() -> None:
    """Untrusted input: an event of an unexpected shape must not end a turn that is going fine."""
    assert read_at(EVENT, "message.nope.deeper") is None
    assert read_at(EVENT, "absent") is None
    assert texts_at(EVENT, "message.content[].absent") == []


def test_an_empty_path_reads_nothing() -> None:
    """A blank field said *do not look*; it must not be read as *the root*."""
    assert read_at(EVENT, "") is None
    assert texts_at(EVENT, "") == []


def test_walking_into_something_that_is_not_a_list_is_nothing() -> None:
    assert texts_at({"content": "not a list"}, "content[].text") == []


def test_walking_into_something_that_is_not_a_mapping_is_nothing() -> None:
    assert read_at({"a": 5}, "a.b") is None
