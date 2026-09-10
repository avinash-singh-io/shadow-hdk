"""The registry, used by a child in another OS process.

The wire tests next door prove the protocol over an in-memory stream pair, which shares a heap, a
task group and an interpreter with the thing it is talking to. This proves the part none of that
touches: a real process, real pipes, and a child that has no way to reach into our run except by
asking for a tool — which is the arrangement the whole design is for.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest
from shadow_hdk.adapters.recording import RecordingServer, serve_over_pipes

from shadow_hdk.kernel import Event, Invoked, Observed
from shadow_hdk.kernel.ports import GovernancePort
from shadow_hdk.runtime import RunContext

from .conftest import with_a_run
from .test_recording import READING, mode

CHILD = Path(__file__).resolve().parents[3] / "spikes" / "mcp" / "child.py"


async def with_a_child(
    *,
    governance: GovernancePort | None = None,
) -> tuple[dict[str, Any], list[Event]]:
    """Spawn the child, serve our registry over its pipes, and give back what it said it saw."""

    async def drive(context: RunContext) -> dict[str, Any]:
        said: list[bytes] = []
        async with RecordingServer(context).served() as server:
            process = await anyio.open_process(
                [sys.executable, str(CHILD)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            async with process, anyio.create_task_group() as group:

                async def drain() -> None:
                    assert process.stderr is not None
                    async for chunk in process.stderr:
                        said.append(chunk)

                group.start_soon(drain)
                # Its own bound: a child that never speaks would otherwise hang the suite, and a
                # test whose subject is a process needs a deadline it owns.
                with anyio.fail_after(45):
                    assert process.stdout is not None and process.stdin is not None
                    await serve_over_pipes(server, process.stdout, process.stdin)
                    assert await process.wait() == 0, "the child did not exit cleanly"
                group.cancel_scope.cancel()
        report: dict[str, Any] = json.loads(b"".join(said).decode().strip().splitlines()[-1])
        return report

    return await with_a_run(drive, governance=governance, steps=40)


@pytest.mark.anyio
async def test_a_child_process_uses_the_parents_registry() -> None:
    said, events = await with_a_child()
    assert said["tools"] == ["breaks", "driver", "look", "wipe"]
    assert said["look_is_error"] is False
    assert said["look"] == '{"found": {"topic": "lathe"}}'

    invoked = [e for e in events if isinstance(e, Invoked) and e.component == "look"]
    observed = [e for e in events if isinstance(e, Observed) and e.step != "s1"]
    assert len(invoked) == 1, "another process called a tool and the parent has no record of it"
    assert observed, "the child's answer never reached the parent's stream"
    assert invoked[0].run_id != events[0].run_id, "it should carry the child run id"


@pytest.mark.anyio
async def test_a_narrowing_mode_reaches_across_the_process_boundary() -> None:
    """The mode is the only thing between our registry and another process. `wipe` writes
    irreversibly, so a reading mode both hides it and refuses it — with no code in between."""
    said, _ = await with_a_child(governance=mode(READING))
    assert "wipe" not in said["tools"]
    assert said["wipe_is_error"] is True
    assert "refused" in said["wipe"]
