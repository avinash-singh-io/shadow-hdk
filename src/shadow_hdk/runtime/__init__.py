"""The runtime — compositions compiled to graphs, every step governed, proposals to a sink.

Four public names:

    run(composition, ports, options=…)      -> AsyncIterator[Event]
    resume(composition, answer, ports, …)   -> AsyncIterator[Event]
    current_run()                           -> RunContext | None
    Ports, RunOptions                        how a runtime is configured
    Trust                                    which driver keys a deployment holds

Everything else in this package is internal.
"""

from shadow_hdk.runtime.approvals import (
    ApprovalAnswer,
    Approvals,
    Approve,
    ApproveAndAddRule,
    Deny,
    Parked,
    Request,
)
from shadow_hdk.runtime.bindings import Ports, Resumed, RunContext, RunOptions, current_run
from shadow_hdk.runtime.cancel import Cancellation
from shadow_hdk.runtime.conversation import Conversation, Turned
from shadow_hdk.runtime.loop import resume, run
from shadow_hdk.runtime.trust import Trust

__all__ = [
    "Cancellation",
    "Pending",
    "Ports",
    "ApprovalAnswer",
    "Approvals",
    "Approve",
    "ApproveAndAddRule",
    "Conversation",
    "Deny",
    "Parked",
    "Request",
    "Turned",
    "Resumed",
    "RunContext",
    "RunOptions",
    "Trust",
    "current_run",
    "resume",
    "run",
]
