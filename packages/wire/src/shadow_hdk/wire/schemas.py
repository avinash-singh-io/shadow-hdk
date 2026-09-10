"""Publish the contracts as files a client can be generated from.

`wire.md`: *schemas are published from `shadow_hdk.kernel.contracts.all_schemas()`; a TypeScript
client is generated from them and is a **client**, never a port of the runtime (`09` §3b).*

That distinction is the reason this exists at all. A generated client speaks the protocol; it does
not *implement* a port, because a port is a seam where the host owns something — and a host owns
that side in whatever language it likes. What it needs from us is an exact description of what
crosses, which is what these files are.

They are checked in as well as generated, and a test compares the two. A schema on disk that has
drifted from the code is worse than none, because it looks authoritative.

    uv run python -m shadow_hdk.wire.schemas
"""

from __future__ import annotations

import json
from pathlib import Path

from shadow_hdk.kernel.contracts import all_schemas
from shadow_hdk.wire.protocol import PROTOCOL_VERSION

HERE = Path(__file__).resolve()
DEFAULT = HERE.parents[5] / "schemas"
"""The repository's `schemas/` directory, five levels up from this file inside the package tree."""


def publish(into: Path | None = None) -> list[Path]:
    """Write one file per contract, plus an index naming the protocol they belong to."""
    where = into or DEFAULT
    where.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    contracts = all_schemas()
    for name, schema in sorted(contracts.items()):
        path = where / f"{name}.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    index = where / "index.json"
    index.write_text(
        json.dumps(
            {
                "protocol_version": PROTOCOL_VERSION,
                "contracts": sorted(contracts),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(index)
    return written


def main() -> int:
    written = publish()
    print(f"published {len(written) - 1} contracts and an index to {written[0].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
