"""A named agent is validated everywhere, and one the kit cannot run is reported (H11-A, phase 66).

Two defects, one cause. `ServeHost._agent_named` returned early whenever the host had no model —
which is every CLI host — and the D176 refusal lived on the line *after* that return:

    if self._handed_agent is not None or self._model is None:
        return None
    pattern = await self.patterns.named(wanted) if wanted else single

So **on Claude Code or Codex a mode naming `"reviewr"` was accepted in silence.** D176 says an
unknown agent name is refused at open, naming what exists; that was true on a key-backed host and
false on a CLI, which is a claim the kit makes and does not keep.

And **nothing said the agent had been dropped.** `agent_recorded(wanted, chosen=False)` records
`""`, which the contract defines as *no agent applies* — honest about the kit's choice, silent about
the product's request. A product that set an agent and got the CLI's own loop had no field to read.
That is the shape of ENH-051 and BUG-229 both: the kit drops what a mode asked for and the honesty
field says nothing.

The decisions are pure functions so they can be mutation-checked without standing up a `ServeHost`,
which hangs on a failing assertion in this harness (TD-019).
"""

from __future__ import annotations

import pytest

from shadow_hdk.adapters.agent.patterns import agent_recorded, agent_unhonoured

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------ what was dropped, named


def test_a_name_the_kit_could_not_run_is_named() -> None:
    """The whole of the reporting half: a product reads back the name it asked for."""
    assert agent_unhonoured("reviewer", chosen=False) == "reviewer"


def test_a_name_the_kit_did_run_is_not_named() -> None:
    """Paired, so the field cannot pass by naming everything."""
    assert agent_unhonoured("reviewer", chosen=True) == ""


def test_asking_for_nothing_drops_nothing() -> None:
    """A composition that named no agent is not owed a report about one. This is every thread
    written before phase 64, and most threads after it."""
    assert agent_unhonoured("", chosen=False) == ""
    assert agent_unhonoured("", chosen=True) == ""


def test_it_is_the_counterpart_of_what_was_recorded() -> None:
    """`agent` says what ran and this says what could not. Exactly one of them is ever set, because
    a product reading both must never have to work out which it believes."""
    for wanted, chosen in (("reviewer", True), ("reviewer", False), ("", True), ("", False)):
        ran = agent_recorded(wanted, chosen=chosen)
        dropped = agent_unhonoured(wanted, chosen=chosen)
        assert not (ran and dropped), f"both set for {wanted!r}/{chosen}: {ran!r} and {dropped!r}"


# ------------------------- and the record carries it, so a resume reports the same thing


def test_the_record_has_somewhere_to_put_it() -> None:
    from shadow_hdk.kernel.threads import ThreadRecord

    record = ThreadRecord(id="t", root="/tmp", created_at="x", agent_unhonoured="reviewer")

    assert record.agent_unhonoured == "reviewer"
    assert ThreadRecord(id="t", root="/tmp", created_at="x").agent_unhonoured == ""


# ------------------------- and a CLI host validates the name, which it never used to


async def test_a_host_with_no_model_still_refuses_an_unknown_agent(tmp_path: object) -> None:
    """The defect, through the door it lived in. A host with no model is every CLI host, and the
    early return used to come **before** `patterns.named`, so D176's refusal never ran there.

    Asserted on `_agent_named` directly rather than through a whole thread: the refusal is the
    property, and a failing test that stands up a `ServeHost` hangs in this harness (TD-019).
    """
    from shadow_hdk.adapters.agent.patterns import NoSuchAgent
    from shadow_hdk.serve import ServeHost, Settings

    host = ServeHost(Settings(root=tmp_path, store=f"sqlite:///{tmp_path}/h.db"))  # type: ignore[arg-type]
    await host.store.put("agents", "reviewer", {"name": "reviewer", "system": "ROLE"})
    try:
        assert host._model is None, "this host must have no model for the test to mean anything"  # noqa: SLF001

        with pytest.raises(NoSuchAgent) as refused:
            await host._agent_named("reviewr")  # noqa: SLF001

        assert "reviewr" in str(refused.value)
        assert "reviewer" in str(refused.value), "it must still name what there is"
    finally:
        await host.aclose()


async def test_a_host_with_no_model_accepts_a_name_that_exists_and_runs_none_of_it(
    tmp_path: object,
) -> None:
    """Paired: the validation must not have become a refusal of everything. A real name resolves,
    and `None` still comes back because a CLI provider owns its own loop."""
    from shadow_hdk.serve import ServeHost, Settings

    host = ServeHost(Settings(root=tmp_path, store=f"sqlite:///{tmp_path}/h.db"))  # type: ignore[arg-type]
    await host.store.put("agents", "reviewer", {"name": "reviewer", "system": "ROLE"})
    try:
        assert await host._agent_named("reviewer") is None  # noqa: SLF001
        assert await host._agent_named("") is None  # noqa: SLF001
    finally:
        await host.aclose()


async def test_a_thread_reports_the_agent_it_could_not_run(tmp_path: object) -> None:
    """Through the field a product actually reads. Without this the record carries it and nothing
    surfaces it — which is how the original defect worked."""
    from typing import Any, cast

    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.kernel import Ceiling, Floor, Lease, Turn
    from shadow_hdk.runtime import Ports
    from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread

    class Cli:
        async def open(self, **kw: Any) -> Any:
            return self

        async def turn(self, prompt: str) -> Turn:
            return Turn(text="done")

        async def close(self) -> None:
            return None

        async def stream(self, prompt: str) -> Any:  # pragma: no cover
            raise NotImplementedError

    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, Cli()),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=store,
        root=cast(Any, tmp_path),
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        agent_unhonoured="reviewer",
    )
    try:
        assert thread.agent_unhonoured == "reviewer", thread.agent_unhonoured
        assert thread.agent == "", "exactly one of the two is ever set"
        saved = await store.get(thread.id)
    finally:
        await thread.close()

    assert saved is not None and saved.agent_unhonoured == "reviewer", saved


async def test_a_thread_that_got_what_it_asked_for_reports_nothing(tmp_path: object) -> None:
    """Paired, so the field cannot pass by always carrying a name."""
    from typing import Any, cast

    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.kernel import Ceiling, Floor, Lease, Turn
    from shadow_hdk.runtime import Ports
    from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread

    class Cli:
        async def open(self, **kw: Any) -> Any:
            return self

        async def turn(self, prompt: str) -> Turn:
            return Turn(text="done")

        async def close(self) -> None:
            return None

        async def stream(self, prompt: str) -> Any:  # pragma: no cover
            raise NotImplementedError

    thread = await Thread.open(
        agent=cast(Any, Cli()),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=cast(Any, tmp_path),
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        agent_named="reviewer",
    )
    try:
        assert thread.agent == "reviewer"
        assert thread.agent_unhonoured == ""
    finally:
        await thread.close()
