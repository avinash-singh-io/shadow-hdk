"""What a run proposes for keeping, kept (ENH-011, D76): the shipped composition's sink.

The runtime has no write path (rule 2): a minted skill leaves a run as a `Proposal` on the sink
port, and whoever holds the sink decides. This host decides to keep it — a `skills` row in its
store (D66), which the skill registry reads at its next refresh — and passes every proposal on to
the sink behind it, so nothing a product listens for is lost. Before this, `serve`'s sink was
stdout and a minted skill was gone at restart (found by the demo).
"""

from __future__ import annotations

from typing import Any

from shadow_hdk.kernel import Proposal
from shadow_hdk.kernel.ports import SinkPort


class KeepingSink(SinkPort):
    """Keep a `skill` proposal as a store row; hand every proposal on."""

    def __init__(self, store: Any, inner: SinkPort | None = None, collection: str = "skills"):
        self._store = store
        self._inner = inner
        self._collection = collection

    async def propose(self, proposal: Proposal) -> None:
        if proposal.kind == "skill":
            await self._keep(proposal.payload)
        if self._inner is not None:
            await self._inner.propose(proposal)

    async def _keep(self, payload: Any) -> None:
        """The row `StoreSkills` reads: name, description, prompt, needs. A payload that is not
        that shape is not kept — the registry would skip it anyway — and is not raised over,
        because a sink that raises ends the run that proposed."""
        if not isinstance(payload, dict):
            return
        name = str(payload.get("name", "") or "")
        if not name or not payload.get("prompt") or not payload.get("description"):
            return
        row = {
            "name": name,
            "description": str(payload["description"]),
            "prompt": str(payload["prompt"]),
            "needs": sorted(str(n) for n in payload.get("needs", []) or []),
        }
        await self._store.put(self._collection, name, row)


__all__ = ["KeepingSink"]
