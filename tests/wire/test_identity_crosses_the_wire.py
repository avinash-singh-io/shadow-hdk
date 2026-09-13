"""Identity on the thread, scope on the rows — across the wire (Phase 29 group 3, D82).

`thread/start {principal, attributes}` puts them on the record a page reads back; `rules/list`
and `modes/list` answer everything for the operator and, given a `thread_id`, only what is in
that thread's scope — so a product's page shows a person the rules and modes that are theirs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.sides import loopback
from tests.serve.test_serve_answers_a_host_in_any_language import ScriptedProvider

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"


async def test_the_thread_carries_its_identity_and_the_registries_answer_in_scope(
    tmp_path: Path,
) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            await client.peer.call(
                "store/put",
                {
                    "collection": "rules",
                    "key": "alice-writes",
                    "row": {"component": "write_file", "scope": "alice"},
                },
            )
            await client.peer.call(
                "store/put",
                {
                    "collection": "rules",
                    "key": "acme-no-shell",
                    "row": {"component": "run_shell", "decision": "deny", "scope": "tenant:acme"},
                },
            )
            await client.peer.call(
                "store/put",
                {"collection": "rules", "key": "anyone", "row": {"component": "read_file"}},
            )
            await client.peer.call(
                "store/put",
                {
                    "collection": "modes",
                    "key": "acme-open",
                    "row": {
                        "id": "acme-open",
                        "policy": "full",
                        "environment": "full",
                        "scope": "tenant:acme",
                    },
                },
            )

            started = await client.peer.call(
                "thread/start",
                {
                    "root": "",
                    "mode": "",
                    "name": "",
                    "principal": "bob",
                    "attributes": {"tenant": "beta"},
                },
            )
            tid = started["thread_id"]
            assert started["principal"] == "bob" and started["attributes"] == {"tenant": "beta"}
            assert "acme-open" not in [m["id"] for m in started["modes"]], "not bob's"

            listed = await client.peer.call("thread/list", {})
            (row,) = [t for t in listed["threads"] if t["id"] == tid]
            assert row["principal"] == "bob" and row["attributes"] == {"tenant": "beta"}

            everything = await client.peer.call("rules/list", {})
            assert sorted(r["component"] for r in everything["rules"]) == [
                "read_file",
                "run_shell",
                "write_file",
            ]
            bobs = await client.peer.call("rules/list", {"thread_id": tid})
            assert [r["component"] for r in bobs["rules"]] == ["read_file"]

            modes = await client.peer.call("modes/list", {})
            assert "acme-open" in [m["id"] for m in modes["modes"]]
            bobs_modes = await client.peer.call("modes/list", {"thread_id": tid})
            assert "acme-open" not in [m["id"] for m in bobs_modes["modes"]]

            with pytest.raises(RemoteError, match="acme-open"):
                await client.peer.call("thread/set_mode", {"thread_id": tid, "mode": "acme-open"})

            acme = await client.peer.call(
                "thread/start",
                {
                    "root": "",
                    "mode": "",
                    "name": "",
                    "principal": "eve",
                    "attributes": {"tenant": "acme"},
                },
            )
            eves = await client.peer.call("rules/list", {"thread_id": acme["thread_id"]})
            assert sorted(r["component"] for r in eves["rules"]) == ["read_file", "run_shell"]
            assert "acme-open" in [m["id"] for m in acme["modes"]]

            with pytest.raises(RemoteError, match="component"):
                await client.peer.call(
                    "thread/start",
                    {"root": "", "mode": "", "name": "", "attributes": {"component": "x"}},
                )

            resumed_id = tid
            await client.peer.call("thread/close", {"thread_id": tid})
            resumed = await client.peer.call("thread/resume", {"thread_id": resumed_id})
            assert resumed["principal"] == "bob" and resumed["attributes"] == {"tenant": "beta"}
    finally:
        await host.aclose()


def _unused(_: Any) -> None:  # pragma: no cover
    return None
