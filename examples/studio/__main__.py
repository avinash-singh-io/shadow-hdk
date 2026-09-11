"""Run the studio. See the package docstring."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import uvicorn

from examples.studio.app import NoProvider, Studio, build_app
from shadow_hdk.runtime.environment import CannotEnforce, Mode


def flag(name: str, default: str) -> str:
    for arg in sys.argv[1:]:
        if arg.startswith(f"--{name}="):
            return arg.split("=", 1)[1]
    return default


async def main() -> int:
    words = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(words[0] if words else "./studio-workspace").resolve()
    root.mkdir(parents=True, exist_ok=True)
    mode: Mode = flag("mode", "workspace-write")  # type: ignore[assignment]
    port = int(flag("port", "8765"))
    studio = Studio(root=root, mode=mode, want=flag("provider", "") or None)
    try:
        await studio.open()
    except NoProvider as nothing:
        print(nothing, file=sys.stderr)
        return 2
    except CannotEnforce as cannot:
        print(cannot, file=sys.stderr)
        return 3
    print(f"studio: http://127.0.0.1:{port}  workspace={root}  mode={mode}")
    # A page left open holds an SSE stream, and uvicorn's graceful shutdown waits for open
    # connections for ever by default — which kept the provider's process alive after a SIGTERM
    # until the tab was closed (measured). Two seconds, then the process ends and, with it, the
    # provider (D53).
    config = uvicorn.Config(
        build_app(studio),
        host="127.0.0.1",
        port=port,
        log_level="warning",
        timeout_graceful_shutdown=2,
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        await studio.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
