"""A person's input reaches the page, and only while the keyboard is theirs (ENH-053)."""

from typing import Any

import pytest

from shadow_hdk.adapters.browser import OriginPolicy, PlaywrightEngine
from shadow_hdk.adapters.browser.person_input import KEY, MOUSE, PersonInput
from shadow_hdk.kernel import Refused

pytestmark = pytest.mark.anyio
SCOPE = "pane"


class Session:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Any]] = []

    async def send(self, method: str, params: Any = None) -> Any:
        self.sent.append((method, params))
        return {}


async def test_a_click_presses_and_releases() -> None:
    """A press with no release leaves the page holding a button nobody is pressing."""
    session = Session()
    await PersonInput(session).click(12, 34)
    kinds = [params["type"] for method, params in session.sent if method == MOUSE]
    assert kinds == ["mousePressed", "mouseReleased"], session.sent
    assert all(params["x"] == 12 and params["y"] == 34 for _, params in session.sent)


async def test_typing_arrives_as_keystrokes_not_as_a_paste() -> None:
    """A page that reacts per keystroke must behave as it would under real hands."""
    session = Session()
    await PersonInput(session).type("hi")
    chars = [params["text"] for method, params in session.sent if method == KEY]
    assert chars == ["h", "i"], session.sent


async def test_a_named_key_goes_down_and_up() -> None:
    session = Session()
    await PersonInput(session).key("Enter")
    kinds = [params["type"] for method, params in session.sent if method == KEY]
    assert kinds == ["keyDown", "keyUp"], session.sent
    assert all(params["key"] == "Enter" for _, params in session.sent)


async def test_a_person_may_only_drive_while_the_keyboard_is_theirs() -> None:
    """The lease decides, and it is asked before any input is dispatched."""
    engine = PlaywrightEngine(policy=OriginPolicy(("http://127.0.0.1:1",)), install_browser=False)
    refused = await engine.person_acts(SCOPE, "click", {"x": 1, "y": 2})
    assert isinstance(refused, Refused), refused
    assert "keyboard" in refused.reason.lower() or "driving" in refused.reason.lower(), refused

    await engine.hand_to_person(SCOPE)
    allowed = await engine.person_acts(SCOPE, "click", {"x": 1, "y": 2})
    assert isinstance(allowed, Refused), allowed
    # Now refused for having no page open, not for who is driving.
    assert "keyboard" not in allowed.reason.lower(), allowed.reason


async def test_an_unknown_person_action_is_refused_by_name() -> None:
    engine = PlaywrightEngine(policy=OriginPolicy(("http://127.0.0.1:1",)), install_browser=False)
    await engine.hand_to_person(SCOPE)
    outcome = await engine.person_acts(SCOPE, "levitate", {})
    assert isinstance(outcome, Refused), outcome
    assert "levitate" in outcome.reason, outcome.reason
