"""A key-backed thread's second turn contains its first (D181, phase 65, BUG-232).

`AgentSession.work` opened every turn with `self.messages = [Message("system", role),
Message("user", brief)]`, and `_ModelSession._turn` built a fresh `_Turnwise` each time. So turn two
did not contain turn one: ask *what did I just ask you* and the model could not know.

What makes it a defect rather than a limitation is that **nothing said so**. A CLI-backed thread
does not have the problem — the CLI keeps its own session — so the kit's behaviour differed by
provider
with nothing in the contract, the docs or `unmapped_behaviour` naming it. A product could not tell a
forgetful thread from a forgetful model.

D181: the transcript is the **thread's**, not the turn's. The system message is still rebuilt every
turn, because a `set_mode` may have changed who the model is, and an accumulated pile of stale roles
is its own bug.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import Ceiling, Floor, Lease, ModelResponse, ScopeSet
from shadow_hdk.kernel.ports import Message
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")


class Listening:
    """A `ModelPort` that keeps every request, so the transcript it was handed is readable."""

    def __init__(self, answers: list[str] | None = None) -> None:
        self.asked: list[Any] = []
        self.answers = list(answers or [])

    def _say(self) -> str:
        return self.answers.pop(0) if self.answers else "done"

    async def complete(self, request: Any) -> ModelResponse:
        self.asked.append(request)
        return ModelResponse(text=self._say())

    async def stream(self, request: Any) -> Any:  # pragma: no cover — complete is enough
        from shadow_hdk.kernel.ports import ModelChunk

        self.asked.append(request)
        yield ModelChunk(text=self._say(), done=True)

    def last(self) -> tuple[Message, ...]:
        return tuple(self.asked[-1].messages)

    def roles_of_last(self) -> list[str]:
        return [m.role for m in self.last()]

    def words_of_last(self) -> str:
        return "\n".join(m.content for m in self.last())


async def a_thread(root: Path, model: Listening, *modes: ModeSpec) -> Thread:
    from shadow_hdk.adapters.agent import ModelAgent, single

    return await Thread.open(
        agent=ModelAgent(model=cast(Any, model), pattern=single),
        ports=Ports(
            model=cast(Any, model),
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=root,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=ModeRegistry(modes) if modes else None,
        mode=modes[0].id if modes else "",
    )


async def _say(thread: Thread, words: str) -> None:
    async for _ in thread.turn(words):
        pass


# ------------------------------------------------------------------ it remembers


async def test_a_second_turn_contains_the_first(tmp_path: Path) -> None:
    """The whole of BUG-232, as a product would see it."""
    model = Listening(["the capital is Paris"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "what is the capital of France?")
        await _say(thread, "and what did I just ask you?")
    finally:
        await thread.close()

    whole = model.words_of_last()
    assert "capital of France" in whole, f"the first question is not in the second turn: {whole!r}"
    assert "the capital is Paris" in whole, f"the first answer is not either: {whole!r}"


async def test_the_third_turn_contains_both(tmp_path: Path) -> None:
    """Not merely the previous one: the transcript is the thread's."""
    model = Listening(["first answer", "second answer"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "question one")
        await _say(thread, "question two")
        await _say(thread, "question three")
    finally:
        await thread.close()

    whole = model.words_of_last()
    for expected in ("question one", "first answer", "question two", "second answer"):
        assert expected in whole, f"{expected!r} missing from turn three: {whole!r}"


async def test_the_turns_are_in_the_order_they_happened(tmp_path: Path) -> None:
    """A transcript out of order is worse than none — a model reads it as the conversation."""
    model = Listening(["answer one", "answer two"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "first question")
        await _say(thread, "second question")
        await _say(thread, "third question")
    finally:
        await thread.close()

    whole = model.words_of_last()
    assert (
        whole.index("first question")
        < whole.index("answer one")
        < whole.index("second question")
        < whole.index("answer two")
        < whole.index("third question")
    ), whole


# ------------------------------------------------------------------ and the role is not piled up


async def test_there_is_exactly_one_system_message_however_many_turns(tmp_path: Path) -> None:
    """Carrying the whole of the last turn's list would carry its system message too, and a model
    handed three roles is being told three different things about who it is."""
    model = Listening(["a", "b"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "one")
        await _say(thread, "two")
        await _say(thread, "three")
    finally:
        await thread.close()

    assert model.roles_of_last().count("system") == 1, model.roles_of_last()


async def test_the_system_message_is_the_first_thing_the_model_reads(tmp_path: Path) -> None:
    model = Listening(["a"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "one")
        await _say(thread, "two")
    finally:
        await thread.close()

    assert model.roles_of_last()[0] == "system", model.roles_of_last()


async def test_a_mode_switch_replaces_the_role_and_keeps_the_transcript(tmp_path: Path) -> None:
    """D181 with D175: who the model is may change mid-thread; what was said did not stop being
    said. The old role must be gone and the old words must still be there."""
    model = Listening(["first answer"])
    thread = await a_thread(
        tmp_path,
        model,
        ModeSpec.of("early", behaviour=Behaviour(system="EARLY-ROLE: be terse.")),
        ModeSpec.of("later", behaviour=Behaviour(system="LATER-ROLE: be thorough.")),
    )
    try:
        await _say(thread, "a question")
        await thread.set_mode("later")
        await _say(thread, "another question")
    finally:
        await thread.close()

    whole = model.words_of_last()
    assert "LATER-ROLE" in whole, whole
    assert "EARLY-ROLE" not in whole, "a stale role was carried into the new mode"
    assert "a question" in whole, "the transcript did not survive the mode switch"


# ------------------------------------------------------------------ and a first turn is unchanged


async def test_a_first_turn_is_exactly_the_system_message_and_the_prompt(tmp_path: Path) -> None:
    """Nothing that works today moves. A fresh thread's first request is what it always was."""
    model = Listening(["a"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "the only thing said")
    finally:
        await thread.close()

    assert model.roles_of_last() == ["system", "user"], model.roles_of_last()
    assert model.last()[1].content == "the only thing said"


async def test_a_fork_is_not_told_its_transcript_twice(tmp_path: Path) -> None:
    """A fork already seeds its first turn from the record (`seeded_turns`, D139). If the carried
    transcript also arrived, every kept turn would be in the request twice."""
    model = Listening(["an answer"])
    thread = await a_thread(tmp_path, model)
    try:
        await _say(thread, "the original question")
    finally:
        await thread.close()

    whole = model.words_of_last()
    assert whole.count("the original question") == 1, whole


# ------------------------------------------------ and compaction still keeps the role and the brief


async def test_a_compaction_on_a_later_turn_keeps_this_turns_request(tmp_path: Path) -> None:
    """`_compact` kept `messages[:2]` — *the role and the brief, because `work()` puts them first
    and in that order*. With the thread's earlier turns between them (D181) that slice is the role
    and the **oldest carried message**, so the request the model is answering would be summarised
    away while a stale one was kept. The position is recorded now rather than assumed.

    This is the test that makes the fix real: without it a mutation restoring `messages[:2]`
    survives, because no other test compacts a turn that has a transcript behind it.
    """
    from shadow_hdk.adapters.agent import COMPACT, ModelAgent, Pattern
    from shadow_hdk.kernel.ports import ModelResponse as Answer
    from shadow_hdk.kernel.ports import ToolCall

    class Scripted:
        """Answers from a script, and keeps every request."""

        def __init__(self, answers: list[Answer]) -> None:
            self.answers = list(answers)
            self.asked: list[Any] = []

        async def complete(self, request: Any) -> Answer:
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else Answer("done")

        async def stream(self, request: Any) -> Any:  # pragma: no cover
            from shadow_hdk.kernel.ports import ModelChunk

            self.asked.append(request)
            answer = self.answers.pop(0) if self.answers else Answer("done")
            yield ModelChunk(text=answer.text, tool_calls=answer.tool_calls, done=True)

    tidy = Pattern(
        name="tidy", system="TIDY-ROLE", meta_tools=frozenset({COMPACT, "propose", "done"})
    )
    model = Scripted(
        [
            Answer("answering the first"),  # turn one ends
            Answer("tidying", (ToolCall("c1", COMPACT, {"summary": "what went before"}),)),
            Answer("answering the second"),  # turn two, after the compaction
        ]
    )
    thread = await Thread.open(
        agent=ModelAgent(model=cast(Any, model), pattern=tidy),
        ports=Ports(
            model=cast(Any, model),
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )
    try:
        await _say(thread, "THE-FIRST-QUESTION")
        await _say(thread, "THE-SECOND-QUESTION")
    finally:
        await thread.close()

    after = "\n".join(m.content for m in model.asked[-1].messages)
    assert "THE-SECOND-QUESTION" in after, (
        f"the request this turn is answering was summarised away: {after!r}"
    )
    assert "what went before" in after, f"the summary is not in what it carries: {after!r}"
    assert "THE-FIRST-QUESTION" not in after, (
        "a compaction that keeps the whole carried transcript has saved nothing"
    )
