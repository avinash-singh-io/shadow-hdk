"""What a driver reads at the moment of the act, and what it leaves behind (R9).

*Authority checked at the moment of the act and every effect attributed.* The runtime's half of
that is small and generic: `exhausted` says whether the lease can still cover an act **now** — read
when the driver is about to act, not when the step was planned — and `grounds` is what the act was
performed under, for the `Acted` receipt an auditor will read later: the run, the step, the time,
the lease left, the argv, and the warrant it carried.

Steps are deliberately not `exhausted`'s question. The step an act runs inside was admitted and
charged by the runtime already; what can change between that admission and the act is time and
money, so those are what a driver re-checks.

The warrant is carried, not judged. What a warrant is, who issues one, and which acts need one are
ADR-1's questions; the mechanism records whatever the driver was handed so nothing is invented here.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.kernel.leases import Lease
from shadow_hdk.runtime.bindings import RunContext


def exhausted(lease: Lease) -> str | None:
    """Why this lease cannot cover an act now, or `None` if it can."""
    if lease.ceiling.max_wall_seconds <= 0:
        return "the lease has no time left"
    if lease.ceiling.max_cost_cents == 0:
        return "the lease has nothing left to spend"
    return None


def grounds(
    context: RunContext, *, argv: JsonValue = None, warrant: JsonValue = None
) -> dict[str, JsonValue]:
    """What an act is performed under, read at the moment it is performed."""
    left = context.remaining().ceiling
    return {
        "run": context.run_id,
        "step": context.step,
        "at": context.now(),
        "lease": {
            "max_steps": left.max_steps,
            "max_wall_seconds": left.max_wall_seconds,
            "max_cost_cents": left.max_cost_cents,
        },
        "argv": argv,
        "warrant": warrant,
    }


__all__ = ["exhausted", "grounds"]
