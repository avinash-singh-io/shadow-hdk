"""The selected interaction SDK owns refs; the host still owns policy and lifecycle."""

import base64
from typing import Any, cast

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.browser import AgentBrowserEngine, OriginPolicy
from shadow_hdk.kernel import Failed, Refused
from tests.adapters.browser.test_real_browser import apps, completed  # noqa: F401

pytestmark = [pytest.mark.anyio, pytest.mark.browser, pytest.mark.timeout(180)]


async def test_snapshot_refs_act_on_the_element_and_invalidate_after_navigation(
    apps: Any,  # noqa: F811
) -> None:
    first, _, _, _, ca = apps
    engine = AgentBrowserEngine(
        policy=OriginPolicy((first.origin,), allow_localhost=False),
        upstream_ca=ca,
        install_browser=False,
    )
    try:
        await completed(engine, "open", {"url": first.origin})
        snapshot = cast(dict[str, Any], (await completed(engine, "snapshot", {})).output)
        refs = snapshot["refs"]
        title = next(
            ref
            for ref, node in refs.items()
            if node["role"] == "textbox" and node["name"] == "Title"
        )
        save = next(
            ref for ref, node in refs.items() if node["role"] == "button" and node["name"] == "Save"
        )
        await completed(engine, "type", {"ref": title, "value": "Reference edit"})
        await completed(engine, "press", {"ref": save, "key": "Enter"})
        observed = cast(dict[str, Any], (await completed(engine, "snapshot", {})).output)
        assert "Reference edit" in observed["snapshot"] and title in observed["refs"]
        image = await completed(engine, "screenshot", {})
        assert base64.b64decode(image.images[0].data).startswith(b"\x89PNG\r\n\x1a\n")
        await completed(engine, "open", {"url": first.origin + "/next"})
        stale = await engine.execute("type", {"ref": title, "value": "must not retarget"}, "app")
        assert isinstance(stale, Failed), stale
        new = cast(dict[str, Any], (await completed(engine, "snapshot", {})).output)
        assert title not in new["refs"] and "Next page" in new["snapshot"]
        profile = engine._profiles["app"]
        agent = profile.agent
        assert agent is not None and agent.process.returncode is None
    finally:
        await engine.release_run("app")
    assert agent.process.returncode is not None
    assert isinstance(await engine.execute("open", {"url": first.origin}, "app"), Refused)


async def test_ref_inputs_are_exclusive_and_do_not_provision_on_malformed_input() -> None:
    engine = AgentBrowserEngine()
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
