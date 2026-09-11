"""The host's own record of what the run proposed — and, for skills, the host's decision to keep.

The runtime never commits anything anywhere; it *proposes* through the sink (D6), and the host
decides what a proposal becomes. This one keeps them, can say so as JSON, and **is a skill source**:
a `kind="skill"` proposal it kept comes back to the next run as a skill with `source="kept"` (D56).
Promotion is the host's decision — here, the simplest one: everything minted is kept. A real host
would review, or ask, or keep only what a person approved; the runtime never learns which.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from shadow_hdk.adapters.agent import Skill, kept_from

from shadow_hdk.kernel import Proposal
from shadow_hdk.kernel.contracts import adapter_for


class Ledger:
    def __init__(self) -> None:
        self.proposals: list[Proposal] = []

    async def propose(self, proposal: Proposal) -> None:
        self.proposals.append(proposal)

    async def skills(self) -> Sequence[Skill]:
        """What this ledger kept, as skills — the host's half of self-evolution."""
        return tuple(kept_from(p, source="kept") for p in self.proposals if p.kind == "skill")

    def as_json(self) -> str:
        dump = adapter_for(Proposal)
        rows: list[Any] = [dump.dump_python(p, mode="json") for p in self.proposals]
        return json.dumps(rows, indent=2, sort_keys=True)


__all__ = ["Ledger"]
