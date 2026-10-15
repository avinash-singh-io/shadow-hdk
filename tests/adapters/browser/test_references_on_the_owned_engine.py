"""The owned engine carries element references itself, so no second engine is needed for them.

The reference contract is the one the replacement candidate was preferred for: a snapshot names
each element by role and name against an opaque handle, acting through that handle reaches the
element, and a handle from a page that has gone is refused rather than retargeted.
"""

from typing import Any, cast

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.browser import OriginPolicy, PlaywrightEngine
from shadow_hdk.kernel import Failed, Refused
from tests.adapters.browser.test_real_browser import apps, completed  # noqa: F401

pytestmark = [pytest.mark.anyio, pytest.mark.browser, pytest.mark.timeout(180)]


def _named(refs: dict[str, Any], role: str, name: str) -> str:
    return next(ref for ref, node in refs.items() if node["role"] == role and node["name"] == name)


async def test_snapshot_refs_act_on_the_element_and_invalidate_after_navigation(
    apps: Any,  # noqa: F811
) -> None:
    first, _, _, _, ca = apps
    engine = PlaywrightEngine(
        policy=OriginPolicy((first.origin,), allow_localhost=False),
        upstream_ca=ca,
        install_browser=False,
    )
    try:
        await completed(engine, "open", {"url": first.origin})
        snapshot = cast(dict[str, Any], (await completed(engine, "snapshot", {})).output)
        refs = snapshot["refs"]
        title = _named(refs, "textbox", "Title")
        save = _named(refs, "button", "Save")

        await completed(engine, "type", {"ref": title, "value": "Reference edit"})
        await completed(engine, "press", {"ref": save, "key": "Enter"})
        observed = cast(dict[str, Any], (await completed(engine, "snapshot", {})).output)
        assert "Reference edit" in observed["snapshot"]
        # The edited elements survive the same-document update, so their handles still stand.
        assert title in observed["refs"]

        await completed(engine, "open", {"url": first.origin + "/next"})
        stale = await engine.execute("type", {"ref": title, "value": "must not retarget"}, "app")
        assert isinstance(stale, Failed), stale
        # Named, and not merely a timeout: leaving the document must retire the handle, so this
        # is refused on sight rather than after spending the caller's whole budget on it.
        assert title in stale.error and "snapshot" in stale.error.lower(), stale.error
        new = cast(dict[str, Any], (await completed(engine, "snapshot", {})).output)
        assert title not in new["refs"] and "Next page" in new["snapshot"]
    finally:
        await engine.release_run("app")


async def test_a_handle_is_refused_before_any_snapshot_rather_than_waited_on(
    apps: Any,  # noqa: F811
) -> None:
    """A handle nothing has issued fails named and at once; it must not spend the timeout."""
    first, _, _, _, ca = apps
    engine = PlaywrightEngine(
        policy=OriginPolicy((first.origin,), allow_localhost=False),
        upstream_ca=ca,
        install_browser=False,
    )
    try:
        await completed(engine, "open", {"url": first.origin})
        outcome = await engine.execute("click", {"ref": "@e9999", "timeout_ms": 30000}, "app")
        assert isinstance(outcome, Failed), outcome
        assert "@e9999" in outcome.error and "snapshot" in outcome.error.lower(), outcome.error
    finally:
        await engine.release_run("app")


async def test_ref_inputs_are_exclusive_and_do_not_provision_on_malformed_input() -> None:
    engine = PlaywrightEngine()
    for values in (
        {"ref": "@e1", "selector": "input"},
        {"ref": "@e1", "role": "textbox"},
        {"ref": "@e1", "nth": 0},
        {"ref": "not-a-ref"},
        {"ref": "@e1", "name": "unused"},
    ):
        outcome = await engine.execute("click", cast(JsonValue, values), "unopened")
        assert isinstance(outcome, Refused), outcome
    assert engine._profiles == {}
