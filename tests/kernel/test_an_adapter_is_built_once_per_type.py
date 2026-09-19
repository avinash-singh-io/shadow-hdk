"""A contract's `TypeAdapter` is built once per type, not once per call (BUG-016).

Pydantic builds a full core schema when a `TypeAdapter` is constructed — for `Observation`, a
six-arm discriminated union, that walks thousands of nodes. The adapter is a **pure function of the
type**: nothing about it varies per call. `contracts.py` built a fresh one every time anyway, and
D19 — *a checkpoint is a wire* — means every step of every run dumps its observation through it.

Measured before the fix: a hundred-step run built **101** adapters, one cost **0.743 ms**, and the
101 of them were **75 ms of a 132 ms run — 57%** of everything the runtime charges for a step.

**These are claims about the mechanism, not stopwatch assertions**, and that is deliberate. A
wall-clock gate is exactly what failed to catch this: `test_benchmark.py` asserts at three times
D11's target, which its own docstring says catches an order of magnitude rather than a drift, and
the drift went unnoticed for phases. Asserting a tighter number would repeat the mistake in a
smaller font. What is asserted here is the thing that is actually true and cannot flake: **one
adapter per type**.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

import pytest
from pydantic import TypeAdapter

import shadow_hdk.kernel.contracts as contracts
from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Floor,
    Invoke,
    Lease,
    Observation,
    Sequence,
)
from shadow_hdk.kernel.events import Event
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, make_registration
from tests.runtime.conftest import ports_over

REG = make_registration("noop")
STEPS = 20


class Counted:
    """Counts every `TypeAdapter` actually constructed, by the type it was asked for.

    Patching the constructor rather than timing anything: the claim is *how many*, and a count is
    the same number on a fast machine and a slow one.
    """

    def __init__(self) -> None:
        self.built: list[Any] = []
        self._real = TypeAdapter.__init__

    def __enter__(self) -> Counted:
        real, built = self._real, self.built

        def counting(adapter: Any, *args: Any, **kwargs: Any) -> None:
            built.append(args[0] if args else None)
            real(adapter, *args, **kwargs)

        TypeAdapter.__init__ = counting  # type: ignore[method-assign, assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        TypeAdapter.__init__ = self._real  # type: ignore[method-assign]

    def of(self, wanted: Any) -> int:
        # Equality, not identity: on Python 3.14 `Event | None` evaluated twice is two equal
        # union objects with one hash — the cache still holds, keyed by the type — where 3.12
        # happened to hand back the very same object (found running the suite on 3.14).
        return sum(1 for what in self.built if what == wanted)


def _warm() -> None:
    """Build every adapter this test will ask about, so the count is of *repeat* construction.

    Without this the first call of a fresh process is indistinguishable from a per-call build, and
    the test would pass on the bug the first time and fail the second.
    """
    contracts.dump(Completed("ok"), Observation)
    contracts.load('{"kind":"completed","output":"ok"}', Observation)


def test_dumping_the_same_type_twice_builds_one_adapter() -> None:
    _warm()
    with Counted() as counted:
        contracts.dump(Completed("one"), Observation)
        contracts.dump(Completed("two"), Observation)
        contracts.dump(Completed("three"), Observation)

    assert counted.of(Observation) == 0, "a fresh adapter was built for a type already seen"


def test_loading_uses_the_same_adapter_as_dumping() -> None:
    """One cache, keyed on the type — not one per call site. `dump` and `load` name the same type
    and the expensive object is the same object."""
    _warm()
    with Counted() as counted:
        contracts.load(contracts.dump(Completed("ok"), Observation), Observation)

    assert counted.of(Observation) == 0


def test_a_type_never_seen_is_built_once_and_then_never_again() -> None:
    """The cache must not be a table somebody has to remember to fill. A type the kernel has never
    dumped is built on first use, and that is the only time."""
    with Counted() as counted:
        for _ in range(4):
            contracts.dump(Completed("ok"), Event | None)  # a shape nothing else asks for

    assert counted.of(Event | None) == 1


def test_a_run_builds_one_observation_adapter_however_many_steps_it_takes() -> None:
    """The claim the bug is actually about. Every step dumps its observation into the checkpoint
    (D19), and each of those used to build the union's schema again from nothing."""
    _warm()
    composition = Composition(
        (Sequence("s", tuple(Invoke(f"n{i}", REG.id) for i in range(STEPS))),)
    )

    async def drive() -> None:
        ports, _ = ports_over([(REG, "ok")], clock=FixedClock())
        options = RunOptions(lease=Lease(Ceiling(STEPS + 10, 10_000, None), Floor(0)))
        async for _event in run(composition, ports, options=options):
            pass

    with Counted() as counted:
        asyncio.run(drive())

    assert counted.of(Observation) == 0, (
        f"a {STEPS}-step run built {counted.of(Observation)} observation adapters; "
        "the schema is a pure function of the type and does not change between steps"
    )


def test_the_cached_adapter_is_the_same_object() -> None:
    """What makes the count claim above mean something: the second call gets the first adapter,
    rather than a second one that happened not to be counted."""
    first = contracts.adapter_for(Observation)
    second = contracts.adapter_for(Observation)

    assert first is second


def test_two_types_do_not_share_an_adapter() -> None:
    """The failure a cache invites, and the one that would be silent: an adapter keyed on nothing
    would validate an `Event` against `Observation` and be believed."""
    assert contracts.adapter_for(Observation) is not contracts.adapter_for(Event)


def test_an_unhashable_annotation_still_works() -> None:
    """A cache must not turn a working call into a `TypeError`.

    **The first version of this test proved nothing**, and a mutation removing the guard survived
    it: `list[dict[str, int]]` looks exotic and is perfectly hashable, so the except branch was
    never reached. What is genuinely unhashable is an `Annotated` carrying mutable metadata — a
    dict or a list beside the type — which is an ordinary thing for a host to write and exactly the
    shape a kernel whose job is crossing wires will be handed.
    """
    unhashable = Annotated[int, {"units": "ms"}]
    with pytest.raises(TypeError):
        hash(unhashable)  # the arrangement, asserted, so this cannot silently stop being the case

    assert contracts.load("7", unhashable) == 7
    assert contracts.dump(7, unhashable) == "7"


def test_every_entry_point_uses_the_cache() -> None:
    """Uniform, because two mutations survived by uncaching the two functions nothing counted.

    `round_trip` and `json_schema` are not on the runtime's step path, so uncaching them costs no
    measurable latency — which is precisely why a test aimed only at the hot path let them go. The
    claim worth holding is the simple one: **no function in this module builds an adapter for a
    type it has already built one for**, wherever it is called from.

    Counted for `Observation` alone rather than for everything. Pydantic constructs its own
    adapters while generating a schema — `str`, `bool`, every nested dataclass — and those are its
    business, not this module's. A test that counted them would fail for a reason it was not about.
    """
    _warm()
    contracts.json_schema("Observation")

    with Counted() as counted:
        contracts.dump(Completed("ok"), Observation)
        contracts.load('{"kind":"completed","output":"ok"}', Observation)
        contracts.round_trip(Completed("ok"), Observation)
        contracts.json_schema("Observation")

    assert counted.of(Observation) == 0, (
        f"{counted.of(Observation)} of these four calls rebuilt the observation adapter"
    )
