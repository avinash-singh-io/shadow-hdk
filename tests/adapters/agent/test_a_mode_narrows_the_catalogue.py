"""A mode's `tools_offered` narrows the catalogue a key-backed model is handed (D178/D179, BUG-230).

The kernel derivation is pinned in `tests/kernel/test_a_mode_narrows_what_a_step_is_shown.py`. What
is pinned here is the property that actually matters to a product: **the model was handed a shorter
list**, asserted against the request it received rather than against a field on an object.

Deliberately on `Thread.open` with `InMemoryComponents` rather than on a `ServeHost`: a failing test
that stands up a host hangs in this harness (TD-019), so a mutation pass could not use one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    EffectProfile,
    Floor,
    Lease,
    ModelResponse,
    ScopeSet,
)
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
OURS = {"read_it", "write_it", "run_it"}
"""The registrations this harness offers — what a narrowing may take away."""

READ = make_registration("read_it", effects=EffectProfile(reads=WORKSPACE))
WRITE = make_registration("write_it", effects=EffectProfile(writes=WORKSPACE))
RUN = make_registration("run_it", effects=EffectProfile(reads=WORKSPACE, reaches=True))


async def _nothing(_inputs: Any) -> Completed:
    return Completed({"ok": True})


class Listening:
    """A `ModelPort` that keeps every request, so the catalogue it was handed is readable."""

    def __init__(self) -> None:
        self.asked: list[Any] = []

    async def complete(self, request: Any) -> ModelResponse:
        self.asked.append(request)
        return ModelResponse(text="done")

    async def stream(self, request: Any) -> Any:  # pragma: no cover — complete is enough
        from shadow_hdk.kernel.ports import ModelChunk

        self.asked.append(request)
        yield ModelChunk(text="done", done=True)

    def shown(self) -> list[str]:
        """Every name the model was shown, verbs included."""
        return [interface.name for request in self.asked for interface in request.tools]

    def offered(self) -> list[str]:
        """The *registered* names it was shown. The loop's own verbs — `done`, `propose` — are the
        pattern's and never a mode's to narrow, so they are not what a narrowing is about; they get
        a test of their own below."""
        return [name for name in self.shown() if name in OURS]


async def a_thread(root: Path, model: Listening, behaviour: Behaviour | None) -> Thread:
    from shadow_hdk.adapters.agent import ModelAgent, single

    modes = ModeRegistry((ModeSpec.of("narrowed", behaviour=behaviour),))
    return await Thread.open(
        agent=ModelAgent(model=cast(Any, model), pattern=single),
        ports=Ports(
            model=cast(Any, model),
            components=(
                InMemoryComponents([(READ, _nothing), (WRITE, _nothing), (RUN, _nothing)]),
            ),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=root,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        modes=modes,
        mode="narrowed",
    )


async def _one_turn(thread: Thread) -> None:
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()


# ------------------------------------------------------------------ it narrows


async def test_a_narrowing_mode_hands_the_model_a_shorter_catalogue(tmp_path: Path) -> None:
    """The whole of BUG-230, as a product would see it."""
    model = Listening()
    await _one_turn(await a_thread(tmp_path, model, Behaviour(tools_offered=("read_it",))))

    assert model.offered() == ["read_it"], model.offered()


async def test_the_tools_left_out_are_genuinely_absent_not_merely_last(tmp_path: Path) -> None:
    """Paired against the unnarrowed run so this cannot pass because the registry was empty."""
    wide, narrow = Listening(), Listening()
    await _one_turn(await a_thread(tmp_path, wide, None))
    await _one_turn(await a_thread(tmp_path, narrow, Behaviour(tools_offered=("run_it",))))

    assert sorted(wide.offered()) == ["read_it", "run_it", "write_it"], wide.offered()
    assert narrow.offered() == ["run_it"], narrow.offered()


async def test_a_mode_naming_nothing_is_offered_everything(tmp_path: Path) -> None:
    """Nothing that works today moves. Asserted rather than assumed."""
    model = Listening()
    await _one_turn(await a_thread(tmp_path, model, Behaviour(system="be brief")))

    assert sorted(model.offered()) == ["read_it", "run_it", "write_it"], model.offered()


async def test_narrowing_cannot_widen_past_the_registry(tmp_path: Path) -> None:
    """D178: applied last, so a name the run does not have is not conjured by asking for it."""
    model = Listening()
    await _one_turn(
        await a_thread(tmp_path, model, Behaviour(tools_offered=("read_it", "write_it")))
    )

    assert sorted(model.offered()) == ["read_it", "write_it"], model.offered()


# ------------------------------------------------------------------ and an unknown name refuses


async def _refusal_of(thread: Thread) -> str:
    """What a run's one failure says. A narrowing nothing answers to raises out of `catalogue()`,
    which the runtime records as `Failed` (D7) — so the words land on the observation, not on a
    text event, and that is where a product reads them."""
    errors: list[str] = []
    try:
        async for event in thread.turn("go"):
            observation = getattr(event, "observation", None)
            error = getattr(observation, "error", "")
            if error:
                errors.append(str(error))
    finally:
        await thread.close()
    return "\n".join(errors)


async def test_a_name_nothing_answers_to_refuses_the_turn_naming_it(tmp_path: Path) -> None:
    """D179. A typo that silently narrows nothing is the failure this closes — the turn must not
    quietly run wide with the tool the mode meant to name missing."""
    model = Listening()
    said = await _refusal_of(
        await a_thread(tmp_path, model, Behaviour(tools_offered=("read_it", "reed_it")))
    )

    assert "reed_it" in said, f"the refusal must name the name nothing answers to: {said!r}"
    assert model.asked == [], "it must refuse before asking a model anything"


async def test_the_refusal_says_what_the_run_does_offer(tmp_path: Path) -> None:
    """A name that is not there is usually a typo, and the fix is the list."""
    said = await _refusal_of(
        await a_thread(tmp_path, Listening(), Behaviour(tools_offered=("reed_it",)))
    )

    assert "read_it" in said, f"it must name what the run actually offers: {said!r}"


async def test_the_loops_own_verbs_survive_a_narrowing(tmp_path: Path) -> None:
    """A mode narrowing to one tool must not take `done` away: the verbs are the pattern's, and a
    loop that cannot say it has finished does not finish. This is why the narrowing is applied to
    the registrations and not to the catalogue the method returns.
    """
    model = Listening()
    await _one_turn(await a_thread(tmp_path, model, Behaviour(tools_offered=("read_it",))))

    verbs = [name for name in model.shown() if name not in OURS]
    assert "done" in verbs, verbs
