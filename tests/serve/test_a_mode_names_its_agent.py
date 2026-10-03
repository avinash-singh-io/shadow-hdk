"""A mode names which agent runs it, and an unknown name is refused (D175, D176, phase 64).

A mode already carries *who the model should be* (`behaviour`, D64) and *what it may do* (policy,
plan limits). Which loop runs it is the same kind of fact, so it goes on the mode — and that means a
product switches agent through `set_mode`, a door that already exists and is already governed,
rather than a new ungoverned one. `thread/start {agent}` overrides it for one thread.

**D176: an unknown name is refused, naming it.** Falling back to `single` would hand a product a run
that looks right and is not — the failure `Dialect` refuses for an unknown transport and
`ModeRegistry` refuses for an unknown mode id. Same cut.

The property that matters here is not that a `Pattern` object was selected. It is that **the
selected agent's own system prompt is what the model was actually asked** — which is why there is a
listening model port rather than an assertion on a field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import ModelResponse
from shadow_hdk.kernel.ports import Message
from shadow_hdk.serve import ServeHost, Settings

pytestmark = pytest.mark.anyio

A_REVIEWER = {
    "name": "reviewer",
    "system": "REVIEWER-ROLE: you review a change and say what is wrong with it.",
}


class Listening:
    """A `ModelPort` that keeps every request, so what a model was told is readable."""

    def __init__(self) -> None:
        self.asked: list[Any] = []

    async def complete(self, request: Any) -> ModelResponse:
        self.asked.append(request)
        return ModelResponse(text="done")

    async def stream(self, request: Any) -> Any:  # pragma: no cover
        from shadow_hdk.kernel.ports import ModelChunk

        self.asked.append(request)
        yield ModelChunk(text="done", done=True)

    def system_said(self) -> str:
        return "\n".join(
            m.content
            for r in self.asked
            for m in r.messages
            if isinstance(m, Message) and m.role == "system"
        )


def a_mode(mode_id: str, *, agent: str = "") -> dict[str, Any]:
    document: dict[str, Any] = {"id": mode_id, "policy": "workspace-write"}
    if agent:
        document["agent"] = agent
    return document


async def a_host(
    where: Path, model: Listening, modes: list[dict[str, Any]], agents: list[dict[str, Any]]
) -> ServeHost:
    host = ServeHost(
        Settings(root=where, store=f"sqlite:///{where / 'h.db'}"), model=cast(Any, model)
    )
    for document in modes:
        await host.store.put("modes", document["id"], document)
    for row in agents:
        await host.store.put("agents", row["name"], row)
    return host


async def _one_turn(host: ServeHost, where: Path, mode: str, **kw: Any) -> None:
    thread = await host.open(root=str(where), mode=mode, want=None, name="tools", **kw)
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()


# ------------------------------------------------------------------ a mode names its agent


async def test_a_mode_naming_an_agent_runs_that_agents_role(tmp_path: Path) -> None:
    """The property that matters: the store-backed agent's own system prompt reached the model."""
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("reviewing", agent="reviewer")], [A_REVIEWER])

    await _one_turn(host, tmp_path, "reviewing")

    assert "REVIEWER-ROLE" in model.system_said(), model.system_said()


async def test_a_mode_naming_nothing_still_gets_single(tmp_path: Path) -> None:
    """Nothing that works today moves. Asserted rather than assumed."""
    from shadow_hdk.adapters.agent import single

    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("plain")], [A_REVIEWER])

    await _one_turn(host, tmp_path, "plain")

    said = model.system_said()
    assert single.system[:40] in said, said
    assert "REVIEWER-ROLE" not in said, "an unnamed mode took an agent it never asked for"


async def test_two_modes_run_two_different_agents_on_one_host(tmp_path: Path) -> None:
    """The whole point for a plugin with four agents: one host, one store, a different loop per
    mode — where before, `ServeHost` hardcoded `single` for every thread it ever opened."""
    builder = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}
    model = Listening()
    host = await a_host(
        tmp_path,
        model,
        [a_mode("reviewing", agent="reviewer"), a_mode("building", agent="builder")],
        [A_REVIEWER, builder],
    )

    await _one_turn(host, tmp_path, "reviewing")
    first = model.system_said()
    model.asked.clear()
    await _one_turn(host, tmp_path, "building")
    second = model.system_said()

    assert "REVIEWER-ROLE" in first and "BUILDER-ROLE" not in first
    assert "BUILDER-ROLE" in second and "REVIEWER-ROLE" not in second


# ------------------------------------------------------------------ and a thread may override it


async def test_a_thread_may_name_its_own_agent_over_the_modes(tmp_path: Path) -> None:
    builder = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}
    model = Listening()
    host = await a_host(
        tmp_path, model, [a_mode("reviewing", agent="reviewer")], [A_REVIEWER, builder]
    )

    await _one_turn(host, tmp_path, "reviewing", agent="builder")

    said = model.system_said()
    assert "BUILDER-ROLE" in said and "REVIEWER-ROLE" not in said, said


# ------------------------------------------------------------------ and an unknown name refuses


async def test_an_unknown_agent_on_a_mode_is_refused_naming_it(tmp_path: Path) -> None:
    """D176. A silent fallback to `single` gives a product a run that looks right and is not."""
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("reviewing", agent="nobody")], [A_REVIEWER])

    with pytest.raises(Exception) as refused:  # noqa: PT011 — the type is the kit's to choose
        await _one_turn(host, tmp_path, "reviewing")

    assert "nobody" in str(refused.value), refused.value
    assert model.asked == [], "it must refuse before asking a model anything"


async def test_an_unknown_agent_on_a_thread_is_refused_naming_it(tmp_path: Path) -> None:
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("plain")], [A_REVIEWER])

    with pytest.raises(Exception) as refused:  # noqa: PT011
        await _one_turn(host, tmp_path, "plain", agent="nobody")

    assert "nobody" in str(refused.value), refused.value


async def test_the_refusal_says_what_there_is(tmp_path: Path) -> None:
    """A name that is not there is usually a typo, and the fix is the list."""
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("plain")], [A_REVIEWER])

    with pytest.raises(Exception) as refused:  # noqa: PT011
        await _one_turn(host, tmp_path, "plain", agent="reviewr")

    assert "reviewer" in str(refused.value), f"it must name what is available: {refused.value}"


# ------------------------------------------------------------------ and a handed agent still wins


async def test_an_agent_handed_to_the_host_is_still_honoured(tmp_path: Path) -> None:
    """Existing behaviour, unchanged: a host composing its own provider keeps it, and naming an
    agent on a mode does not silently replace what it handed in."""
    from shadow_hdk.adapters.agent import ModelAgent, single
    from shadow_hdk.adapters.agent.loader import pattern_from

    mine = pattern_from({"name": "mine", "system": "HANDED-ROLE: the host's own."}, where="test")
    model = Listening()
    host = ServeHost(
        Settings(root=tmp_path, store=f"sqlite:///{tmp_path / 'h.db'}"),
        agent=ModelAgent(model=cast(Any, model), pattern=mine),
    )
    await host.store.put("modes", "reviewing", a_mode("reviewing", agent="reviewer"))
    await host.store.put("agents", "reviewer", A_REVIEWER)

    await _one_turn(host, tmp_path, "reviewing")

    said = model.system_said()
    assert "HANDED-ROLE" in said, said
    assert single.system[:40] not in said


# ------------------------------------------------ and the thread says which one it resolved to


async def test_a_thread_records_the_agent_it_resolved_to(tmp_path: Path) -> None:
    """D177. Lane P carries a resolved snapshot — agent, instructions, skills, version, hash — so
    a person's machine can cache by hash. They cannot build one if the kit will not say which
    agent a run resolved to.

    Asserted here, at the host, rather than over the wire: a wire test whose assertion fails hangs
    in this harness (TD-019), so the mutation pass cannot use one.
    """
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("reviewing", agent="reviewer")], [A_REVIEWER])

    thread = await host.open(root=str(tmp_path), mode="reviewing", want=None, name="tools")
    try:
        assert thread.agent == "reviewer"
    finally:
        await thread.close()


async def test_a_thread_naming_nothing_records_single_rather_than_empty(tmp_path: Path) -> None:
    """Empty would read as *we do not know*; `single` is what actually ran."""
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("plain")], [A_REVIEWER])

    thread = await host.open(root=str(tmp_path), mode="plain", want=None, name="tools")
    try:
        assert thread.agent == "single"
    finally:
        await thread.close()


async def test_a_threads_override_is_what_is_recorded(tmp_path: Path) -> None:
    builder = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}
    model = Listening()
    host = await a_host(
        tmp_path, model, [a_mode("reviewing", agent="reviewer")], [A_REVIEWER, builder]
    )

    thread = await host.open(
        root=str(tmp_path), mode="reviewing", want=None, name="tools", agent="builder"
    )
    try:
        assert thread.agent == "builder"
    finally:
        await thread.close()


# ------------------------------------------------ and it survives the doors a product uses (D183)


async def test_switching_mode_switches_the_agent(tmp_path: Path) -> None:
    """BUG-234. Phase 64 shipped selection and left `set_mode` replacing the policy, the
    environment and the behaviour while the agent stayed exactly as it was — so a product switching
    from a Reviewer mode to a Builder mode kept the Reviewer, and the capability was real only for a
    thread that was never switched.

    Asserted on what the model was actually asked, as the rest of this file is.
    """
    builder = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}
    model = Listening()
    host = await a_host(
        tmp_path,
        model,
        [a_mode("reviewing", agent="reviewer"), a_mode("building", agent="builder")],
        [A_REVIEWER, builder],
    )

    thread = await host.open(root=str(tmp_path), mode="reviewing", want=None, name="tools")
    try:
        async for _ in thread.turn("first"):
            pass
        assert "REVIEWER-ROLE" in model.system_said()
        model.asked.clear()

        await thread.set_mode("building")
        async for _ in thread.turn("second"):
            pass
    finally:
        await thread.close()

    said = model.system_said()
    assert "BUILDER-ROLE" in said, said
    assert "REVIEWER-ROLE" not in said, "the switch kept the mode it was leaving"


async def test_the_thread_reports_the_agent_it_switched_to(tmp_path: Path) -> None:
    """D177's field has to keep being true after a switch, or a product's cached snapshot is of a
    run that is no longer happening."""
    builder = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}
    model = Listening()
    host = await a_host(
        tmp_path,
        model,
        [a_mode("reviewing", agent="reviewer"), a_mode("building", agent="builder")],
        [A_REVIEWER, builder],
    )

    thread = await host.open(root=str(tmp_path), mode="reviewing", want=None, name="tools")
    try:
        assert thread.agent == "reviewer"
        await thread.set_mode("building")
        assert thread.agent == "builder", thread.agent
    finally:
        await thread.close()


async def test_a_threads_own_agent_survives_a_mode_switch(tmp_path: Path) -> None:
    """`thread/start {agent}` is an override *for this thread* (D175). One that evaporated at the
    first `set_mode` would be the same defect in a new place."""
    builder = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}
    model = Listening()
    host = await a_host(
        tmp_path,
        model,
        [a_mode("reviewing", agent="reviewer"), a_mode("plain")],
        [A_REVIEWER, builder],
    )

    thread = await host.open(
        root=str(tmp_path), mode="reviewing", want=None, name="tools", agent="builder"
    )
    try:
        await thread.set_mode("plain")
        assert thread.agent == "builder", thread.agent
    finally:
        await thread.close()


async def test_an_unknown_agent_on_the_mode_switched_to_is_refused_naming_it(
    tmp_path: Path,
) -> None:
    """D176 at the other door that selects an agent. A silent fallback to `single` here would hand a
    product a run that looks right and is not, exactly as it would at open."""
    model = Listening()
    host = await a_host(
        tmp_path, model, [a_mode("plain"), a_mode("broken", agent="nobody")], [A_REVIEWER]
    )

    thread = await host.open(root=str(tmp_path), mode="plain", want=None, name="tools")
    try:
        with pytest.raises(Exception) as refused:  # noqa: PT011 — the type is the kit's to choose
            await thread.set_mode("broken")
        assert "nobody" in str(refused.value), refused.value
    finally:
        await thread.close()


async def test_a_resumed_thread_runs_the_agent_it_was_running(tmp_path: Path) -> None:
    """BUG-234's other half. `ThreadRecord` had no `agent`, so a resume fell through to the host's
    default and a Reviewer thread came back as `single` — while `thread.agent` reported `single`,
    truthfully, about a run that was supposed to be a Reviewer."""
    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("reviewing", agent="reviewer")], [A_REVIEWER])

    thread = await host.open(root=str(tmp_path), mode="reviewing", want=None, name="tools")
    thread_id = thread.id
    await thread.close()

    again = await host.resume(thread_id)
    try:
        assert again.agent == "reviewer", again.agent
        async for _ in again.turn("after the resume"):
            pass
    finally:
        await again.close()

    assert "REVIEWER-ROLE" in model.system_said(), model.system_said()


async def test_a_resumed_thread_that_named_no_agent_still_gets_single(tmp_path: Path) -> None:
    """Nothing that works today moves."""
    from shadow_hdk.adapters.agent import single

    model = Listening()
    host = await a_host(tmp_path, model, [a_mode("plain")], [A_REVIEWER])

    thread = await host.open(root=str(tmp_path), mode="plain", want=None, name="tools")
    thread_id = thread.id
    await thread.close()

    again = await host.resume(thread_id)
    try:
        assert again.agent == "single", again.agent
        async for _ in again.turn("go"):
            pass
    finally:
        await again.close()

    said = model.system_said()
    assert single.system[:40] in said, said
    assert "REVIEWER-ROLE" not in said
