"""A run that can be replayed for nothing.

Record once against whatever provider; replay for ever, with no network and no bill. That is what
makes a regression suite over *real* model behaviour affordable, and it is the same trick the
`spikes` use to argue a shape on a $0 replay rather than in production.

It only works if a replay is **honest**, so the rule that matters most here is the one about
misses. A recorded port that quietly fell through to the live model on a fingerprint it did not
know would turn a free suite into a bill and a determinism test into a coin flip, and neither would
be visible in a green run. So: no inner port means no call is possible, and a fingerprint that is
not on the tape raises.

Answers are consumed **in order**. Asking a question more times than it was recorded is a miss too —
a replay that diverges enough to ask again is a divergence worth seeing, not one to paper over by
repeating the last answer.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.ports import ModelChunk, ModelPort, ModelRequest, ModelResponse


class ReplayMiss(LookupError):
    """A question the tape does not answer. Deliberately loud."""


def fingerprint(request: ModelRequest) -> str:
    """What makes two requests the same question.

    Everything the model was told: the messages, **the tools it was offered**, and the model name.
    The catalogue is in here on purpose — two runs with the same words and different tools are not
    the same run, because the model was told it could do different things.
    """
    canonical = {
        "messages": [
            {"role": m.role, "content": m.content, "tool_call_id": m.tool_call_id}
            for m in request.messages
        ],
        # Sorted as **text**, not as parsed objects: two dicts have no order, and sorting them
        # raises the moment a request offers more than one tool. Every unit test here offered
        # exactly one, so `sorted` never compared anything and the bug only surfaced when a real
        # agent run went through with a catalogue.
        "tools": sorted(dump(interface, type(interface)) for interface in request.tools),
        "model": request.model,
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class Tape:
    """Fingerprints to the answers they got, in the order they got them."""

    def __init__(self, answers: dict[str, list[ModelResponse]] | None = None) -> None:
        self._answers: dict[str, list[ModelResponse]] = answers or {}
        self._taken: dict[str, int] = {}

    def __len__(self) -> int:
        return sum(len(answers) for answers in self._answers.values())

    def put(self, request: ModelRequest, response: ModelResponse) -> None:
        self._answers.setdefault(fingerprint(request), []).append(response)

    def take(self, request: ModelRequest) -> ModelResponse | None:
        """The next answer to this question, or `None` if there is not one."""
        key = fingerprint(request)
        answers = self._answers.get(key)
        if answers is None:
            return None
        index = self._taken.get(key, 0)
        if index >= len(answers):
            return None
        self._taken[key] = index + 1
        return answers[index]

    def rewind(self) -> None:
        """Start the tape again. A second replay of the same run is the same replay."""
        self._taken.clear()

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                {
                    key: [json.loads(dump(answer, ModelResponse)) for answer in answers]
                    for key, answers in self._answers.items()
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> Tape:
        raw: dict[str, list[Any]] = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            {
                key: [load(json.dumps(answer), ModelResponse) for answer in answers]
                for key, answers in raw.items()
            }
        )


class RecordedModel(ModelPort):
    """A model port with a tape behind it.

    With an `inner` port it **records**: every request goes through and is appended to the tape.
    Without one it **replays**, and cannot call a model at all — which is the design rather than a
    convenience, because a tape that has drifted out of date should fail loudly instead of quietly
    costing money.

    There is deliberately no third mode that replays what it knows and records what it does not. It
    is the obvious convenience and it is exactly the danger above: a run that half-replayed would
    report a green suite while calling a provider for the other half.
    """

    def __init__(self, inner: ModelPort | None, tape: Tape) -> None:
        self.inner = inner
        self.tape = tape

    async def complete(self, request: ModelRequest) -> ModelResponse:
        # Two modes, not a fallback. **Recording always calls through**, even for a question already
        # on the tape: the first version read the tape first, and a run that asked the same thing
        # twice recorded one answer and replayed it as the second — a tape that quietly disagreed
        # with the run it claimed to be of. And a replay never calls at all, which is what makes a
        # stale tape fail loudly instead of quietly costing money.
        if self.inner is not None:
            answer = await self.inner.complete(request)
            self.tape.put(request, answer)
            return answer
        recorded = self.tape.take(request)
        if recorded is None:
            raise ReplayMiss(
                f"not on the tape: {_first_words(request)} "
                f"(fingerprint {fingerprint(request)[:12]})"
            )
        return recorded

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]:
        """One chunk, from the tape. A recording of a stream is a recording of what it *said* —
        the timing is not on the tape and pretending otherwise would be a different lie."""
        response = await self.complete(request)
        yield ModelChunk(
            text=response.text,
            tool_calls=response.tool_calls,
            usage=response.usage,
            done=True,
        )


def _first_words(request: ModelRequest) -> str:
    """Enough of the question for a person to recognise it in a failure."""
    last = request.messages[-1].content if request.messages else ""
    return f"{last[:60]}…" if len(last) > 60 else last


__all__ = ["RecordedModel", "ReplayMiss", "Tape", "fingerprint"]
