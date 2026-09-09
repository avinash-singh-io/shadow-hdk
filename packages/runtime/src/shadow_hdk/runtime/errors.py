"""What the runtime raises internally, and what it never lets out.

D7: a **component** raising is data — a `Failed` observation, and the run continues. A **port**
raising is a failure — `PortFailure`, which the drive turns into `Ended(reason="failed")`. No
exception from this module escapes `run()`.
"""

from __future__ import annotations

from shadow_hdk.kernel.events import EndReason


class RuntimeStop(Exception):
    """Base for the three ways a run stops other than finishing its graph."""

    reason: EndReason


class LeaseExhausted(RuntimeStop):
    reason: EndReason = "lease_exhausted"


class Cancelled(RuntimeStop):
    reason: EndReason = "cancelled"


class PortFailure(RuntimeStop):
    """A port the host implements raised. A broken host is not something to reason past."""

    reason: EndReason = "failed"

    def __init__(self, port: str, cause: BaseException) -> None:
        super().__init__(f"{port} port failed: {type(cause).__name__}: {cause}")
        self.port = port
        self.cause = cause


class DanglingRef(Exception):
    """A binding referred to a step whose output is not there. The agent's mistake, not a crash."""
