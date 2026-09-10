"""The tools, the policy and the lease — everything the agent is allowed to be.

Read this file first. It is the whole of what a host decides, and it is deliberately short: three
component ports, one mode, one lease. Everything else in this example is wiring.
"""

from __future__ import annotations

from pathlib import Path

from shadow_hdk.adapters.basic import StdoutSink, SystemClock
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.adapters.sandbox_subprocess import SubprocessSandbox
from shadow_hdk.adapters.workspace import WorkspaceComponents

from shadow_hdk.kernel import Ceiling, EffectProfile, Floor, Lease, ScopeSet
from shadow_hdk.runtime import Ports

EVERYTHING = ScopeSet(everything=True)
WORKSPACE = ScopeSet.of("workspace")

BUILDING = Mode(
    "building",
    # What the agent may do at all: read anything it is shown, write inside the workspace, run code
    # there. `reaches` is true because a plain subprocess on an ordinary host can open a socket
    # whatever we pass it — the sandbox says so itself, and a governance system fed a comfortable
    # lie is worse than one fed nothing.
    ceiling=EffectProfile(
        reads=EVERYTHING,
        writes=WORKSPACE,
        reaches=True,
        reversible=False,
        contained=False,
        costs=True,
    ),
)
"""The one mode this example runs in. Narrow it and watch the refusals appear in the stream — that
is the demonstration: the policy is about **effects**, and it has never heard of `write_file`."""

LOOKING = Mode("looking", EffectProfile(reads=EVERYTHING, contained=False, costs=True))
"""A second mode, for showing what a refusal looks like. Nothing may be written or run."""


def workshop(root: Path, *, mode: Mode = BUILDING, out: object = None) -> Ports:
    """Everything the agent can reach, and the policy that judges it."""
    return Ports(
        model=None,  # the reasoning is the provider's; this runtime supplies no model
        components=(
            WorkspaceComponents(root, at="2026-09-11T00:00:00+00:00"),
            SubprocessSandbox(
                root,
                contained=False,  # an honest `False`: this is a leash, not a jail
                timeout_s=60.0,
                output_limit=32_000,
                at="2026-09-11T00:00:00+00:00",
            ),
        ),
        governance=ModeGovernance({mode.name: mode}, default=mode.name),
        sink=StdoutSink(),
        clock=SystemClock(),
    )


def a_lease() -> Lease:
    """What the whole conversation may spend. A ceiling on steps, wall-clock and money — the money
    being the subscription's, which is why it is small enough to notice."""
    return Lease(Ceiling(max_steps=400, max_wall_seconds=3600, max_cost_cents=500), Floor(0))


__all__ = ["BUILDING", "LOOKING", "a_lease", "workshop"]
