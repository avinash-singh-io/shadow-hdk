"""The narrowing order is a partial order and the meet is its greatest lower bound (09 §2).

Property-tested, because these two facts are what let a team's mode file be *proven* to narrow
rather than reviewed for it.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from shadow_hdk.kernel.effects import ASSUME_WORST, NOTHING, EffectProfile, ScopeSet

SCOPES = ("session", "host", "workspace", "network", "record")

scope_sets = st.one_of(
    st.just(ScopeSet(everything=True)),
    st.frozensets(st.sampled_from(SCOPES)).map(ScopeSet),
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


@given(profiles)
def test_narrows_is_reflexive(a: EffectProfile) -> None:
    assert a.narrows(a)


@given(profiles, profiles)
def test_narrows_is_antisymmetric(a: EffectProfile, b: EffectProfile) -> None:
    if a.narrows(b) and b.narrows(a):
        assert a == b


@given(profiles, profiles, profiles)
def test_narrows_is_transitive(a: EffectProfile, b: EffectProfile, c: EffectProfile) -> None:
    if a.narrows(b) and b.narrows(c):
        assert a.narrows(c)


@given(profiles, profiles)
def test_meet_narrows_both(a: EffectProfile, b: EffectProfile) -> None:
    m = a.meet(b)
    assert m.narrows(a) and m.narrows(b)


@given(profiles, profiles, profiles)
def test_meet_is_the_greatest_lower_bound(
    a: EffectProfile, b: EffectProfile, c: EffectProfile
) -> None:
    if c.narrows(a) and c.narrows(b):
        assert c.narrows(a.meet(b))


@given(profiles)
def test_nothing_is_the_bottom_and_assume_worst_is_the_top(a: EffectProfile) -> None:
    assert NOTHING.narrows(a)
    assert a.narrows(ASSUME_WORST)


def test_a_team_mode_that_widens_is_detectable() -> None:
    base = EffectProfile(reads=ScopeSet.of("record"), writes=ScopeSet.of("record"))
    team = EffectProfile(reads=ScopeSet.of("record", "network"), writes=ScopeSet.of("record"))
    assert not team.narrows(base)
    assert team.meet(base) == base


def test_mcp_annotations_fill_half_a_profile_and_assume_the_rest() -> None:
    read_only = EffectProfile.from_mcp_annotations(read_only_hint=True, open_world_hint=False)
    assert read_only.writes == ScopeSet() and read_only.reversible and not read_only.reaches
    assert read_only.reads.everything and not read_only.contained and read_only.costs

    undeclared = EffectProfile.from_mcp_annotations()
    assert undeclared == ASSUME_WORST

    gentle = EffectProfile.from_mcp_annotations(destructive_hint=False)
    assert gentle.reversible and gentle.writes.everything
