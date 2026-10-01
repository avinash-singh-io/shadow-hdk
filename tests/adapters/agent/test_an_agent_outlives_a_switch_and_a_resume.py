"""A selected agent survives a mode switch and a resume (D183, phase 65, BUG-234).

Phase 64 made an agent selectable per mode (D175), refused an unknown name (D176) and put the
resolved one on the thread (D177) — and shipped it in 0.43.0. Neither door a product actually uses
carried it:

* `set_mode` replaced mode, environment and behaviour and **never re-resolved the agent**, so
  switching from a Reviewer mode to a Builder mode kept the Reviewer.
* `ThreadRecord` had no `agent` field, so a resumed thread silently took the host's default.

The capability was therefore real only for a thread opened once, never switched and never resumed,
which is not how a product runs. That is mine, from phase 64, and it bounds what 0.43.0 delivered.

The decisions are pinned as **pure functions** on purpose: a failing test that stands up a
`ServeHost` hangs in this harness (TD-019), so the mutation pass cannot use one. The host-level
tests in `tests/serve/test_a_mode_names_its_agent.py` are behavioural coverage; they are not what
proves these assertions bite.
"""

from __future__ import annotations

import pytest

from shadow_hdk.adapters.agent.patterns import agent_now, agent_to_resume

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------ which agent runs now


def test_a_mode_that_names_an_agent_gets_it() -> None:
    assert agent_now("", "reviewer") == "reviewer"


def test_a_threads_own_override_survives_a_mode_switch() -> None:
    """`thread/start {agent}` is *an override for this thread* (D175). A switch that dropped it
    would make the override evaporate at the first `set_mode` — the same class of bug as the mode's
    own agent not being read, and a product cannot see either happen.
    """
    assert agent_now("builder", "reviewer") == "builder"


def test_a_mode_naming_nothing_runs_nothing_in_particular() -> None:
    """Which `agent_recorded` then reads as `single`. Empty here rather than `single`, because this
    answers *what was asked for*, and nothing was."""
    assert agent_now("", "") == ""


def test_an_override_with_no_mode_agent_is_still_the_override() -> None:
    assert agent_now("builder", "") == "builder"


# ------------------------------------------------------------------ and which one a resume restores


def test_a_resume_runs_the_agent_the_record_says_it_was_running() -> None:
    """D183. Before this a resumed thread fell through to the host's default, so a Reviewer thread
    came back as `single` — and `thread.agent` then reported `single`, truthfully, about a run that
    was supposed to be a Reviewer."""
    assert agent_to_resume("reviewer") == "reviewer"


def test_a_record_that_names_no_agent_resumes_on_nothing_in_particular() -> None:
    """Every thread written before phase 64, and every thread on a CLI provider."""
    assert agent_to_resume("") == ""


def test_a_record_that_recorded_single_resumes_on_single() -> None:
    """`single` on the record is not *we do not know* — `agent_recorded` writes it precisely so
    that absence and the default can be told apart (D177). So it is honoured, not second-guessed."""
    assert agent_to_resume("single") == "single"


# ------------------------------------------- the record carries it, which makes it durable


def test_the_record_has_somewhere_to_put_the_agent() -> None:
    from shadow_hdk.kernel.threads import ThreadRecord

    record = ThreadRecord(id="t1", root="/tmp", created_at="2026-10-02T00:00:00+00:00")

    assert record.agent == "", "a record that names no agent is every record written before this"


def test_a_record_keeps_the_agent_it_was_given() -> None:
    from shadow_hdk.kernel.threads import ThreadRecord

    record = ThreadRecord(
        id="t1", root="/tmp", created_at="2026-10-02T00:00:00+00:00", agent="reviewer"
    )

    assert record.agent == "reviewer"


# ------------------------------- and the thread asks again, without a host in the way (TD-019)


class _Double:
    """A provider double, so the switch can be observed without a `ServeHost` — a failing test that
    stands one up hangs in this harness (TD-019), and a hang proves nothing."""

    def __init__(self, label: str = "first") -> None:
        self.label = label
        self.opened: list[str] = []

    async def open(self, **kw: object) -> object:
        self.opened.append(self.label)
        return self

    async def turn(self, prompt: str) -> object:
        from shadow_hdk.kernel import Turn

        return Turn(text=f"{self.label} answered")

    async def close(self) -> None:
        return None

    async def stream(self, prompt: str) -> object:  # pragma: no cover
        raise NotImplementedError


async def _a_thread(
    root: object, modes: object, mode: str, chooser: object, **kw: object
) -> object:
    from typing import Any, cast

    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.kernel import Ceiling, Floor, Lease
    from shadow_hdk.runtime import Ports
    from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread

    return await Thread.open(
        agent=cast(Any, _Double()),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=cast(Any, root),
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=modes,
        mode=mode,
        choose_agent=chooser,
        **cast(Any, kw),
    )


async def test_a_mode_switch_asks_for_the_new_modes_agent(tmp_path: object) -> None:
    """The wiring, which is what makes `agent_now` more than an arithmetic exercise."""
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec

    asked: list[str] = []

    async def chooser(wanted: str) -> tuple[object, str]:
        asked.append(wanted)
        return _Double(wanted), wanted or "single"

    modes = ModeRegistry(
        (ModeSpec.of("reviewing", agent="reviewer"), ModeSpec.of("building", agent="builder"))
    )
    thread = await _a_thread(tmp_path, modes, "reviewing", chooser, agent_named="reviewer")
    try:
        await thread.set_mode("building")  # type: ignore[attr-defined]

        assert asked == ["builder"], asked
        assert thread.agent == "builder", thread.agent  # type: ignore[attr-defined]
    finally:
        await thread.close()  # type: ignore[attr-defined]


async def test_a_switch_keeps_the_threads_own_override(tmp_path: object) -> None:
    """The override and the new mode's agent must **differ**, or the test cannot tell which one won.

    The first version switched into a mode that named the same agent as the override, so a
    mutation dropping the override entirely passed — the mode's own name happened to be the right
    answer. Here the mode asks for `reviewer` and the override says `builder`, and `builder` is
    what must be asked for.
    """
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec

    asked: list[str] = []

    async def chooser(wanted: str) -> tuple[object, str]:
        asked.append(wanted)
        return _Double(wanted), wanted or "single"

    modes = ModeRegistry((ModeSpec.of("plain"), ModeSpec.of("reviewing", agent="reviewer")))
    thread = await _a_thread(
        tmp_path,
        modes,
        "plain",
        chooser,
        agent_named="builder",
        agent_override="builder",
    )
    try:
        await thread.set_mode("reviewing")  # type: ignore[attr-defined]

        assert asked == ["builder"], f"the mode's own agent overrode the thread's: {asked}"
        assert thread.agent == "builder"  # type: ignore[attr-defined]
    finally:
        await thread.close()  # type: ignore[attr-defined]


async def test_the_agent_a_thread_opened_with_is_on_its_record(tmp_path: object) -> None:
    """The foundation the resume stands on: if `Thread.open` does not put the resolved name on the
    record, nothing downstream can restore it however well it reads it."""
    thread = await _a_thread(tmp_path, None, "", None, agent_named="reviewer")
    store = thread._store  # type: ignore[attr-defined] # noqa: SLF001 — the record is the point
    try:
        assert thread.agent == "reviewer"  # type: ignore[attr-defined]
        saved = await store.get(thread.id)  # type: ignore[attr-defined]
    finally:
        await thread.close()  # type: ignore[attr-defined]

    assert saved is not None and saved.agent == "reviewer", saved


async def test_a_thread_opened_naming_no_agent_records_none(tmp_path: object) -> None:
    thread = await _a_thread(tmp_path, None, "", None)
    try:
        assert thread.agent == ""  # type: ignore[attr-defined]
    finally:
        await thread.close()  # type: ignore[attr-defined]


async def test_the_new_agent_is_on_the_record_so_a_resume_finds_it(tmp_path: object) -> None:
    """A switch that updated the live object and not the record would be forgotten by the next
    resume, which is BUG-234 in a new place."""
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec

    async def chooser(wanted: str) -> tuple[object, str]:
        return _Double(wanted), wanted or "single"

    modes = ModeRegistry(
        (ModeSpec.of("reviewing", agent="reviewer"), ModeSpec.of("building", agent="builder"))
    )
    thread = await _a_thread(tmp_path, modes, "reviewing", chooser, agent_named="reviewer")
    store = thread._store  # type: ignore[attr-defined] # noqa: SLF001 — the record is the point
    try:
        await thread.set_mode("building")  # type: ignore[attr-defined]
        saved = await store.get(thread.id)  # type: ignore[attr-defined]
    finally:
        await thread.close()  # type: ignore[attr-defined]

    assert saved is not None and saved.agent == "builder", saved


async def test_a_composition_offering_no_chooser_is_unchanged(tmp_path: object) -> None:
    """Every composition that does not select agents — which is every one written before phase 64 —
    passes no chooser, and `set_mode` must behave exactly as it did."""
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec

    modes = ModeRegistry((ModeSpec.of("one"), ModeSpec.of("two")))
    thread = await _a_thread(tmp_path, modes, "one", None)
    try:
        await thread.set_mode("two")  # type: ignore[attr-defined]

        assert thread.agent == ""  # type: ignore[attr-defined]
    finally:
        await thread.close()  # type: ignore[attr-defined]


async def test_a_resumed_thread_keeps_knowing_it_had_an_override(tmp_path: object) -> None:
    """`agent` says what is running; `agent_override` says why. Without the second, a `set_mode`
    after a restart would quietly follow the new mode while the same switch before the restart kept
    the override — the same inconsistency BUG-234 was, one door further along.

    Found by a surviving mutation on the field's initial value: nothing read it, because `open`
    always overwrote it and `resume` never set it at all.
    """
    from typing import Any, cast

    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
    from shadow_hdk.kernel import Ceiling, Floor, Lease
    from shadow_hdk.runtime import Ports
    from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread

    asked: list[str] = []

    async def chooser(wanted: str) -> tuple[object, str]:
        asked.append(wanted)
        return _Double(wanted), wanted or "single"

    def _ports() -> Ports:
        return Ports(
            model=None,
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        )

    store = InMemoryThreads()
    modes = ModeRegistry((ModeSpec.of("plain"), ModeSpec.of("reviewing", agent="reviewer")))
    thread = await Thread.open(
        agent=cast(Any, _Double()),
        ports=_ports(),
        store=store,
        root=cast(Any, tmp_path),
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=modes,
        mode="plain",
        choose_agent=chooser,
        agent_named="builder",
        agent_override="builder",
    )
    thread_id = thread.id
    await thread.close()

    again = await Thread.resume(
        thread_id,
        agent=cast(Any, _Double()),
        ports=_ports(),
        store=store,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=modes,
        choose_agent=chooser,
    )
    try:
        await again.set_mode("reviewing")

        assert asked == ["builder"], f"the resumed thread forgot its override: {asked}"
        assert again.agent == "builder", again.agent
    finally:
        await again.close()
