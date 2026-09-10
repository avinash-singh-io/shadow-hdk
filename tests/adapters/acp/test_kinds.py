"""What a child agent is asking for, in our own vocabulary.

ACP tells us the *kind* of a tool call — `read`, `edit`, `delete`, `execute` and six more. That is
half a profile, exactly as MCP's annotations were half a profile in Phase 1, and the other half is
the deployment's. Everything unmapped or absent is the worst case, which is the rule that lets the
registry stay open: **an effect nobody vouched for is assumed to be the worst one.**
"""

from __future__ import annotations

import pytest
from shadow_hdk.adapters.acp import effects_for

from shadow_hdk.kernel import ASSUME_WORST, NOTHING, EffectProfile, ScopeSet

WORKSPACE = ScopeSet.of("workspace")


def profile(kind: str | None, *, contained: bool = False, network: bool = False) -> EffectProfile:
    return effects_for(kind, contained=contained, network=network)


@pytest.mark.parametrize("kind", ["read", "search"])
def test_looking_only_reads(kind: str) -> None:
    found = profile(kind)
    assert found.reads == WORKSPACE
    assert found.writes == ScopeSet()
    assert found.reversible


def test_thinking_touches_nothing() -> None:
    """A child that is only reasoning has no effect, and a mode forbidding everything still
    permits it — which is what makes `NOTHING` the bottom of the order, not a special case."""
    assert profile("think") == NOTHING


@pytest.mark.parametrize("kind", ["edit", "move"])
def test_changing_a_file_is_reversible(kind: str) -> None:
    found = profile(kind)
    assert found.writes == WORKSPACE
    assert found.reversible is True


def test_deleting_is_not_reversible() -> None:
    """The same distinction the workspace adapter makes: change and destroy are different
    permissions, and one field carries it."""
    assert profile("delete").writes == WORKSPACE
    assert profile("delete").reversible is False


def test_fetching_reaches_outside() -> None:
    found = profile("fetch")
    assert found.reaches is True
    assert found.reversible is True, "reading the internet changes nothing here"


def test_executing_is_irreversible_and_carries_the_deployments_containment() -> None:
    on_a_laptop = profile("execute", contained=False)
    assert on_a_laptop.reversible is False
    assert on_a_laptop.contained is False
    assert on_a_laptop.reaches is True, "an uncontained host cannot promise otherwise"

    contained = profile("execute", contained=True, network=False)
    assert contained.contained is True
    assert contained.reaches is False


@pytest.mark.parametrize("kind", [None, "other", "switch_mode", "something_invented_in_2028"])
def test_anything_undeclared_or_unknown_is_the_worst_case(kind: str | None) -> None:
    """Including a kind that does not exist yet. A protocol gains values; a system that treats an
    unrecognised one as harmless gains a hole on the day it does."""
    assert profile(kind) == ASSUME_WORST


def test_the_mapping_covers_every_kind_acp_defines() -> None:
    """A guard against the protocol moving underneath us: if ACP adds a kind and we do not map it,
    this says so — and until it is mapped the worst case applies, which is safe but blunt.
    """
    from acp import schema

    annotation = schema.ToolCallUpdate.model_fields["kind"].annotation
    assert annotation is not None
    declared = set(annotation.__args__[0].__args__)
    from shadow_hdk.adapters.acp.kinds import KNOWN_KINDS

    unmapped = declared - KNOWN_KINDS - {"other", "switch_mode"}
    assert not unmapped, f"ACP declares kinds this bridge does not map: {sorted(unmapped)}"


def test_execute_admits_it_reaches_the_machine_unless_contained() -> None:
    """BUG-018, on this side of the house.

    `execute` claimed `{workspace}` for reads and writes whatever `contained` said, while getting
    `reaches` right in the same expression. A command run on an ordinary host reaches the whole
    machine — `cd ..` works, an absolute path works — so a mode permitting workspace writes was
    permitting writes anywhere, and the record said the workspace.

    The sandbox adapter had the identical mistake. Neither imports the other, and the rule was
    written in a docstring rather than in a test, so it was applied to one field of three in two
    places. It is a test in both now.
    """
    from shadow_hdk.kernel import ScopeSet

    loose = effects_for("execute", contained=False)
    assert loose.reads == ScopeSet(everything=True)
    assert loose.writes == ScopeSet(everything=True)

    proven = effects_for("execute", contained=True)
    assert proven.reads == ScopeSet.of("workspace")
    assert proven.writes == ScopeSet.of("workspace")
