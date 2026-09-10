"""Shutting the listener down prints nothing (BUG-017).

`served_over_http` cancelled uvicorn mid-`serve`, which left uvicorn's own tasks to be torn down by
force. One of them surfaced the cancellation as an **unretrieved exception**, and the loop printed
it at teardown — a full `asyncio.exceptions.CancelledError` traceback on the way out of a context
manager that had done nothing wrong.

It is harmless and it is the first thing anybody driving the wire sees, which is the whole problem:
a traceback on a clean exit teaches a reader to ignore tracebacks.

**Why no existing test caught it.** Every wire test runs under pytest's anyio runner, which owns
the loop and absorbs the unretrieved exception; the leak is only visible to a program that calls
`asyncio.run` itself — which is to say, to every program that is not a test. So this one runs the
listener in a **subprocess under plain `asyncio.run`** and reads what the process wrote, because
the claim is about what a reader sees, and nothing inside this process can see it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DRIVES_THE_LISTENER = """
import asyncio

from shadow_hdk.wire.serve import served_over_http


async def main() -> None:
    async with served_over_http() as address:
        assert address.startswith("http://127.0.0.1:"), address


asyncio.run(main())
print("left cleanly")
"""


def run_it(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """A listener started and stopped inside one short-lived process, on loopback."""
    script = tmp_path / "drives_the_listener.py"
    script.write_text(DRIVES_THE_LISTENER, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=120, check=False
    )


def test_the_listener_shuts_down_without_printing_a_traceback(tmp_path: Path) -> None:
    """The bug, at the size a reader met it."""
    finished = run_it(tmp_path)

    assert "left cleanly" in finished.stdout, finished.stderr
    assert "Traceback" not in finished.stderr, f"the exit printed a traceback:\n{finished.stderr}"
    assert "CancelledError" not in finished.stderr, finished.stderr


def test_the_process_exits_zero(tmp_path: Path) -> None:
    """An unretrieved exception does not fail the process, so the exit code is a **separate**
    claim from the one above rather than a restatement of it: a fix that quietened the loop by
    swallowing a real shutdown failure would still have to answer this."""
    finished = run_it(tmp_path)

    assert finished.returncode == 0, finished.stderr


def test_the_port_is_let_go(tmp_path: Path) -> None:
    """The reason the fix waits rather than only asking: `should_exit` without the wait returns
    while uvicorn is still closing its sockets. Two listeners in one process, in sequence, is what
    catches a shutdown that had not finished when it said it had."""
    script = tmp_path / "twice.py"
    script.write_text(
        "import asyncio\n\nfrom shadow_hdk.wire.serve import served_over_http\n\n\n"
        "async def main() -> None:\n"
        "    seen = []\n"
        "    for _ in range(2):\n"
        "        async with served_over_http() as address:\n"
        "            seen.append(address)\n"
        "    print(len(seen))\n\n\n"
        "asyncio.run(main())\n",
        encoding="utf-8",
    )
    finished = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=120, check=False
    )

    assert finished.stdout.strip() == "2", finished.stderr
    assert "Traceback" not in finished.stderr, finished.stderr
