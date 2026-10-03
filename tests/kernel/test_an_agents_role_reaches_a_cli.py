"""An agent's role and tool list compose with its mode's, for a provider that owns its loop (H11-B).

G2 confirmed the gap and found it cheaper than the audit implied: a CLI gets *everything but its own
loop*, and both mechanisms for that already shipped — the instruction flag/fold path (0.38.0,
0.41.0, measured live) and the registry narrowing (0.44.0). What was missing is the composition, and
the composition is arithmetic over two values, so it is pinned here rather than through a host.

Two rules, and the second is the one lane P asked for by name.

**Instructions layer, agent first** — D168's rule, which this reuses rather than reinventing: a
mode's words are layered *onto* the role, never replacing it, because the role is who the agent is
and the mode is what this run wants of it. Reversing them would let a mode's aside outrank the role.

**Tool lists intersect and never widen.** Both are allow-lists over one registry, and D178 made
narrowing safe precisely by applying it last so it can only take away. Two allow-lists where the
later widened the earlier would break that, and a mode could then be handed more than its policy
left by naming an agent.
"""

from __future__ import annotations

from shadow_hdk.kernel.providers import Behaviour, carried_into

ROLE = "REVIEWER-ROLE: you review a change and say what is wrong with it."


def a_behaviour(
    behaviour: Behaviour | None, *, instructions: str, tool_names: tuple[str, ...] | None
) -> Behaviour:
    """`carried_into`, with the one thing every test below assumes asserted once: composing in
    something always yields a behaviour. The signature returns `Behaviour | None` because composing
    in *nothing* returns what it was given, which may be `None`."""
    made = carried_into(behaviour, instructions=instructions, tool_names=tool_names)
    assert made is not None, "composing in a role or a tool list must yield a behaviour"
    return made


# ------------------------------------------------------------------ instructions layer


def test_an_agents_role_reaches_a_behaviour_that_had_none() -> None:
    """The whole point: a CLI run whose mode names an agent is told who to be."""
    composed = a_behaviour(Behaviour(), instructions=ROLE, tool_names=None)

    assert composed.system == ROLE


def test_a_modes_words_are_layered_onto_the_role_and_not_the_other_way() -> None:
    """D168. The role comes first because it is who the agent is; the mode is what this run wants of
    it. A mode's aside outranking the role is how an agent stops being that agent."""
    composed = a_behaviour(Behaviour(system="be terse"), instructions=ROLE, tool_names=None)

    assert ROLE in composed.system and "be terse" in composed.system
    assert composed.system.index(ROLE) < composed.system.index("be terse"), composed.system


def test_a_behaviour_with_no_agent_is_returned_unchanged() -> None:
    """Every mode that names no agent, which is most of them. Identity, not a copy with empty
    strings welded on — a changed `system` would reach a CLI's flag and be billed for."""
    behaviour = Behaviour(system="be terse", model="m", tools_offered=("read",))

    assert carried_into(behaviour, instructions="", tool_names=None) is behaviour


def test_no_behaviour_at_all_still_takes_the_role() -> None:
    """A thread opened with no mode is still entitled to its agent's role."""
    composed = a_behaviour(None, instructions=ROLE, tool_names=None)

    assert composed is not None
    assert composed.system == ROLE


def test_append_system_is_left_alone() -> None:
    """`append_system` is the mode's own second channel and is not the role's to touch."""
    composed = a_behaviour(
        Behaviour(append_system="and cite files"), instructions=ROLE, tool_names=None
    )

    assert composed.system == ROLE
    assert composed.append_system == "and cite files"


# ------------------------------------------------------------------ and tool lists intersect


def test_an_agents_tools_narrow_a_mode_that_narrowed_nothing() -> None:
    composed = a_behaviour(Behaviour(), instructions="", tool_names=("read", "write"))

    assert composed.tools_offered == ("read", "write")


def test_a_mode_that_narrowed_keeps_narrowing_when_an_agent_names_more() -> None:
    """**Never widening.** The mode allows one tool; the agent names two; the answer is one."""
    composed = a_behaviour(
        Behaviour(tools_offered=("read",)), instructions="", tool_names=("read", "write")
    )

    assert composed.tools_offered == ("read",), composed.tools_offered


def test_an_agent_that_narrows_further_than_its_mode_is_honoured() -> None:
    composed = a_behaviour(
        Behaviour(tools_offered=("read", "write")), instructions="", tool_names=("read",)
    )

    assert composed.tools_offered == ("read",), composed.tools_offered


def test_the_intersection_keeps_the_modes_order() -> None:
    """One source of ordering. A catalogue that reshuffled because an agent listed its names
    differently would make the agent a second source of it (D178's rule, again)."""
    composed = a_behaviour(
        Behaviour(tools_offered=("read", "write", "run")),
        instructions="",
        tool_names=("run", "read"),
    )

    assert composed.tools_offered == ("read", "run"), composed.tools_offered


def test_two_lists_that_do_not_overlap_offer_nothing() -> None:
    """Honest rather than helpful: an intersection of disjoint allow-lists is empty, and widening to
    either would hand a run tools something said it may not have. A name nothing answers to is the
    *other* error, and D179 already refuses that at open."""
    composed = a_behaviour(
        Behaviour(tools_offered=("read",)), instructions="", tool_names=("write",)
    )

    assert composed.tools_offered == ()


def test_an_agent_naming_no_tools_leaves_the_modes_list_alone() -> None:
    """`tool_names=None` on a pattern means *all of the run's*, exactly as an empty `tools_offered`
    does — so it must not be read as *none*."""
    composed = a_behaviour(Behaviour(tools_offered=("read",)), instructions=ROLE, tool_names=None)

    assert composed.tools_offered == ("read",)


def test_an_agent_naming_an_empty_list_is_not_the_same_as_naming_none() -> None:
    """A pattern that explicitly offers nothing has said something, and it is not *everything*."""
    composed = a_behaviour(Behaviour(tools_offered=("read",)), instructions="", tool_names=())

    assert composed.tools_offered == ()


# ------------------------------------------------------------------ and nothing else moves


def test_every_other_field_survives_untouched() -> None:
    """A composition that quietly dropped the mode's `model` would be the BUG-231 shape again."""
    behaviour = Behaviour(
        system="be terse",
        append_system="cite files",
        model="strong-one",
        effort="high",
        temperature=0.2,
        silence_seconds=42.0,
        tools_offered=("read",),
    )

    composed = a_behaviour(behaviour, instructions=ROLE, tool_names=("read",))

    assert composed.model == "strong-one"
    assert composed.effort == "high"
    assert composed.temperature == 0.2
    assert composed.silence_seconds == 42.0
    assert composed.append_system == "cite files"


def test_an_agent_with_no_role_does_not_blank_line_the_modes_own_words() -> None:
    """A pattern may carry a tool list and no role of its own. Composing in nothing must leave the
    mode's `system` byte-for-byte: this value reaches a CLI's `--system-prompt` flag, or is folded
    into the turn and paid for, so a leading blank line is not cosmetic.

    Found by a surviving mutation — the no-instructions case was only ever exercised against a
    behaviour whose `system` was already empty, where prepending nothing is invisible.
    """
    composed = a_behaviour(Behaviour(system="be terse"), instructions="", tool_names=("read",))

    assert composed is not None
    assert composed.system == "be terse", repr(composed.system)
