"""The kit keeps a run's proposals only when nobody else is listening (D156, lane P's ask 6).

`KeepingSink`'s own docstring says it: *the runtime has no write path — a minted skill leaves a run
as a `Proposal` on the sink port, and whoever holds the sink decides.* The shipped composition then
decided, for everyone, to keep it as a `skills` row in the kit's own store.

Lane P's position, and they are right: a run's creations — a skill an agent mints, a memory, an
instruction it writes — should arrive as a proposal and be stored by the product once agreed, not
kept inside the kit. A kit that keeps regardless is taking the product's decision.

But never keeping would re-break what ENH-011 fixed: for a standalone `serve` with no host sink,
keeping is the only way a minted skill survives a restart, and losing them was found by the demo.

So the rule states itself — **the kit keeps only when nobody else is listening** — and
`keep_proposals` forces it either way for a host that wants neither default.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.kernel import Proposal, Provenance
from shadow_hdk.kernel.ports import SinkPort
from shadow_hdk.serve import ServeHost, Settings

pytestmark = pytest.mark.anyio

A_SKILL = {
    "name": "tidy",
    "description": "tidy a file",
    "prompt": "read it, then write it back sorted",
    "needs": [],
}


class Listening(SinkPort):
    """A product's own sink: it hears everything and the kit stores nothing on its behalf."""

    def __init__(self) -> None:
        self.heard: list[Proposal] = []

    async def propose(self, proposal: Proposal) -> None:
        self.heard.append(proposal)


def a_host(where: Path, **kw: object) -> ServeHost:
    url = f"sqlite:///{where / 'h.db'}"
    return ServeHost(Settings(root=where, store=url), **kw)  # type: ignore[arg-type]


async def _propose(host: ServeHost, kind: str = "skill", payload: object = None) -> None:
    await host.sink.propose(
        Proposal(
            kind=kind,
            payload=payload if payload is not None else A_SKILL,  # type: ignore[arg-type]
            provenance=Provenance(registered_by="a test", adapter="test", at="2026-10-01"),
        )
    )


async def _kept(host: ServeHost) -> list[object]:
    row = await host.store.get("skills", A_SKILL["name"])
    return [] if row is None else [row]


# ------------------------------------------------------ a host that is listening keeps its own


async def test_a_host_with_its_own_sink_hears_the_proposal(tmp_path: Path) -> None:
    mine = Listening()
    host = a_host(tmp_path, sink=mine)

    await _propose(host)

    assert len(mine.heard) == 1, "the product heard it"
    assert mine.heard[0].kind == "skill"


async def test_and_the_kits_own_store_stays_empty(tmp_path: Path) -> None:
    """Lane P's ask in one assertion: *not kept in the kit's own store*."""
    mine = Listening()
    host = a_host(tmp_path, sink=mine)

    await _propose(host)

    assert await _kept(host) == [], "the kit stored nothing on the product's behalf"


async def test_a_proposal_of_any_kind_reaches_the_host(tmp_path: Path) -> None:
    """A memory and an instruction an agent writes are proposals too — nothing narrows to skills."""
    mine = Listening()
    host = a_host(tmp_path, sink=mine)

    await _propose(host, kind="memory", payload={"text": "the build is flaky on tuesdays"})
    await _propose(host, kind="instruction", payload={"text": "always run the linter"})

    assert [p.kind for p in mine.heard] == ["memory", "instruction"]


# ------------------------------------------------------ and a host that is not keeps nothing lost


async def test_a_host_with_no_sink_still_keeps_a_minted_skill(tmp_path: Path) -> None:
    """ENH-011 kept. With nobody listening, keeping is the only way it survives a restart, and
    losing them was found by the demo."""
    host = a_host(tmp_path)

    await _propose(host)

    kept = await _kept(host)
    assert len(kept) == 1, kept
    assert isinstance(kept[0], dict) and kept[0]["name"] == "tidy"


# ------------------------------------------------------ and a host that wants neither default


async def test_keep_proposals_false_stops_the_kit_keeping_even_with_no_sink(
    tmp_path: Path,
) -> None:
    host = a_host(tmp_path, keep_proposals=False)

    await _propose(host)

    assert await _kept(host) == []


async def test_keep_proposals_true_keeps_even_when_a_host_is_listening(tmp_path: Path) -> None:
    """A host that wants both — its own record and the kit's — says so."""
    mine = Listening()
    host = a_host(tmp_path, sink=mine, keep_proposals=True)

    await _propose(host)

    assert len(mine.heard) == 1, "still heard"
    assert len(await _kept(host)) == 1, "and kept"
