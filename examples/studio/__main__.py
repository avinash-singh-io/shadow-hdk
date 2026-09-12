"""Run the studio: `shadow-hdk serve --http` with the page, and the flags this example has
always taken. See the package docstring."""

from __future__ import annotations

import sys
from pathlib import Path

from shadow_hdk.serve.__main__ import main as serve

PAGE = Path(__file__).resolve().parent / "page.html"


def _flag(arguments: list[str], name: str, default: str) -> str:
    for argument in arguments:
        if argument.startswith(f"--{name}="):
            return argument.split("=", 1)[1]
    return default


def serve_arguments(arguments: list[str]) -> list[str]:
    """What `python -m examples.studio [workspace] [--mode=] [--store=] [--port=] [--provider=]`
    hands to `shadow-hdk serve`: the page, and every flag as the flag it already is."""
    words = [a for a in arguments if not a.startswith("--")]
    root = words[0] if words else "./studio-workspace"
    handed = [
        "serve",
        "--http",
        f"--port={_flag(arguments, 'port', '8765')}",
        f"--page={PAGE}",
        f"--root={root}",
        f"--mode={_flag(arguments, 'mode', 'workspace-write')}",
    ]
    if store := _flag(arguments, "store", ""):
        handed.append(f"--store={store}")
    if provider := _flag(arguments, "provider", ""):
        handed.append(f"--provider={provider}")
    return handed


if __name__ == "__main__":
    handed = serve_arguments(sys.argv[1:])
    print(
        f"studio: http://127.0.0.1:{_flag(handed, 'port', '8765')}  "
        f"workspace={_flag(handed, 'root', '')}  mode={_flag(handed, 'mode', '')}",
        file=sys.stderr,
    )
    sys.exit(serve(handed))
