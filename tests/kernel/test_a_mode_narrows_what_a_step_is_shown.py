"""`tools_offered` narrows, and an unknown name refuses (D178, D179, phase 65, BUG-230).

A mode may name a subset of the run's tools for a step. Until this phase the field **parsed and did
nothing**: `adapters/jsonl/transport.py` skipped it as a launch flag with the comment *offered-set
narrowing is the registry's, not a launch flag*, and no registry narrowed by it. Both honesty
fields then reported it delivered — `unmapped_behaviour` unioned it into `mapped` unconditionally
and `unmapped_for_a_model` excluded it with the words *the registry narrows what a model is shown,
so it is honoured elsewhere*. So a product that narrowed got everything **and** was told the
narrowing was honoured, which is worse than either failure alone, because the report is what lane P
planned against.

The derivation is pure and lives here because there are genuinely **two** catalogues — the one an
in-process loop builds for a key-backed model, and the one the registry serves a CLI over MCP. One
derivation, two call sites, so the two cannot drift.
"""

from __future__ import annotations

from shadow_hdk.kernel.providers import Behaviour, narrowed, unanswered

EVERYTHING = ("read", "write", "run", "ask_person")


# ------------------------------------------------------------------ what a step is shown


def test_a_behaviour_naming_a_subset_is_shown_that_subset() -> None:
    kept = narrowed(EVERYTHING, Behaviour(tools_offered=("read", "run")))

    assert kept == ("read", "run"), kept


def test_the_runs_own_order_is_kept_not_the_modes() -> None:
    """A catalogue that reshuffles because a mode listed its names in another order would make the
    offered set a second source of ordering. The run's order is the run's."""
    kept = narrowed(EVERYTHING, Behaviour(tools_offered=("run", "read")))

    assert kept == ("read", "run"), kept


def test_a_behaviour_naming_nothing_is_shown_everything() -> None:
    """The default, and the whole of today's behaviour. Asserted rather than assumed."""
    assert narrowed(EVERYTHING, Behaviour()) == EVERYTHING


def test_no_behaviour_at_all_is_shown_everything() -> None:
    assert narrowed(EVERYTHING, None) == EVERYTHING


def test_narrowing_can_only_take_away() -> None:
    """D178: it is applied last, so no mode can widen past what the policy left. A name the run
    does not have cannot be conjured by asking for it."""
    kept = narrowed(("read",), Behaviour(tools_offered=("read", "write", "delete_everything")))

    assert kept == ("read",), kept


def test_narrowing_to_nothing_of_what_is_there_shows_nothing() -> None:
    """Not a fallback to everything, which is the failure mode that makes a typo invisible."""
    assert narrowed(EVERYTHING, Behaviour(tools_offered=("nothing_like_it",))) == ()


# ------------------------------------------------------------------ and a name nothing answers to


def test_a_name_no_registration_answers_to_is_named() -> None:
    """D179, the D176 cut again: a typo that silently offers everything is the failure this
    phase exists to stop, so the caller is given what to refuse with."""
    missing = unanswered(EVERYTHING, Behaviour(tools_offered=("read", "reed")))

    assert missing == ("reed",), missing


def test_several_are_named_sorted_so_a_refusal_reads_the_same_twice() -> None:
    missing = unanswered(EVERYTHING, Behaviour(tools_offered=("zebra", "aardvark", "read")))

    assert missing == ("aardvark", "zebra"), missing


def test_a_behaviour_naming_only_real_names_has_nothing_unanswered() -> None:
    assert unanswered(EVERYTHING, Behaviour(tools_offered=("read", "write"))) == ()


def test_a_behaviour_naming_nothing_has_nothing_unanswered() -> None:
    """An empty offered set is *all of them*, not *none of them named wrongly*."""
    assert unanswered(EVERYTHING, Behaviour()) == ()
    assert unanswered(EVERYTHING, None) == ()


def test_nothing_is_unanswered_against_an_empty_run() -> None:
    """A run with no tools and a mode that narrows: every name is unanswered, and saying so is
    how a product learns its registry never arrived."""
    assert unanswered((), Behaviour(tools_offered=("read",))) == ("read",)


# ------------------------------------------------------------------ and the honesty fields agree


def test_a_narrowing_mode_is_reported_on_only_for_what_the_cli_cannot_take() -> None:
    """The two sides must move together, and the test has to bite to say so.

    An earlier version of this asserted only that a narrowing mode reports nothing unmapped — which
    passed **vacuously**: `unmapped_behaviour` walks five named fields and `tools_offered` is not
    one of them, so the `| {"tools_offered"}` union it carried since phase 62 was dead code that
    could never change an answer. A mutation deleting the union survived, which is how that was
    found. So this pairs the narrowing with a field the CLI genuinely cannot take: exactly one name
    comes back, and it is the other one.
    """
    from shadow_hdk.kernel.providers import Dialect, Provider, unmapped_behaviour

    provider = Provider(id="c", kind="agent", bin="c", dialect=Dialect())
    behaviour = Behaviour(tools_offered=("read",), temperature=0.5)

    assert unmapped_behaviour(provider, behaviour) == ["temperature"], (
        "a narrowing the kit applies must not be named; a temperature a turn cannot set must be"
    )


def test_a_key_backed_model_does_not_name_a_narrowing_it_gets() -> None:
    from shadow_hdk.kernel.providers import unmapped_for_a_model

    assert "tools_offered" not in unmapped_for_a_model(Behaviour(tools_offered=("read",)))
