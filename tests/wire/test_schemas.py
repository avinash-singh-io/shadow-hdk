"""The schemas a client is generated from, and a test that they are not stale.

`wire.md`: *schemas are published from `shadow_hdk.kernel.contracts.published()`; a TypeScript
client is generated from them and is a **client**, never a port of the runtime (`09` §3b).*

Publishing them as files is the easy half. The half that matters is that a file on disk and the code
that produced it cannot drift: a generated client is only as true as the schema it was generated
from, and a stale schema is worse than no schema because it looks authoritative.

So the files are checked in **and** checked. If a contract changes and nobody regenerates, this
fails and says which one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadow_hdk.wire.schemas import published

PUBLISHED = Path(__file__).resolve().parents[2] / "schemas"


def test_every_contract_is_published() -> None:
    on_disk = {path.stem for path in PUBLISHED.glob("*.json")} - {"index"}
    assert on_disk == set(published()), (
        "the published schemas and the code disagree about which contracts exist; "
        "run `uv run python -m shadow_hdk.wire.schemas` to republish"
    )


@pytest.mark.parametrize("name", sorted(published()))
def test_a_published_schema_matches_the_code_that_made_it(name: str) -> None:
    """The whole point. A generated client is only as true as the schema it came from."""
    on_disk = json.loads((PUBLISHED / f"{name}.json").read_text(encoding="utf-8"))
    assert on_disk == published()[name], (
        f"{name}.json is stale; run `uv run python -m shadow_hdk.wire.schemas`"
    )


def test_the_index_names_the_protocol_it_belongs_to() -> None:
    """A schema set with no version is a set nobody can tell apart from the next one."""
    from shadow_hdk.wire import PROTOCOL_VERSION

    index = json.loads((PUBLISHED / "index.json").read_text(encoding="utf-8"))
    assert index["protocol_version"] == PROTOCOL_VERSION
    assert sorted(index["contracts"]) == sorted(published())


TWELVE = (
    "started",
    "composed",
    "invoked",
    "observed",
    "proposed",
    "refused",
    "approval_requested",
    "input_requested",
    "spawned",
    "held",
    "usage",
    "reasoning",
    "ended",
)


@pytest.mark.parametrize("kind", TWELVE)
def test_the_event_schema_carries_every_kind(kind: str) -> None:
    """The contract a client is most likely to match exhaustively on.

    Eleven kinds now, and each arrived as a deliberate contract change. A client generated against a
    schema missing one would silently drop whichever arm it had never heard of — which for `refused`
    or `spent` means losing the record of a governance decision or of what a run cost.
    """
    assert f'"{kind}"' in json.dumps(published()["Event"])


def test_the_event_schema_carries_no_kind_nobody_declared() -> None:
    """The other direction: a schema naming a kind the code does not emit would send a client
    looking for something that never arrives."""
    from typing import get_args

    from shadow_hdk.kernel.events import Event as EventUnion

    declared = {
        getattr(arm, "__dataclass_fields__", {})["kind"].default
        for arm in get_args(get_args(EventUnion)[0])
    }
    assert declared == set(TWELVE), declared


def test_publishing_fresh_produces_exactly_what_is_checked_in(tmp_path: Path) -> None:
    """Publish into an empty directory and compare, rather than trusting what is already on disk.

    A mutation that made the publisher **skip** a contract survived every test above, because the
    publisher never deletes: the file from the previous good run was still sitting there, correct,
    and satisfied both the set check and the content check. Comparing a fresh publish catches a
    contract that was never written as well as one written wrongly.
    """
    from shadow_hdk.wire.schemas import publish

    written = publish(tmp_path)
    fresh = {path.name: path.read_text(encoding="utf-8") for path in tmp_path.glob("*.json")}
    checked_in = {path.name: path.read_text(encoding="utf-8") for path in PUBLISHED.glob("*.json")}

    assert set(fresh) == set(checked_in), (
        "a fresh publish and the checked-in files disagree about which files exist"
    )
    assert fresh == checked_in, "a fresh publish differs from what is checked in"
    assert len(written) == len(published()) + 1, "publish did not report every file it wrote"
