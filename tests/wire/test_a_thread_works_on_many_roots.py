"""A thread works on the roots a product names (D76): `thread/start {roots}`, a root added live
with `thread/add_root` (the proof re-run, the change on the record), and the files methods
across roots — over the real composition with a scripted provider.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
import pytest

from shadow_hdk.wire import connect_to, served_over_http
from tests.serve.test_serve_answers_a_host_in_any_language import ENFORCEABLE
from tests.test_the_studio_example import StudioHost, _ports

pytestmark = pytest.mark.anyio


def two(tmp_path: Path) -> tuple[Path, Path]:
    finance, sales = tmp_path / "finance", tmp_path / "sales"
    finance.mkdir()
    sales.mkdir()
    (finance / "revenue.csv").write_text("r\n", encoding="utf-8")
    (sales / "notes.md").write_text("n\n", encoding="utf-8")
    return finance, sales


async def test_a_thread_starts_on_two_roots_and_the_files_methods_span_them(
    tmp_path: Path,
) -> None:
    finance, sales = two(tmp_path)
    host = StudioHost(tmp_path)
    heard: list[dict[str, Any]] = []
    with anyio.fail_after(60):
        async with served_over_http(threads=host) as address:
            async with connect_to(address, _ports()) as client:
                await client.initialize()

                async def keep(params: dict[str, Any]) -> None:
                    heard.append(params["event"])

                client.peer.hears("event", keep)
                started = await client.peer.call(
                    "thread/start",
                    {
                        "roots": [
                            {"name": "finance", "path": str(finance)},
                            {"name": "sales", "path": str(sales)},
                        ],
                        "mode": ENFORCEABLE,
                    },
                )
                tid = started["thread_id"]
                assert started["root"] == str(finance), "the primary, for a one-root reader"
                assert [r["name"] for r in started["roots"]] == ["finance", "sales"]
                assert started["environment"] == ENFORCEABLE, (
                    "the sandbox's mode, beside the policy's"
                )
                listed = await client.peer.call("files/list", {"thread_id": tid})
                assert [(f["root"], f["path"]) for f in listed["files"]] == [
                    ("finance", "revenue.csv"),
                    ("sales", "notes.md"),
                ]
                read = await client.peer.call(
                    "files/read", {"thread_id": tid, "root": "sales", "path": "notes.md"}
                )
                assert read["content"] == "n\n"
                primary = await client.peer.call(
                    "files/read", {"thread_id": tid, "path": "revenue.csv"}
                )
                assert primary["content"] == "r\n", "no root named means the primary"
                with pytest.raises(Exception, match="no root"):
                    await client.peer.call(
                        "files/read", {"thread_id": tid, "root": "hr", "path": "x"}
                    )
                # The agent writes into the second root through its tools (scripted: hello.txt
                # into `sales/`), and the environment pane sees it there.
                await client.peer.call("turn/start", {"thread_id": tid, "text": "sales/hello.txt"})
                after = await client.peer.call("files/list", {"thread_id": tid})
    assert ("sales", "hello.txt") in [(f["root"], f["path"]) for f in after["files"]]
    assert (sales / "hello.txt").read_text(encoding="utf-8") == "hello"


async def test_a_root_is_added_live_and_the_change_is_on_the_record(tmp_path: Path) -> None:
    finance, sales = two(tmp_path)
    host = StudioHost(tmp_path)
    heard: list[dict[str, Any]] = []
    with anyio.fail_after(60):
        async with served_over_http(threads=host) as address:
            async with connect_to(address, _ports()) as client:
                await client.initialize()

                async def keep(params: dict[str, Any]) -> None:
                    heard.append(params["event"])

                client.peer.hears("event", keep)
                started = await client.peer.call(
                    "thread/start", {"root": str(finance), "mode": ENFORCEABLE}
                )
                tid = started["thread_id"]
                assert [r["name"] for r in started["roots"]] == ["finance"]
                with pytest.raises(Exception, match="not in the workspace"):
                    await client.peer.call(
                        "files/read", {"thread_id": tid, "root": "sales", "path": "notes.md"}
                    )
                added = await client.peer.call(
                    "thread/add_root", {"thread_id": tid, "name": "sales", "path": str(sales)}
                )
                assert [r["name"] for r in added["roots"]] == ["finance", "sales"]
                assert added["events"] and added["events"][0]["kind"] == "workspace_changed"
                read = await client.peer.call(
                    "files/read", {"thread_id": tid, "root": "sales", "path": "notes.md"}
                )
                assert read["content"] == "n\n"
                tools = await client.peer.call("tools/list", {"thread_id": tid})
                described = {t["id"]: t["description"] for t in tools["tools"]}
                assert "sales" in described["read_file"], "the tools say the new root"
                with pytest.raises(Exception, match="same name"):
                    await client.peer.call(
                        "thread/add_root", {"thread_id": tid, "name": "sales", "path": str(sales)}
                    )
                listed = await client.peer.call("thread/list", {})
    assert [k["kind"] for k in heard if k["kind"] == "workspace_changed"] == ["workspace_changed"]
    assert [r["name"] for r in listed["threads"][0]["roots"]] == ["finance", "sales"], (
        "the record carries the roots"
    )
