"""Batteries live (Phase 29 group 4, D83).

What is wanted is rows: `[tools] batteries` seeds the store's `wanted` collection at the host's
first open (`{id, on}`; a row already there is left as it is), and from then on the store says
which batteries the next thread gets — `store/put wanted <id> {"id", "on"}` switches one on or
off without a restart, the way a mode or a rule is written (D66). A battery switched on is
opened at the next thread that wants it and held for the process; one switched off is closed at
the next thread's open — for every thread, because a battery's server is the process's, not a
thread's: a thread already open sees its tools go too.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
import pytest

from shadow_hdk.serve.config import Settings
from tests.serve.test_batteries_in_the_composition import (
    LOOKING,
    BatteryHost,
    _reference_battery,
)

pytestmark = pytest.mark.anyio


def _host(tmp_path: Path, *wanted: str) -> BatteryHost:
    return BatteryHost(
        Settings(
            root=tmp_path / "ws",
            mode=LOOKING,
            batteries=wanted,
            batteries_dir=_reference_battery(tmp_path / "batteries"),
            store=f"sqlite:///{tmp_path}/live.sqlite",
        )
    )


async def _ids(host: Any) -> dict[str, str]:
    return {b["id"]: b["status"] for b in await host.battery_listing()}


async def test_the_file_seeds_the_rows_and_the_rows_decide_the_next_thread(tmp_path: Path) -> None:
    host = _host(tmp_path, "reference")
    try:
        with anyio.fail_after(60):
            first = await host.open(root="", mode=LOOKING, want=None, name="tools", observer=None)
            try:
                assert await host.store.get("wanted", "reference") == {
                    "id": "reference",
                    "on": True,
                }
                assert (await _ids(host))["reference"] == "on"
                assert "web_search" in [o.registration.id for o in await first.tools()]
                opened = [b for b in host.batteries_opened if b.battery.id == "reference"]
                assert len(opened) == 1 and opened[0].port is not None

                # Switched off in the store: the next thread does not get it, and its server is
                # closed — for the thread already open too, whose port is the same server.
                await host.store.put("wanted", "reference", {"id": "reference", "on": False})
                second = await host.open(
                    root="", mode=LOOKING, want=None, name="tools", observer=None
                )
                try:
                    assert "web_search" not in [o.registration.id for o in await second.tools()]
                    assert (await _ids(host))["reference"] == "off"
                    assert not [b for b in host.batteries_opened if b.battery.id == "reference"]
                    assert await opened[0].port.registrations() == [], "its session is gone"
                    assert "web_search" not in [o.registration.id for o in await first.tools()]
                finally:
                    await second.close()
            finally:
                await first.close()
    finally:
        await host.aclose()


async def test_a_battery_switched_on_by_a_row_alone_is_opened_at_the_next_thread(
    tmp_path: Path,
) -> None:
    host = _host(tmp_path)  # the file wants nothing
    try:
        with anyio.fail_after(60):
            first = await host.open(root="", mode=LOOKING, want=None, name="tools", observer=None)
            try:
                assert (await _ids(host))["reference"] == "off"
                assert "web_search" not in [o.registration.id for o in await first.tools()]
            finally:
                await first.close()
            await host.store.put("wanted", "reference", {"id": "reference", "on": True})
            second = await host.open(root="", mode=LOOKING, want=None, name="tools", observer=None)
            try:
                assert (await _ids(host))["reference"] == "on"
                assert "web_search" in [o.registration.id for o in await second.tools()]
            finally:
                await second.close()
    finally:
        await host.aclose()


async def test_a_row_written_before_the_first_open_is_not_overwritten_by_the_file(
    tmp_path: Path,
) -> None:
    """The file seeds; the store rules. A product that switched a battery off before the host
    ever opened keeps it off."""
    host = _host(tmp_path, "reference")
    try:
        await host.store.put("wanted", "reference", {"id": "reference", "on": False})
        with anyio.fail_after(60):
            thread = await host.open(root="", mode=LOOKING, want=None, name="tools", observer=None)
            try:
                assert await host.store.get("wanted", "reference") == {
                    "id": "reference",
                    "on": False,
                }
                assert (await _ids(host))["reference"] == "off"
                assert "web_search" not in [o.registration.id for o in await thread.tools()]
            finally:
                await thread.close()
    finally:
        await host.aclose()


async def test_a_row_naming_no_battery_is_reported_not_fatal(tmp_path: Path) -> None:
    host = _host(tmp_path)
    try:
        await host.store.put("wanted", "nowhere", {"id": "nowhere", "on": True})
        with anyio.fail_after(60):
            thread = await host.open(root="", mode=LOOKING, want=None, name="tools", observer=None)
            try:
                listed = {b["id"]: b for b in await host.battery_listing()}
                assert listed["nowhere"]["status"] == "unavailable"
                assert "no battery" in listed["nowhere"]["problem"]
            finally:
                await thread.close()
    finally:
        await host.aclose()
