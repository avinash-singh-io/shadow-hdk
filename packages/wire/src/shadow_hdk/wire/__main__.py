"""`python -m shadow_hdk.wire --stdio` — the runtime, as somebody's child process."""

from __future__ import annotations

import sys

import anyio

from shadow_hdk.wire.stdio import serve_stdio


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--stdio" not in arguments:
        print("usage: python -m shadow_hdk.wire --stdio", file=sys.stderr)
        return 2
    anyio.run(serve_stdio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
