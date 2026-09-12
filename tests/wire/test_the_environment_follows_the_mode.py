"""The environment follows the mode (D76): a shipped mode names the sandbox mode it needs, and
`thread/set_mode` re-opens the environment — proven again — when that differs from the one open.
Before this, the selector flipped the policy while the sandbox stayed as opened, so `full` on a
workspace-write thread reached nothing more and the page said `full`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
import pytest

from shadow_hdk.adapters.environment.local import local_sandbox
from shadow_hdk.wire import connect_to, served_over_http
from tests.test_the_studio_example import StudioHost, _ports

pytestmark = pytest.mark.anyio
needs_sandbox = pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")


@needs_sandbox
async def test_set_mode_reopens_the_environment_in_the_mode_the_policy_needs(
    tmp_path: Path,
) -> None:
    host = StudioHost(tmp_path)
    with anyio.fail_after(90):
        async with served_over_http(threads=host) as address:
            async with connect_to(address, _ports()) as client:
                await client.initialize()
                started = await client.peer.call(
                    "thread/start", {"root": str(tmp_path), "mode": "ask"}
                )
                tid = started["thread_id"]
                assert started["mode"] == "ask" and started["environment"] == "workspace-write"

                def effects_of(tools: dict[str, Any], name: str) -> dict[str, Any]:
                    found: dict[str, Any] = next(t for t in tools["tools"] if t["id"] == name)
                    return dict(found["effects"])

                confined = await client.peer.call("tools/list", {"thread_id": tid})
                assert effects_of(confined, "write_file")["writes"]["names"] == ["workspace"]
                assert effects_of(confined, "write_file")["contained"] is True

                opened = await client.peer.call(
                    "thread/set_mode", {"thread_id": tid, "mode": "full"}
                )
                assert opened["environment"] == "full", "the sandbox followed the policy"
                wide = await client.peer.call("tools/list", {"thread_id": tid})
                assert effects_of(wide, "write_file")["writes"]["everything"] is True
                assert effects_of(wide, "write_file")["contained"] is False
                # `full` asks about a command that can now write anywhere and reach the network
                # (`write_file` has the studio host's pre-approving rule; `run_shell` has none).
                assert effects_of(wide, "run_shell")["reaches"] is True
                assert (
                    next(t for t in wide["tools"] if t["id"] == "run_shell")["judgement"] == "ask"
                )

                looking = await client.peer.call(
                    "thread/set_mode", {"thread_id": tid, "mode": "read-only"}
                )
                assert looking["environment"] == "read-only"
                narrow = await client.peer.call("tools/list", {"thread_id": tid})
                assert "write_file" not in {t["id"] for t in narrow["tools"]}, (
                    "a read-only environment does not even register a write"
                )
                listed = await client.peer.call("thread/list", {})
    assert listed["threads"][0]["environment"] == "read-only", "the record carries it"


async def test_a_mode_document_may_name_its_environment_and_defaults_to_its_policys(
    tmp_path: Path,
) -> None:
    from shadow_hdk.adapters.modes import mode_from_document

    spec = mode_from_document({"id": "careful", "policy": "ask"}, source="store")
    assert spec.environment == "workspace-write", "the policy's own"
    wide = mode_from_document(
        {"id": "wide-ask", "policy": "ask", "environment": "full"}, source="store"
    )
    assert wide.environment == "full"
    with pytest.raises(ValueError, match="environment"):
        mode_from_document({"id": "x", "policy": "ask", "environment": "boxed"}, source="store")
