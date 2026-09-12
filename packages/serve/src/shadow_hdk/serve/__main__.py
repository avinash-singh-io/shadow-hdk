"""`shadow-hdk serve [harness.toml] --stdio|--http [--port N] [--token T] [--page FILE]`.

The runtime with the shipped composition behind it, for a host in any language. `--stdio` is
newline-delimited JSON-RPC over stdin/stdout — Codex's default, what an editor or a desktop app
spawns; `--http` is the loopback listener with SSE, what a browser page or a service talks to. The
same `ServeHost` stands behind both. Diagnostics go to stderr; stdout is the wire.
"""

from __future__ import annotations

import sys
from pathlib import Path

import anyio

from shadow_hdk.serve.config import Settings, load_settings
from shadow_hdk.serve.host import ServeHost

USAGE = (
    "usage: shadow-hdk serve [harness.toml] --stdio | --http [--port N] [--token T] "
    "[--page FILE]"
)


def _flag(arguments: list[str], name: str, default: str = "") -> str:
    for argument in arguments:
        if argument.startswith(f"--{name}="):
            return argument.split("=", 1)[1]
    return default


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] != "serve":
        print(USAGE, file=sys.stderr)
        return 2
    rest = arguments[1:]
    words = [a for a in rest if not a.startswith("--")]
    settings = load_settings(words[0]) if words else Settings(root=Path.cwd())
    host = ServeHost(settings)
    if "--stdio" in rest:
        from shadow_hdk.wire.stdio import serve_stdio

        anyio.run(serve_stdio, host)
        return 0
    if "--http" in rest:
        from shadow_hdk.wire.serve import serve_http_forever

        page = _flag(rest, "page") or None
        anyio.run(
            serve_http_forever,
            host,
            int(_flag(rest, "port", "8765")),
            _flag(rest, "token") or None,
            Path(page) if page else None,
        )
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
