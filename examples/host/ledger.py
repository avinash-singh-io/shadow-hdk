"""The host's own record of what the run proposed.

The runtime never commits anything anywhere; it *proposes* through the sink (D6), and the host
decides what a proposal becomes. This one keeps them, and can say so as JSON.
"""

from __future__ import annotations

import json
from typing import Any

from shadow_hdk.kernel import Proposal
from shadow_hdk.kernel.contracts import adapter_for


class Ledger:
    def __init__(self) -> None:
        self.proposals: list[Proposal] = []

    async def propose(self, proposal: Proposal) -> None:
        self.proposals.append(proposal)

    def as_json(self) -> str:
        dump = adapter_for(Proposal)
        rows: list[Any] = [dump.dump_python(p, mode="json") for p in self.proposals]
        return json.dumps(rows, indent=2, sort_keys=True)


__all__ = ["Ledger"]
