"""A battery is a file (Phase 27 group 1, D70): a document naming an MCP server — or a Python
callable — the tools to expose under the harness's names, and the effects a deployment vouches
for. Consumed behind the component port, never built (principle 5); a registry over sources with
a store among them (D66); judged by the shipped modes as they are.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.kernel import EffectProfile
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.serve.batteries import (
    Battery,
    BatteryRegistry,
    batteries_in,
    battery_from_document,
    open_battery,
    shipped_batteries,
    store_batteries,
)

pytestmark = pytest.mark.anyio

REFERENCE_SERVER = Path(__file__).resolve().parents[1] / "adapters" / "mcp" / "server.py"


def _reference(**tools: dict[str, Any]) -> dict[str, Any]:
    """A battery over the test suite's own MCP server, exposing what `tools` says."""
    return {
        "battery": {
            "id": "reference",
            "name": "The reference server",
            "kind": "mcp",
            "command": sys.executable,
            "args": [str(REFERENCE_SERVER)],
        },
        "tools": tools,
    }


def test_a_battery_document_names_a_server_and_vouches_for_its_tools() -> None:
    battery = battery_from_document(
        _reference(
            web_search={"tool": "look_up", "effects": {"reaches": True, "contained": False}}
        ),
        source="test",
    )
    assert battery.id == "reference" and battery.kind == "mcp" and battery.source == "test"
    assert battery.command == sys.executable and battery.args == (str(REFERENCE_SERVER),)
    assert battery.tools["web_search"].tool == "look_up"
    assert battery.tools["web_search"].effects == EffectProfile(reaches=True, contained=False)
    for broken, why in (
        ({"battery": {"id": "x"}}, "kind"),
        ({"battery": {"id": "x", "kind": "mcp"}, "tools": {}}, "command"),
        ({"battery": {"id": "x", "kind": "python"}, "tools": {}}, "callable"),
        (_reference(web_search={"tool": "look_up"}), "effects"),
        (_reference(web_search={"tool": "look_up", "effects": {"reach": True}}), "reach"),
        ({"battery": {"id": "x", "kind": "spark", "command": "y"}, "tools": {}}, "spark"),
    ):
        with pytest.raises(ValueError, match=why):
            battery_from_document(broken, source="test")


def test_the_shipped_batteries_load_and_expose_the_web_under_the_harnesss_names() -> None:
    shipped = {b.id: b for b in shipped_batteries().load()}
    assert set(shipped) == {"wigolo", "ddgs"}
    assert shipped["wigolo"].kind == "mcp" and shipped["wigolo"].command == "wigolo"
    assert shipped["wigolo"].bin_env == "WIGOLO_BIN"
    assert set(shipped["wigolo"].tools) == {"web_search", "web_fetch"}
    assert shipped["wigolo"].tools["web_search"].tool == "search"
    assert "AGPL" in shipped["wigolo"].licence, "the licence is named where the file is read"
    assert shipped["ddgs"].kind == "python" and set(shipped["ddgs"].tools) == {"web_search"}
    for battery in shipped.values():
        for tool in battery.tools.values():
            # Honest: a battery is its own process, outside the environment's sandbox, and it
            # reaches the web — so a mode that requires containment refuses it by its profile.
            assert tool.effects.reaches and not tool.effects.contained
            assert tool.effects.writes.names == frozenset() and not tool.effects.writes.everything


async def test_a_registry_reads_shipped_files_a_directory_and_a_store(tmp_path: Path) -> None:
    (tmp_path / "mine.toml").write_text(
        '[battery]\nid = "mine"\nname = "Mine"\nkind = "mcp"\ncommand = "nothing-here"\n'
        '[tools.web_search]\ntool = "search"\neffects = { reaches = true, contained = false }\n',
        encoding="utf-8",
    )
    store = InMemoryStore()
    registry = BatteryRegistry(
        shipped_batteries(), sources=(batteries_in(tmp_path), store_batteries(store))
    )
    ids = [b.id for b in await registry.all()]
    assert ids == ["ddgs", "wigolo", "mine"], "shipped (by file name), then the directory"
    assert (await registry.find("mine")).source == "file"  # type: ignore[union-attr]
    # A row is a battery at the next read (D66) — and shadows a file with the same id.
    await store.put(
        "batteries",
        "mine",
        _reference(web_search={"tool": "look_up", "effects": {"reaches": True}})
        | {"battery": {**_reference()["battery"], "id": "mine"}},
    )
    found = await registry.find("mine")
    assert found is not None and found.source == "store" and found.command == sys.executable
    (tmp_path / "broken.toml").write_text("[battery]\nid = 'b'\n", encoding="utf-8")
    await registry.all()
    assert any("broken.toml" in p and "kind" in p for p in await registry.problems())


async def test_an_mcp_battery_exposes_only_the_named_tools_under_the_harnesss_names() -> None:
    battery = battery_from_document(
        _reference(
            web_search={"tool": "look_up", "effects": {"reaches": True, "contained": False}},
        ),
        source="test",
    )
    opened = await open_battery(battery)
    assert opened.problem is None and opened.port is not None
    try:
        registrations = await opened.port.registrations()
        names = sorted(r.id for r in registrations)
        assert names == ["web_search"], "only what the file names, under the file's names"
        (found,) = registrations
        assert found.component.effects == EffectProfile(reaches=True, contained=False)
        assert found.component.provenance.registered_by == "battery:reference"
        answer = await opened.port.invoke("web_search", {"topic": "lathe"})
        assert answer.kind == "completed"
        assert isinstance(answer.output, dict) and answer.output["asset"] == "LATHE-3"
    finally:
        await opened.close()


async def test_a_battery_whose_command_is_absent_is_a_reported_problem_not_an_absence(
    tmp_path: Path,
) -> None:
    document = _reference(web_search={"tool": "search", "effects": {"reaches": True}})
    document["battery"]["command"] = "no-such-binary-here"
    document["battery"]["bin_env"] = "NO_SUCH_BIN_HERE"
    document["battery"]["install"] = "npm i no-such-binary-here"
    battery = battery_from_document(document, source="test")
    opened = await open_battery(battery, env={})
    assert opened.port is None
    assert opened.problem is not None
    assert "no-such-binary-here" in opened.problem and "NO_SUCH_BIN_HERE" in opened.problem
    assert "npm i no-such-binary-here" in opened.problem, "what would fix it, in the words"
    # The environment variable names the binary where PATH does not.
    fake = tmp_path / "fake-server"
    fake.write_text("#!/bin/sh\nexec true\n", encoding="utf-8")
    fake.chmod(0o755)
    resolved = battery.resolve(env={"NO_SUCH_BIN_HERE": str(fake)})
    assert resolved == str(fake)


async def test_a_python_battery_is_a_callable_behind_the_same_port() -> None:
    battery = battery_from_document(
        {
            "battery": {
                "id": "py",
                "name": "A callable",
                "kind": "python",
                "callable": "tests.serve.test_a_battery_is_a_file:_echo",
            },
            "tools": {"echo": {"effects": {"reaches": False}}},
        },
        source="test",
    )
    opened = await open_battery(battery)
    assert opened.problem is None and opened.port is not None
    (found,) = await opened.port.registrations()
    assert found.id == "echo" and found.component.effects == EffectProfile()
    answer = await opened.port.invoke("echo", {"text": "hi"})
    assert answer.kind == "completed" and answer.output == {"echoed": "hi"}
    missing = battery_from_document(
        {
            "battery": {
                "id": "gone",
                "name": "",
                "kind": "python",
                "callable": "no_such_module:f",
                "requires": "no_such_module",
                "install": "pip install nothing",
            },
            "tools": {"f": {"effects": {}}},
        },
        source="test",
    )
    gone = await open_battery(missing)
    assert gone.port is None and gone.problem is not None
    assert "no_such_module" in gone.problem and "pip install nothing" in gone.problem


def _echo(text: str) -> dict[str, str]:
    return {"echoed": text}


def test_the_shipped_modes_judge_a_battery_by_its_profile_and_no_rule_is_added() -> None:
    """`workspace-write` requires containment and a battery is its own process: refused by the
    ceiling as it stands. `read-only` reads the web as it reads anything; `full` allows."""
    from shadow_hdk.serve.host import CONFINED, LOOKING, OPEN

    web = shipped_batteries().load()[0].tools["web_search"].effects
    assert not web.narrows(CONFINED.ceiling)
    assert web.narrows(LOOKING.ceiling)
    assert web.narrows(OPEN.ceiling)


def test_a_battery_is_immutable_data() -> None:
    battery = battery_from_document(
        _reference(web_search={"tool": "search", "effects": {"reaches": True}}), source="t"
    )
    assert isinstance(battery, Battery)
    with pytest.raises(AttributeError):
        battery.id = "other"  # type: ignore[misc]
