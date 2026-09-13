"""Newline-delimited frames over a byte stream — one implementation (D35's rule applied to
framing): the wire's stdio channel, the recording adapter's pipes and anything else that speaks
one JSON message per line share this, so the edge cases are decided once. A frame is what lies
between newlines; a trailing carriage return is not part of it; a blank line is not a frame; what
is left when the stream ends without a newline is a truncated frame, and the caller says what
that means to it.
"""

from __future__ import annotations


class LineBuffer:
    """Feed chunks in; take complete lines out."""

    def __init__(self) -> None:
        self._pending = b""

    def feed(self, chunk: bytes) -> list[bytes]:
        self._pending += chunk
        lines: list[bytes] = []
        while b"\n" in self._pending:
            line, _, self._pending = self._pending.partition(b"\n")
            line = line.rstrip(b"\r")
            if line.strip():
                lines.append(line)
        return lines

    @property
    def pending(self) -> bytes:
        """Bytes received after the last newline — a frame still arriving."""
        return self._pending

    @property
    def truncated(self) -> bool:
        """Whether the stream ending now would cut a frame in half."""
        return bool(self._pending.strip())


__all__ = ["LineBuffer"]
