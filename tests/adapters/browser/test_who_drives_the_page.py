"""Who may drive the page, and the fact of it on the record (ENH-053).

A pane exists so a person can watch the agent work and take the keyboard when a flow needs a human.
The taking is not a button in a user interface: while a person drives, the agent's governance is not
what gates the page, so the kit has to know who holds the keyboard and say when it changes. The same
reasoning made a dropped agent report itself rather than vanish.

Mechanism only. Who is allowed to take over, and what a pane looks like, stay with the product.
"""

from typing import Any

import pytest

from shadow_hdk.adapters.browser import OriginPolicy, PlaywrightEngine
from shadow_hdk.kernel import Refused

pytestmark = pytest.mark.anyio

SCOPE = "pane"


def an_engine() -> PlaywrightEngine:
    """No browser is started here: the lease is decided before any page exists, and a refusal that
    needed a running Chromium to be told would be a refusal a product could not rely on."""
    return PlaywrightEngine(policy=OriginPolicy(("http://127.0.0.1:1",)), install_browser=False)


async def test_the_agent_drives_until_somebody_takes_over() -> None:
    engine = an_engine()
    assert engine.driver(SCOPE) == "agent", (
        "the agent drives unless a person has taken the keyboard"
    )


async def test_a_person_holding_the_keyboard_refuses_the_agent_by_name() -> None:
    """Refused, not failed, and said plainly: this is a decision about who drives, not an error."""
    engine = an_engine()
    await engine.hand_to_person(SCOPE)
    assert engine.driver(SCOPE) == "person"
    outcome = await engine.execute("click", {"selector": "#go"}, SCOPE)
    assert isinstance(outcome, Refused), outcome
    assert "person" in outcome.reason.lower(), outcome.reason


async def test_reading_the_page_is_still_allowed_while_a_person_drives() -> None:
    """A person at the keyboard does not blind the agent. Watching is not driving, and an agent
    that cannot read cannot report what it saw happen."""
    engine = an_engine()
    await engine.hand_to_person(SCOPE)
    outcome = await engine.execute("snapshot", {}, SCOPE)
    assert isinstance(outcome, Refused), outcome
    # Refused for having no browser open in this scope — not for who is driving.
    assert "person" not in outcome.reason.lower(), outcome.reason


async def test_handing_back_returns_the_keyboard() -> None:
    engine = an_engine()
    await engine.hand_to_person(SCOPE)
    await engine.hand_back(SCOPE)
    assert engine.driver(SCOPE) == "agent"
    outcome = await engine.execute("click", {"selector": "#go"}, SCOPE)
    assert isinstance(outcome, Refused), outcome
    assert "person" not in outcome.reason.lower(), "the keyboard came back, so this is another no"


async def test_each_scope_has_its_own_keyboard() -> None:
    """One person taking over one pane must not freeze another conversation's agent."""
    engine = an_engine()
    await engine.hand_to_person(SCOPE)
    assert engine.driver("another") == "agent"


async def test_the_handover_reaches_the_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """A product that treats a person's input as consent needs to find it on the record later."""
    said: list[tuple[str, str]] = []

    class Recording:
        async def activity(self, kind: str, text: str) -> None:
            said.append((kind, text))

    engine = an_engine()
    monkeypatch.setattr("shadow_hdk.adapters.browser.engine.current_run", lambda: Recording())
    await engine.hand_to_person(SCOPE)
    await engine.hand_back(SCOPE)
    kinds = [kind for kind, _ in said]
    assert kinds == ["browser_driver", "browser_driver"], said
    assert "person" in said[0][1].lower() and "agent" in said[1][1].lower(), said


async def test_a_handover_with_no_run_to_tell_is_still_a_handover() -> None:
    """The lease is the kit's own state. A host taking over between turns has no run to record
    into, and must not be told no because of it."""
    engine = an_engine()
    await engine.hand_to_person(SCOPE)
    assert engine.driver(SCOPE) == "person"


def test_every_write_action_is_covered_by_the_lease() -> None:
    """Named explicitly rather than derived, so a new write action cannot quietly escape the lease:
    adding one to the contract and not to this list is a failure here.
    """
    from shadow_hdk.adapters.browser.arguments import READ_ACTIONS, WRITE_ACTIONS
    from shadow_hdk.adapters.browser.engine import PERSON_HOLDS

    assert set(PERSON_HOLDS) == set(WRITE_ACTIONS), (set(WRITE_ACTIONS) - set(PERSON_HOLDS),)
    assert not set(PERSON_HOLDS) & set(READ_ACTIONS), "reading is never withheld from the agent"


def _unused(value: Any) -> None:
    return None
