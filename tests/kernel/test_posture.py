"""Whether an effect was **gated** or merely **reported** (`08` §9 R9).

*Controlled* means we judged it before it happened; only that satisfies consent-before-effect.
*Observed* means we found out afterwards — a child agent's own unmediated work, learned from a
notification. The line is **gated versus merely reported**, and it cuts through the middle of a
child agent: what it routes through us is controlled, what it does natively is observed.

It lives on `Provenance` because provenance already answers *how did this come to be here*, and
already travels with every `Proposal` — the carrier for *something happened and we are telling you*.
"""

from __future__ import annotations

from shadow_hdk.kernel import Posture, Proposal, Provenance
from shadow_hdk.kernel.contracts import CONTRACTS, round_trip


def a_provenance(posture: Posture = "controlled") -> Provenance:
    return Provenance(
        registered_by="tests",
        adapter="recording",
        at="2026-09-10T00:00:00+00:00",
        posture=posture,
    )


def test_the_default_is_controlled() -> None:
    """The safe way round. Everything the runtime invokes, it gated — so an adapter that forgets to
    say produces a claim that is true of everything the runtime does. The exception is what has to
    be explicit.

    Constructed **without** `posture` on purpose: a first version used a helper that always passed
    it, so the test could not see the default at all, and a mutation flipping it stayed green.
    """
    bare = Provenance(registered_by="tests", adapter="recording", at="2026-09-10T00:00:00+00:00")
    assert bare.posture == "controlled"


def test_an_effect_we_only_heard_about_says_so() -> None:
    assert a_provenance(posture="observed").posture == "observed"


def test_posture_round_trips_through_json() -> None:
    postures: tuple[Posture, ...] = ("controlled", "observed")
    for posture in postures:
        provenance = a_provenance(posture=posture)
        assert round_trip(provenance, Provenance) == provenance


def test_a_proposal_carries_the_posture_of_what_produced_it() -> None:
    """The whole reason it lives here: a proposal is how something reaches the host, and the host
    needs to know whether it was consented to or merely witnessed."""
    proposal = Proposal(
        kind="tool_call", payload={"name": "wipe"}, provenance=a_provenance(posture="observed")
    )
    assert round_trip(proposal, CONTRACTS["Proposal"]) == proposal
    assert proposal.provenance.posture == "observed"
