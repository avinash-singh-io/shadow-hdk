"""The runtime — compositions compiled to graphs, every step governed, proposals to a sink.

Four public names:

    run(composition, ports, options=…)      -> AsyncIterator[Event]
    resume(composition, answer, ports, …)   -> AsyncIterator[Event]
    current_run()                           -> RunContext | None
    Ports, RunOptions                        how a runtime is configured

Everything else in this package is internal.
"""

from shadow_hdk.runtime.bindings import Ports, RunContext, RunOptions, current_run
from shadow_hdk.runtime.loop import resume, run

__all__ = ["Ports", "RunContext", "RunOptions", "current_run", "resume", "run"]
