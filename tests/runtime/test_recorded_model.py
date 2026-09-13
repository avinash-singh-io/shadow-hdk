"""A run that can be replayed for nothing.

The point is a regression suite that exercises real model behaviour at no cost and with no network:
record once against whatever provider, replay for ever. Which only works if a replay is *honest* —
so the one rule that matters here is that a **miss says so**. A recorded port that quietly fell
through to the live model on a fingerprint it did not know would turn a $0 suite into a bill, and a
determinism test into a coin flip, and neither would be visible.

Consumed **in order**: a fingerprint's answers are replayed one at a time, and asking more times
than were recorded is a miss too. A replay that diverges enough to ask again is a divergence worth
seeing rather than one to paper over by repeating the last answer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.kernel.components import Interface
from shadow_hdk.kernel.ports import Message, ModelRequest, ModelResponse, ToolCall
from shadow_hdk.runtime.replay import RecordedModel, ReplayMiss, Tape
from shadow_hdk.runtime.testing import ScriptedModel

TOOL = Interface(name="search", description="Look it up.", input_schema={"type": "object"})
ALSO = Interface(name="weigh", description="Weigh it.", input_schema={"type": "object"})


def _ask(text: str, tools: tuple[Interface, ...] = (TOOL, ALSO)) -> ModelRequest:
    """Two tools by default, deliberately. With one, sorting the catalogue never compares anything
    and a fingerprint that cannot sort two of them passes every test."""
    return ModelRequest((Message("user", text),), tools)


def _answers() -> list[ModelResponse]:
    return [
        ModelResponse("first", (ToolCall("c1", "search", {"q": "lathe"}),)),
        ModelResponse("second"),
    ]


async def test_recording_passes_the_answer_through_unchanged() -> None:
    """A recorder that changed what came back would be a different kind of thing."""
    inner = ScriptedModel(_answers())
    tape = Tape()
    recorder = RecordedModel(inner, tape)
    first = await recorder.complete(_ask("what is a lathe"))
    assert first == _answers()[0]
    assert len(tape) == 1


async def test_a_replay_makes_no_model_call() -> None:
    """The whole claim. There is no inner port to call, so a call would be an error, not a cost."""
    tape = Tape()
    recorder = RecordedModel(ScriptedModel(_answers()), tape)
    asked = _ask("what is a lathe")
    recorded = await recorder.complete(asked)

    replay = RecordedModel(None, tape)
    assert await replay.complete(asked) == recorded


async def test_a_fingerprint_that_is_not_on_the_tape_is_a_miss_that_says_so() -> None:
    tape = Tape()
    recorder = RecordedModel(ScriptedModel(_answers()), tape)
    await recorder.complete(_ask("what is a lathe"))

    replay = RecordedModel(None, tape)
    with pytest.raises(ReplayMiss) as missed:
        await replay.complete(_ask("what is a milling machine"))
    assert "milling machine" in str(missed.value) or "not on the tape" in str(missed.value)


async def test_a_changed_prompt_is_a_miss_and_not_a_quiet_re_record() -> None:
    """The regression this is for. A tape that silently re-recorded would pass a suite whose
    prompts had drifted, and report the drift as a green run."""
    tape = Tape()
    await RecordedModel(ScriptedModel(_answers()), tape).complete(_ask("what is a lathe"))

    replay = RecordedModel(None, tape)
    with pytest.raises(ReplayMiss):
        await replay.complete(_ask("what is a lathe?"))


async def test_the_tools_offered_are_part_of_the_fingerprint() -> None:
    """Two runs with the same words and different catalogues are not the same run — the model was
    told it could do different things."""
    tape = Tape()
    await RecordedModel(ScriptedModel(_answers()), tape).complete(_ask("what is a lathe"))

    replay = RecordedModel(None, tape)
    with pytest.raises(ReplayMiss):
        await replay.complete(_ask("what is a lathe", tools=()))


async def test_asking_more_times_than_were_recorded_is_a_miss() -> None:
    """Answers are consumed in order. A replay that diverges enough to ask again is a divergence
    worth seeing, not one to paper over by repeating the last answer."""
    tape = Tape()
    recorder = RecordedModel(ScriptedModel(_answers()), tape)
    asked = _ask("what is a lathe")
    await recorder.complete(asked)

    replay = RecordedModel(None, tape)
    await replay.complete(asked)
    with pytest.raises(ReplayMiss):
        await replay.complete(asked)


async def test_the_same_question_asked_twice_replays_both_answers_in_order() -> None:
    tape = Tape()
    recorder = RecordedModel(ScriptedModel(_answers()), tape)
    asked = _ask("what is a lathe")
    await recorder.complete(asked)
    await recorder.complete(asked)

    replay = RecordedModel(None, tape)
    assert [(await replay.complete(asked)).text for _ in range(2)] == ["first", "second"]


def test_a_tape_survives_a_round_trip_through_a_file(tmp_path: Path) -> None:
    """A tape nobody can save is a tape that only replays inside the process that made it."""
    tape = Tape()
    tape.put(_ask("what is a lathe"), _answers()[0])
    written = tmp_path / "tape.json"
    tape.save(written)

    read_back = Tape.load(written)
    assert len(read_back) == 1
    assert read_back.take(_ask("what is a lathe")) == _answers()[0]


async def test_a_whole_agent_run_replays_with_no_model_behind_it() -> None:
    """The headline claim, end to end.

    A real agent loop is recorded against a scripted model, then run again with **no model port at
    all** — the replay-only recorder would raise on any question the tape did not answer. Same
    observations, same order, nothing called.
    """
    from shadow_hdk.adapters.agent import AgentComponent, single
    from shadow_hdk.adapters.basic import AllowAll, CallableComponents
    from shadow_hdk.kernel import (
        Binding,
        Ceiling,
        Composition,
        EffectProfile,
        Floor,
        Invoke,
        Lease,
        Observed,
        ScopeSet,
    )
    from shadow_hdk.runtime import Ports, RunOptions, run
    from shadow_hdk.runtime.testing import FixedClock, ListSink

    def look_up(topic: str) -> str:
        """Look a topic up."""
        return f"what is known about {topic}"

    script = [
        ModelResponse("checking", (ToolCall("t1", "look_up", {"topic": "lathes"}),)),
        ModelResponse("that will do", (ToolCall("t2", "done", {"summary": "looked it up"}),)),
    ]

    async def once(model: RecordedModel) -> list[str]:
        tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
        tools.add(look_up, effects=EffectProfile(reads=ScopeSet.of("workspace")))
        agent = AgentComponent(
            pattern=single,
            effects=EffectProfile(reads=ScopeSet.of("workspace"), costs=True),
            at="2026-01-01T00:00:00+00:00",
        )
        ports = Ports(
            model=model,
            components=(tools, agent),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        )
        composition = Composition(
            (Invoke("a1", "agent", (Binding(name="brief", value="find out about lathes"),)),)
        )
        return [
            f"{event.step}:{event.observation.kind}"
            async for event in run(
                composition,
                ports,
                options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
            )
            if isinstance(event, Observed)
        ]

    tape = Tape()
    recorded = await once(RecordedModel(ScriptedModel(script), tape))
    assert len(tape) == 2, "both turns should be on the tape"

    tape.rewind()
    replayed = await once(RecordedModel(None, tape))
    assert replayed == recorded, "the replay did not produce the run it was recorded from"
