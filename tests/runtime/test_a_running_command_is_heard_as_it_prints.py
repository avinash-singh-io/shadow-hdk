"""A running command's output is activity as it prints, not only a result when it ends (D63).

The snake game's harness ran for minutes with nothing on screen. `run_leashed` collected both
streams to the end and handed back the whole; now it also hands each chunk to `on_output` as it
arrives — and the local environment turns that into `output` activity on the run — while the
result it returns is unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.kernel import Activity, Completed, Event
from shadow_hdk.runtime.leash import run_leashed

pytestmark = pytest.mark.anyio

SCRIPT = "import sys, time; print('one', flush=True); time.sleep(0.4); print('two', flush=True)"


async def test_each_chunk_reaches_on_output_before_the_command_ends(tmp_path: Path) -> None:
    heard: list[tuple[str, bool]] = []  # (chunk, was the command still running?)
    finished = {"yes": False}

    def on_output(chunk: str) -> None:
        heard.append((chunk, not finished["yes"]))

    done = await run_leashed(
        [sys.executable, "-c", SCRIPT],
        cwd=tmp_path,
        timeout_s=10,
        output_limit=10_000,
        on_output=on_output,
    )
    finished["yes"] = True

    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert done.output["stdout"] == "one\ntwo\n", "the result is unchanged"
    text = "".join(chunk for chunk, _ in heard)
    assert text == "one\ntwo\n"
    assert len(heard) >= 2, "two flushes 400ms apart must arrive as two chunks, not one at the end"
    assert all(live for _, live in heard), "every chunk arrived while the command was running"


async def test_the_local_environment_turns_output_into_activity(tmp_path: Path) -> None:
    from shadow_hdk.adapters.environment import LocalEnvironment
    from shadow_hdk.kernel import (
        Binding,
        Ceiling,
        Composition,
        EffectProfile,
        Floor,
        Invoke,
        Lease,
    )
    from shadow_hdk.kernel.ports import Allow, Context, Judgement
    from shadow_hdk.runtime import Ports, RunOptions, run
    from shadow_hdk.runtime.testing import FixedClock, ListSink

    class Watching:
        def __init__(self) -> None:
            self.activity: list[Activity] = []

        async def on(self, event: Event) -> None:
            pass

        async def on_activity(self, activity: Activity) -> None:
            self.activity.append(activity)

    class AllowAll:
        async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
            return Allow()

    root = tmp_path / "ws"
    root.mkdir()
    env = await LocalEnvironment.open(root, mode="full")
    watching = Watching()
    ports = Ports(
        model=None,
        components=(env,),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=watching,
    )
    plan = Composition(
        (Invoke("s1", "run_python", (Binding("source", value=SCRIPT),)),),
    )
    events: list[Any] = [
        e
        async for e in run(
            plan, ports, options=RunOptions(lease=Lease(Ceiling(5, 60, None), Floor(0)))
        )
    ]

    assert events[-1].kind == "ended" and events[-1].reason == "completed"
    assert [a.kind for a in watching.activity] and all(
        a.kind == "output" and a.step == "s1" for a in watching.activity
    )
    assert "".join(a.text for a in watching.activity) == "one\ntwo\n"
