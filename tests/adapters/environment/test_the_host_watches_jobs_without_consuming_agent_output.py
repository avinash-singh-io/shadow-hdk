"""The person's workspace door has no model, and each job reader owns its cursor."""

import asyncio
import contextlib
import shlex
import sys
from pathlib import Path
from typing import Any, cast

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.adapters.workbench import HostDoor, LocalProcessListeners, WorkbenchComponents
from shadow_hdk.kernel import Completed, Ended, Refused
from shadow_hdk.runtime.environment import _Job


def data(result: Any) -> Any:
    assert isinstance(result, Completed), result
    return result.output


async def eventually_output(door: HostDoor, job: str, text: str) -> dict[str, Any]:
    async def wait() -> dict[str, Any]:
        while True:
            result = cast(dict[str, Any], data(await door.output(job)))
            if text in result["output"]:
                return result
            await asyncio.sleep(0.01)

    # No inner deadline (TD-018, sixth instance). This waits on a fresh interpreter starting,
    # importing and binding a socket, which took longer than five seconds on a loaded macOS
    # runner and failed a release gate for being slow rather than wrong. The suite's own
    # per-test timeout is the hang guard and is far above anything healthy here, so a second
    # tighter clock only converts a busy machine into a red run.
    return await wait()


async def test_host_and_agent_readers_share_a_job_but_never_consume_each_others_output(
    tmp_path: Path,
) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full", output_limit=64)
    door = HostDoor(environment)
    try:
        source = "import time; print('begin', flush=True); time.sleep(300)"
        started = data(
            await door.background(f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}")
        )
        job = started["job"]
        first = await eventually_output(door, job, "begin")
        assert (first["output"], first["cursor"], first["truncated"]) == ("begin\n", 6, False)
        assert data(await environment.invoke("job_output", {"job": job}))["output"] == "begin\n"
        assert data(await door.output(job, cursor=0))["output"] == "begin\n"
        assert data(await door.output(job, cursor=6))["output"] == ""
        jobs = data(await door.jobs())["jobs"]
        assert [(j["job"], j["pid"], j["running"], j["exit_code"]) for j in jobs] == [
            (job, started["pid"], True, None)
        ]
        assert data(await door.stop(job))["killed"] is True
        process = environment._jobs[job].process
        await process.wait()
        assert data(await door.jobs())["jobs"][0]["running"] is False
        assert data(await door.jobs())["jobs"][0]["exit_code"] != 0
        assert isinstance(await door.output("someone-elses-job"), Refused)
    finally:
        await environment.close()


async def test_output_cursors_survive_truncation_and_paginate_without_silent_loss(
    tmp_path: Path,
) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full", output_limit=10)
    door = HostDoor(environment)
    try:
        source = "print('0123456789abcdef', end='', flush=True)"
        job = data(
            await door.background(f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}")
        )["job"]
        first = await eventually_output(door, job, "abcdef")
        assert (first["start"], first["cursor"], first["output"], first["truncated"]) == (
            6,
            16,
            "6789abcdef",
            True,
        )
        page = data(await door.output(job, cursor=8, limit=3))
        assert (page["output"], page["cursor"], page["more"], page["truncated"]) == (
            "89a",
            11,
            True,
            False,
        )
        assert isinstance(await door.output(job, cursor=1000), Refused)
        assert isinstance(await door.output(job, cursor=-1), Refused)
    finally:
        await environment.close()


async def test_the_person_runs_and_reads_in_the_same_copy_without_an_agent(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    door = HostDoor(environment)
    try:
        data(await door.run("printf 'from the person' > person.txt"))
        assert data(await door.read("person.txt")) == "from the person"
        assert environment.root == tmp_path.resolve()
        pack = WorkbenchComponents(door)
        assert {r.id for r in await pack.registrations()} == {
            "list_jobs",
            "read_job",
            "test_results",
        }
    finally:
        await environment.close()


async def test_a_silent_server_has_a_verified_listener_instead_of_a_guessed_url(
    tmp_path: Path,
) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    door = HostDoor(environment, listeners=LocalProcessListeners())
    try:
        source = (
            "from http.server import HTTPServer, SimpleHTTPRequestHandler; "
            "s=HTTPServer(('127.0.0.1',0),SimpleHTTPRequestHandler); "
            "print('ready',flush=True); s.serve_forever()"
        )
        job = data(
            await door.background(f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}")
        )["job"]
        await eventually_output(door, job, "ready")
        addresses = data(await door.jobs())["jobs"][0]["addresses"]
        assert len(addresses) == 1 and addresses[0]["verified"] is True
        assert (addresses[0]["host"], addresses[0]["source"], addresses[0]["protocol"]) == (
            "127.0.0.1",
            "listener",
            "tcp",
        )
        reader, writer = await asyncio.open_connection("127.0.0.1", addresses[0]["port"])
        try:
            writer.write(b"GET / HTTP/1.0\r\n\r\n")
            await writer.drain()
            assert b"200" in await reader.readline()
        finally:
            writer.close()
            await writer.wait_closed()
    finally:
        await environment.close()


async def test_split_utf8_is_decoded_once_and_cursors_count_characters() -> None:
    class Stream:
        chunks = iter((b"\xf0\x9f", b"\x98\x80!"))

        async def read(self, size: int) -> bytes:
            return next(self.chunks, b"")

    class Process:
        pid = 1
        returncode = 0
        stdout = Stream()
        stderr = None

    job = _Job("test", "unicode", Process())
    job.start_reading(10)
    await job.reader
    result = job.observe(0, 10)
    assert (result["output"], result["cursor"]) == ("😀!", 2)


async def test_stopping_an_exited_leader_still_ends_its_owned_child(tmp_path: Path) -> None:
    import psutil

    environment = await LocalEnvironment.open(tmp_path, mode="full")
    door = HostDoor(environment)
    child = None
    try:
        source = (
            "import subprocess; p=subprocess.Popen(['sleep','300'], "
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)"
        )
        job = data(
            await door.background(f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}")
        )["job"]
        process = environment._jobs[job].process
        await process.wait()
        await environment._jobs[job].reader
        child = psutil.Process(int(data(await door.output(job))["output"].strip()))
        assert child.is_running() and child.status() != psutil.STATUS_ZOMBIE
        stopped = data(await door.stop(job))
        assert stopped["killed"] is False, "the leader was already done"

        async def gone() -> bool:
            for _ in range(100):
                if not child.is_running() or child.status() == psutil.STATUS_ZOMBIE:
                    return True
                await asyncio.sleep(0.01)
            return False

        assert await gone(), "stop must also end descendants after the leader exits"
    finally:
        if child is not None and child.is_running():
            with contextlib.suppress(psutil.NoSuchProcess):
                child.kill()
        await environment.close()


async def test_workbench_reads_are_governed_and_reports_use_the_same_confined_file_door(
    tmp_path: Path,
) -> None:
    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.kernel import Binding, Ceiling, Composition, Floor, Invoke, Lease
    from shadow_hdk.runtime import Ports, RunOptions, run
    from shadow_hdk.runtime.testing import FixedClock, ListSink

    environment = await LocalEnvironment.open(tmp_path, mode="full")
    door = HostDoor(environment)
    pack = WorkbenchComponents(door)
    (tmp_path / "report.xml").write_text('<testsuite tests="1"><testcase name="real"/></testsuite>')
    try:
        events = [
            e
            async for e in run(
                Composition(
                    (Invoke("tests", "test_results", (Binding("path", value="report.xml"),)),)
                ),
                Ports(
                    components=(pack,), governance=AllowAll(), sink=ListSink(), clock=FixedClock()
                ),
                options=RunOptions(lease=Lease(Ceiling(10, 60, 0), Floor(0))),
            )
        ]
        observed = [e.observation for e in events if e.kind == "observed"]
        assert (
            data(observed[0])["passed"] == 1
            and isinstance(events[-1], Ended)
            and events[-1].reason == "completed"
        )
        assert [(e.component, e.inputs) for e in events if e.kind == "invoked"] == [
            ("test_results", {"path": "report.xml"})
        ]
        assert isinstance(await pack.invoke("test_results", {"path": "../outside.xml"}), Refused)
        for operation, inputs in (
            ("list_jobs", {"ignored": True}),
            ("read_job", {"job": "missing", "cursor": True}),
            ("read_job", {"job": "missing", "ignored": True}),
            ("test_results", {"path": "report.xml", "ignored": True}),
            ("unknown", {}),
        ):
            assert isinstance(await pack.invoke(operation, cast(Any, inputs)), Refused)
    finally:
        await environment.close()
