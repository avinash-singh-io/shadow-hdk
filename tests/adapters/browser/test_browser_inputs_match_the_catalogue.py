"""A browser argument is used, or refused; the offered contract does not accept ignored fields."""

from typing import Any, cast

from pydantic import JsonValue

from shadow_hdk.adapters.browser import BrowserComponents, PlaywrightEngine
from shadow_hdk.adapters.browser.arguments import parse
from shadow_hdk.kernel import Refused


async def test_arguments_not_used_by_an_action_are_refused_before_opening_a_profile() -> None:
    engine = PlaywrightEngine()
    cases: tuple[tuple[str, JsonValue], ...] = (
        ("tabs", {"tab": "unused"}),
        ("new_tab", {"url": "http://localhost", "tab": "unused"}),
        ("find", {"selector": "button", "nth": 2}),
        ("console", {"timeout_ms": 1000}),
        ("click", {"selector": "button", "name": "unused accessible name"}),
        ("type", {"selector": "input", "value": None}),
        ("open", {"url": "http://localhost", "script": "ignored"}),
    )
    for action, inputs in cases:
        result = await engine.execute(action, inputs, "unopened")
        assert isinstance(result, Refused) and "invalid browser inputs" in result.reason, result
    assert engine._profiles == {}, "invalid inputs must not provision or launch the engine"


async def test_the_catalogue_offers_only_consumed_fields_and_uses_dispatch_limits() -> None:
    offered = {
        r.id: cast(dict[str, Any], r.component.interface.input_schema)
        for r in await BrowserComponents().registrations()
    }
    assert offered["browser_tabs"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    assert offered["browser_new_tab"]["required"] == ["url"]
    assert "tab" not in offered["browser_new_tab"]["properties"]
    assert "nth" not in offered["browser_find"]["properties"]
    assert offered["browser_type"]["properties"]["value"].get("maxLength") == 1_000_000
    assert parse("type", {"role": "textbox", "name": "Title", "value": ""}).value == ""
