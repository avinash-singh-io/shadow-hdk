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
    # **What running code on an ordinary host really costs** (BUG-018).
    #
    # `write_file` is genuinely confined: `WorkspaceComponents` refuses a path that resolves outside
    # its root, and refuses a hard link that reaches out of it. Its `writes: {workspace}` is true.
    #
    # `run_shell` and `run_python` are not, and until BUG-018 they said they were. A plain
    # subprocess honours `cwd` and nothing else: `cd ..` works, an absolute path works. So a mode
    # that permits running code at all is permitting **the machine**, and the honest way to write
    # that is `everything` — not `{workspace}` and a hope.
    #
    # This is uncomfortable to read, which is the point. Narrowing it back is exactly what a
    # contained sandbox is for (D25, D36), and why Phase 11's live proofs need a Linux host.
    ceiling=EffectProfile(
        reads=EVERYTHING,
        writes=EVERYTHING,
        reaches=True,
        reversible=False,
        contained=False,
        costs=True,
    ),
)
"""Everything the agent can do here, said out loud."""

CONFINED = Mode(
    "confined",
    # The workspace tools and nothing else. `write_file` and `read_file` fit inside this; running
    # code does not, and is **refused** — which is the demonstration:
    #
    #     ✕ refused: mode 'confined' does not permit this
    #
    # from a policy that has never heard of `run_shell`. It refused a set of effects, so it would
    # refuse a tool nobody has written yet on exactly the same grounds.
    ceiling=EffectProfile(
        reads=EVERYTHING,
        writes=WORKSPACE,
        # **True, and it has to be.** Holding the conversation open is itself a step, and talking to
        # a provider reaches out — that is what a subscription *is*. Setting this `False` refused
        # the conversation before it began, which is correct enforcement of a mode that had said
        # something it did not mean. What `confined` narrows is what the agent's **tools** may do.
        reaches=True,
        reversible=False,
        contained=False,
        costs=True,
    ),
)
"""Files, but no shell. The agent writes code and cannot run it."""

LOOKING = Mode("looking", EffectProfile(reads=EVERYTHING, contained=False, costs=True))
"""Nothing may be written or run at all."""


def workshop(root: Path, *, mode: Mode = BUILDING) -> Ports:
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


__all__ = ["BUILDING", "CONFINED", "LOOKING", "a_lease", "workshop"]
