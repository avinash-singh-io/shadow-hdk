"""A runtime on stdio whose thread host is the scripted double — what a TypeScript sidecar spawns
in the suite, so the stdio proof crosses a real process boundary without needing a CLI."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


def main() -> None:
    from shadow_hdk.wire import serve_stdio
    from tests.wire.test_a_hosts_tools_cross_on_the_thread_door import ToolCallingThreads

    root = Path(sys.argv[1])
    threads = ToolCallingThreads(root, [("greet", {"name": "typescript"})])
    asyncio.run(serve_stdio(threads=threads))


if __name__ == "__main__":
    main()
