"""What the runtime raises internally, and what it never lets out.

D7: a **component** raising is data — a `Failed` observation, and the run continues. A **port**
raising is a failure — `PortFailure`, which the drive turns into `Ended(reason="failed")`. No
exception from this module escapes `run()`.
"""

from __future__ import annotations

from shadow_hdk.kernel.events import EndReason


class RuntimeStop(BaseException):
    """Base for the three ways a run stops other than finishing its graph.

    **A `BaseException`, deliberately** (TD-006). These are stop signals, not errors a component may
    handle — and every component adapter catches `Exception` around the callable it runs, because
    D7 says a component raising is data. So a lease that ran out, a host that cancelled, or a port
    that broke *inside* a component was caught by that component and returned as its own `Failed`.
    The run then carried on past the very things that exist to stop it.

    This is why `asyncio.CancelledError` moved out of `Exception` in Python 3.8, and it is the same
    argument: a signal that must not be swallowed must not be catchable by code that is right to
    swallow errors. It fixes the inversion in adapters nobody has written yet, which a fix inside
    `step.py` could not.

    `loop.py` catches `BaseException` and asks `_stop_reason`, so every one of these still ends the
    run with a reason on the record rather than a traceback at the caller.
    """

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
