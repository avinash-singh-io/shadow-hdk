"""A mode is a ceiling and an ask line — data, so two modes, ten, or one called `auto` is a
different mapping through the same adapter.

The four here are *examples in a test*, not a vocabulary the adapter imposes. The runtime knows no
mode names at all, and this adapter knows only the ones a product hands it.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shadow_hdk.adapters.modes import Mode, ModeGovernance, layer
from shadow_hdk.kernel import ASSUME_WORST, NOTHING, EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Context, GovernancePort
from tests.adapters.contract import GovernancePortContract

EVERYTHING = ScopeSet(everything=True)

READ = Mode("read", EffectProfile(reads=EVERYTHING))
BUILD = Mode("build", EffectProfile(reads=EVERYTHING, writes=ScopeSet.of("workspace")))
ACT = Mode("act", ASSUME_WORST, ask_above=EffectProfile(reads=EVERYTHING, writes=EVERYTHING))
AUTO = Mode("auto", ASSUME_WORST)

MODES = {m.name: m for m in (READ, BUILD, ACT, AUTO)}

LOOKING = EffectProfile(reads=ScopeSet.of("workspace"))
WRITING_A_FILE = EffectProfile(reads=EVERYTHING, writes=ScopeSet.of("workspace"))
SENDING_AN_EMAIL = EffectProfile(reaches=True, reversible=False, contained=False, costs=True)


def ctx(mode: str) -> Context:
    return Context(run_id="r", step="s", principal="p", attributes={"mode": mode})


def governance(default: str = "read") -> ModeGovernance:
    return ModeGovernance(MODES, default=default)


class TestModeGovernanceIsAGovernancePort(GovernancePortContract):
    def port(self) -> GovernancePort:
        return governance(default="auto")


async def test_reading_is_allowed_in_every_mode() -> None:
    for name in MODES:
        assert (await governance().judge(LOOKING, ctx(name))).kind == "allow"


async def test_writing_a_file_is_refused_while_reading_and_allowed_while_building() -> None:
    assert (await governance().judge(WRITING_A_FILE, ctx("read"))).kind == "refuse"
    assert (await governance().judge(WRITING_A_FILE, ctx("build"))).kind == "allow"


async def test_the_irreversible_is_refused_while_building_and_asked_while_acting() -> None:
    assert (await governance().judge(SENDING_AN_EMAIL, ctx("build"))).kind == "refuse"
    asked = await governance().judge(SENDING_AN_EMAIL, ctx("act"))
    assert asked.kind == "ask"
    assert "act" in asked.question or "irreversible" in asked.question.lower()


async def test_auto_never_asks() -> None:
    """A mode with no ask line does not stop for anybody. That is a thing a product may want and
    the adapter will not second-guess — but it has to be *said*, not inherited."""
    assert (await governance().judge(SENDING_AN_EMAIL, ctx("auto"))).kind == "allow"


async def test_a_refusal_names_the_mode_that_refused() -> None:
    refusal = await governance().judge(SENDING_AN_EMAIL, ctx("read"))
    assert refusal.kind == "refuse"
    assert "read" in refusal.reason


async def test_an_unknown_mode_refuses_rather_than_falling_back() -> None:
    """The dangerous failure would be silent widening: a typo in a mode name resolving to whatever
    the default is. It refuses, and says which name it did not recognise."""
    refusal = await governance().judge(LOOKING, ctx("biuld"))
    assert refusal.kind == "refuse"
    assert "biuld" in refusal.reason


async def test_a_context_with_no_mode_takes_the_default() -> None:
    bare = Context(run_id="r", step="s")
    assert (await governance(default="read").judge(WRITING_A_FILE, bare)).kind == "refuse"
    assert (await governance(default="build").judge(WRITING_A_FILE, bare)).kind == "allow"


async def test_a_default_that_is_not_a_mode_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="default"):
        ModeGovernance(MODES, default="nonexistent")


# ---------------------------------------------------------------- layering


async def test_a_team_layer_can_only_narrow() -> None:
    team = Mode("build", EffectProfile(reads=ScopeSet.of("workspace"), writes=EVERYTHING))
    layered = layer(BUILD, team)
    assert layered.ceiling.narrows(BUILD.ceiling)
    assert layered.ceiling.narrows(team.ceiling)
    assert (
        await ModeGovernance({"build": layered}, default="build").judge(
            WRITING_A_FILE, ctx("build")
        )
    ).kind == "refuse"


scope_sets = st.one_of(
    st.just(EVERYTHING),
    st.frozensets(st.sampled_from(("session", "workspace", "record"))).map(ScopeSet),
)
profiles = st.builds(
    EffectProfile,
    reads=scope_sets,
    writes=scope_sets,
    reaches=st.booleans(),
    reversible=st.booleans(),
    contained=st.booleans(),
    costs=st.booleans(),
)


@given(profiles, profiles)
def test_layering_is_narrowing_whatever_the_layers_say(
    base: EffectProfile, over: EffectProfile
) -> None:
    """The property the whole design rests on: a team cannot widen what it was given, and it is the
    kernel's `meet` that makes it true rather than a review."""
    layered = layer(Mode("m", base), Mode("m", over))
    assert layered.ceiling.narrows(base)
    assert layered.ceiling.narrows(over)


@given(profiles)
def test_nothing_is_allowed_under_every_mode_and_assume_worst_only_under_the_widest(
    ceiling: EffectProfile,
) -> None:
    mode = Mode("m", ceiling)
    assert NOTHING.narrows(mode.ceiling)
    if ASSUME_WORST.narrows(mode.ceiling):
        assert mode.ceiling == ASSUME_WORST
