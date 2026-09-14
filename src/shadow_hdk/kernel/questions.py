"""A question a run is waiting on, and who answers it (D58, D61, D91).

Two kinds, the industry's words: an **approval request** — the policy asked before an act, and
the person answers approve · deny · approve-and-add-rule, or **park** (D88); an **input
request** — the agent's own question, answered with text. The runtime asks through the
`Questions` port (`kernel/ports.py`); the host's handle (`runtime.Approvals`) implements it, and
a product with its own way of asking implements it too, without inheriting ours.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Request:
    """One request a component is waiting on: for approval of an act, or for the person's input."""

    handle: str
    run_id: str
    step: str
    question: str
    component: str | None = None
    """What it is about — the component and inputs the step would run with (BUG-026)."""
    inputs: Any = None
    kind: str = "approval"
    """`approval` or `input`."""


__all__ = ["Request"]
