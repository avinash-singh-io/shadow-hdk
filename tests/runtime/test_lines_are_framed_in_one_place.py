"""Newline-delimited frames over a byte stream have one implementation (`runtime.lines`), used
by the wire's stdio channel and the recording adapter's pipes — the two places that each carried
their own buffer-and-split loop, which is a rule with two implementations waiting to differ
(one skipped blank lines, one did not).
"""

from __future__ import annotations

from shadow_hdk.runtime.lines import LineBuffer


def test_lines_arrive_whole_whatever_the_chunking() -> None:
    buffer = LineBuffer()
    assert buffer.feed(b'{"a":') == []
    assert buffer.feed(b' 1}\n{"b": 2}\n{"c"') == [b'{"a": 1}', b'{"b": 2}']
    assert buffer.pending == b'{"c"'
    assert buffer.feed(b": 3}\n") == [b'{"c": 3}']
    assert buffer.pending == b""


def test_blank_lines_are_not_frames() -> None:
    buffer = LineBuffer()
    assert buffer.feed(b"\n\n  \n{}\n") == [b"{}"]


def test_a_trailing_newline_is_the_frame_boundary_not_part_of_the_frame() -> None:
    buffer = LineBuffer()
    assert buffer.feed(b"x\r\n") == [b"x"], "a CR before the LF is stripped too"


def test_what_is_left_at_end_of_stream_is_a_truncated_frame() -> None:
    buffer = LineBuffer()
    buffer.feed(b'{"half":')
    assert buffer.pending == b'{"half":'
    assert buffer.truncated is True
    assert LineBuffer().truncated is False
