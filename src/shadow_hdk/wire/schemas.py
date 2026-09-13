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
from typing import Any

from shadow_hdk.kernel import Activity
from shadow_hdk.kernel.contracts import adapter_for, all_schemas
from shadow_hdk.runtime.items import Item
from shadow_hdk.wire.protocol import PROTOCOL_VERSION

HERE = Path(__file__).resolve()
DEFAULT = HERE.parents[5] / "schemas"
"""The repository's `schemas/` directory, five levels up from this file inside the package tree."""


def published() -> dict[str, dict[str, Any]]:
    """Everything the wire publishes: the kernel's contracts, plus what crosses only as a wire
    notification.

    The projection is a runtime type rather than a kernel contract — it is derived from the
    events, not a thing a host hands in — but it crosses as a `step` notification (D46) and a
    client in another language needs its shape as much as any kernel type's.
    """
    contracts: dict[str, dict[str, Any]] = dict(all_schemas())
    contracts["Item"] = adapter_for(Item).json_schema()
    contracts["Activity"] = adapter_for(Activity).json_schema()
    return contracts


def publish(into: Path | None = None) -> list[Path]:
    """Write one file per contract, plus an index naming the protocol they belong to."""
    where = into or DEFAULT
    where.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    contracts = published()
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
