"""`shadow-hdk serve [harness.toml] --stdio|--http [--port N] [--token T] [--page FILE]
[--root DIR] [--mode M] [--store FILE] [--provider P]`.

The runtime with the shipped composition behind it, for a host in any language. `--stdio` is
newline-delimited JSON-RPC over stdin/stdout — Codex's default, what an editor or a desktop app
spawns; `--http` is the loopback listener with SSE, what a browser page or a service talks to. The
same `ServeHost` stands behind both. Diagnostics go to stderr; stdout is the wire.

The settings come from the `harness.toml` named, or from flags, or both — a flag overrides the
file, so a launcher (the studio's `__main__`, a desktop app) need not write a file to pass a root.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import anyio

from shadow_hdk.serve.config import Settings, load_settings
from shadow_hdk.serve.host import ServeHost

USAGE = (
    "usage: shadow-hdk serve [harness.toml] --stdio | --http [--port N] [--token T] "
    "[--page FILE] [--root DIR] [--mode M] [--store FILE] [--provider P]"
)


VALUED = ("port", "token", "page", "root", "mode", "store", "provider")
"""Flags that take a value — as `--name=value` or `--name value`, the way every CLI takes them."""


def _flag(arguments: list[str], name: str, default: str = "") -> str:
    for index, argument in enumerate(arguments):
        if argument.startswith(f"--{name}="):
            return argument.split("=", 1)[1]
        if argument == f"--{name}" and index + 1 < len(arguments):
            return arguments[index + 1]
    return default


def _words(arguments: list[str]) -> list[str]:
    """The positional arguments: what is left once every flag, and the value it takes, is out."""
    words: list[str] = []
    skip = False
    for argument in arguments:
        if skip:
            skip = False
            continue
        if argument.startswith("--"):
            skip = argument.lstrip("-") in VALUED  # `--root ./work`: the next word is its value
            continue
        words.append(argument)
    return words


def settings_from(rest: list[str]) -> Settings:
    """The file first (if one is named), then each flag over it."""
    words = _words(rest)
    settings = load_settings(words[0]) if words else Settings(root=Path.cwd())
    if root := _flag(rest, "root"):
        settings = replace(settings, root=Path(root).resolve())
    if mode := _flag(rest, "mode"):
        if mode not in ("read-only", "workspace-write", "full"):
            raise ValueError(f"--mode={mode!r} is not read-only, workspace-write or full")
        settings = replace(settings, mode=mode)  # type: ignore[arg-type]
    if store := _flag(rest, "store"):
        settings = replace(settings, store=Path(store))
    if provider := _flag(rest, "provider"):
        settings = replace(settings, want=provider)
    return settings


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] != "serve":
        print(USAGE, file=sys.stderr)
        return 2
    rest = arguments[1:]
    settings = settings_from(rest)
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
