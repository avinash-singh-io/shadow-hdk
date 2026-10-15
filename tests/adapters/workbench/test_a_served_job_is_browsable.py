"""A development server started as a job is reachable in the governed browser (ENH-053).

Both halves already existed and nothing joined them: the workbench reports a job's verified
listeners, and the browser's origin policy allows loopback by default. What was missing was turning
one into the other, so a person can open their own server without the host naming an origin by hand
— and without widening what the gateway allows, which is the thing that must not happen here.
"""

import pytest

from shadow_hdk.adapters.browser import OriginPolicy
from shadow_hdk.adapters.workbench.host import browsable

VERIFIED = {
    "host": "127.0.0.1",
    "port": 5173,
    "protocol": "tcp",
    "source": "listener",
    "verified": True,
}


def test_a_verified_listener_becomes_a_url_the_default_policy_allows() -> None:
    """The join, and its own proof: the url is only useful if the gateway would let it through."""
    url = browsable([VERIFIED])
    assert url == "http://127.0.0.1:5173", url
    assert OriginPolicy().allows(url), "a job's own server must need no origin naming by hand"


def test_a_verified_listener_is_preferred_over_something_scraped_from_output() -> None:
    """A url printed by a process is a guess; a listener was looked up. Prefer the fact."""
    guessed = {"url": "http://127.0.0.1:9999", "source": "output", "verified": False}
    assert browsable([guessed, VERIFIED]) == "http://127.0.0.1:5173"


def test_nothing_verified_means_no_url_rather_than_a_guess() -> None:
    """Returning the guess would have the pane open a page nobody confirmed is there."""
    assert (
        browsable([{"url": "http://127.0.0.1:9999", "source": "output", "verified": False}]) is None
    )
    assert browsable([]) is None


def test_a_listener_that_is_not_loopback_is_not_offered() -> None:
    """The seam must not widen the boundary. A job bound to a routable interface is somebody else's
    reach into this run, and the policy would refuse it anyway — so it is not offered at all."""
    routable = {**VERIFIED, "host": "192.168.1.10"}
    assert browsable([routable]) is None


@pytest.mark.parametrize("protocol", ["udp", "unix", ""])
def test_only_something_a_browser_could_open_is_offered(protocol: str) -> None:
    assert browsable([{**VERIFIED, "protocol": protocol}]) is None


def test_an_unverified_listener_is_refused_even_when_it_looks_complete() -> None:
    """The `verified` flag must carry its own weight.

    The earlier control passed an unverified guess with no host or port, so it was rejected for
    being incomplete and the flag was never what stopped it — a mutation removing the check
    survived. This one is complete and loopback and tcp in every respect but confirmed, so only
    the flag can refuse it.
    """
    unconfirmed = {**VERIFIED, "verified": False, "source": "output"}
    assert browsable([unconfirmed]) is None
