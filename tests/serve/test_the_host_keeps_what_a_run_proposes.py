"""What a run proposes for keeping is kept (Phase 28 group 4, ENH-011): the shipped composition's
sink writes a minted skill into the store's `skills` collection, so it is offered after a restart
and listed with source `store`. The runtime still has no write path — the *host's* sink writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Proposal
from shadow_hdk.kernel.components import Provenance
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.serve import ServeHost
from shadow_hdk.serve.config import Settings
from shadow_hdk.serve.keeping import KeepingSink
from tests.adapters.contract import SinkPortContract

pytestmark = pytest.mark.anyio


class Heard:
    def __init__(self) -> None:
        self.proposals: list[Proposal] = []

    async def propose(self, proposal: Proposal) -> None:
        self.proposals.append(proposal)


def _minted(name: str = "csv-summary") -> Proposal:
    return Proposal(
        kind="skill",
        payload={
            "name": name,
            "description": "Summarise a CSV in three lines.",
            "prompt": "Read the header; total per group; three bullets.",
            "needs": ["read_file"],
        },
        provenance=Provenance(registered_by="agent", adapter="agent", at="t"),
    )


async def test_a_minted_skill_becomes_a_store_row_and_the_rest_passes_through() -> None:
    store = InMemoryStore()
    inner = Heard()
    sink = KeepingSink(store, inner)
    await sink.propose(_minted())
    rows = list(await store.list("skills"))
    assert [key for key, _ in rows] == ["csv-summary"]
    row = cast(dict[str, Any], rows[0][1])
    assert str(row["prompt"]).startswith("Read the header")
    other = Proposal(kind="note", payload={"x": 1}, provenance=_minted().provenance)
    await sink.propose(other)
    assert [p.kind for p in inner.proposals] == ["skill", "note"], "everything still reaches it"


async def test_a_malformed_skill_proposal_is_passed_on_not_kept() -> None:
    store = InMemoryStore()
    inner = Heard()
    sink = KeepingSink(store, inner)
    bad = Proposal(kind="skill", payload={"name": "x"}, provenance=_minted().provenance)
    await sink.propose(bad)
    assert list(await store.list("skills")) == []
    assert [p.kind for p in inner.proposals] == ["skill"]


async def test_the_serve_host_offers_a_kept_skill_after_a_restart(tmp_path: Path) -> None:
    settings = Settings(root=tmp_path, mode="full", store=tmp_path / "live.sqlite")
    first = ServeHost(settings)
    await first.sink.propose(_minted("kept-one"))
    second = ServeHost(settings)  # a new process, same file
    names = {s.name: s.source for s in await second.skills.all()}
    assert names.get("kept-one") == "store"


class TestKeepingSinkIsASinkPort(SinkPortContract):
    def port(self) -> KeepingSink:
        return KeepingSink(InMemoryStore(), Heard())
