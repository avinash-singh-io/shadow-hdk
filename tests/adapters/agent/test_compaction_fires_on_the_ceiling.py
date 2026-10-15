"""A thread folds its own history before the window stops it (ENH-052, the audit's H34).

Compaction existed and only ever happened when a model chose to call for it — and no shipped
pattern offered it, so on the patterns a product actually uses it could not be chosen at all. With
a token ceiling to measure against, the kit can fold the history itself when the budget is nearly
gone, which is the difference between a thread that gets shorter and a thread that fails at the
window.

The threshold is the product's number, carried on the pattern beside the other sizes it chooses.
When to act is mechanism; how much room to leave is content.
"""

from typing import Any

import pytest

from shadow_hdk.adapters.agent.loader import pattern_from
from shadow_hdk.adapters.agent.pattern import COMPACT, Pattern
from shadow_hdk.kernel import Ceiling, Floor, Lease

pytestmark = pytest.mark.anyio


def test_the_threshold_is_carried_on_the_pattern_and_defaults_to_never() -> None:
    """Off unless a product asks: folding a history is lossy, and a kit that did it uninvited
    would be throwing away a thread's past on a number nobody chose."""
    assert Pattern(name="p", system="s").compact_under_tokens is None
    assert (
        pattern_from(
            {"name": "p", "system": "s", "compact_under_tokens": 2000}, where="row"
        ).compact_under_tokens
        == 2000
    )


def test_a_shipped_pattern_offers_compaction_so_a_model_can_choose_it() -> None:
    """H34: it was in no shipped pattern's meta tools, so the one way it could ever happen was
    unavailable on every pattern a product starts from."""
    from shadow_hdk.adapters.agent import shipped

    offering = [name for name, pattern in shipped().items() if COMPACT in pattern.meta_tools]
    assert offering, "no shipped pattern lets a model ask to compact"


@pytest.mark.parametrize(
    "left, under, folds",
    [
        (100, 2000, True),
        (5000, 2000, False),
        (2000, 2000, True),
        (None, 2000, False),
        (100, None, False),
    ],
)
def test_when_a_fold_is_due(left: int | None, under: int | None, folds: bool) -> None:
    """Due at or below the threshold, never without one, and never on an unknown count — a
    provider that reports nothing must not trigger a fold any more than it exhausts a run."""
    from shadow_hdk.adapters.agent.component import a_fold_is_due

    assert a_fold_is_due(Lease(Ceiling(10, 10, None, max_tokens=left), Floor(0)), under) is folds


async def test_the_loop_folds_before_asking_the_model_again() -> None:
    """The point of the whole thing: the fold happens while there is still room to send it."""
    folded: list[str] = []

    class Ctx:
        async def remaining_now(self) -> Lease:
            return Lease(Ceiling(10, 10, None, max_tokens=10), Floor(0))

    class Loop:
        pattern = Pattern(name="p", system="s", compact_under_tokens=2000)
        ctx = Ctx()

        async def compact(self, call: Any = None) -> None:
            folded.append("folded")

    from shadow_hdk.adapters.agent.component import _Turnwise

    await _Turnwise._fold_if_due(Loop())  # type: ignore[arg-type]
    assert folded == ["folded"], folded


def test_the_loop_actually_calls_the_fold() -> None:
    """That the method exists is not that it runs — twice over in this release train a wait and a
    hand-over were written, left uncalled, and passed every control that invoked them directly.

    Asserted against the source of the turn loop, because a control that calls the method itself
    cannot tell the difference.
    """
    from pathlib import Path

    import shadow_hdk.adapters.agent.component as module

    body = Path(module.__file__).read_text(encoding="utf-8")
    loop = body.split("for turn in range(self.turns, self.pattern.max_turns):", 1)[1]
    asked = loop.split("request = ModelRequest", 1)[0]
    assert "_fold_if_due()" in asked, "the loop must fold before it builds the request"
