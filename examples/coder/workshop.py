"""The environment, the policy and the lease — everything the agent is allowed to be.

Read this file first. It is the whole of what a host decides, and it is deliberately short: one
environment with a mode, one policy, one lease. Everything else in this example is wiring.

**What changed in Phase 22, and why it is the whole example.** This file used to wire three
component ports — a workspace for files, a subprocess sandbox for commands, and an honest comment
saying the second one reached the whole machine. It now wires **one environment with a mode**
(D48), and the confinement is the operating system's rather than a comment's: `workspace-write`
means a command cannot write outside the root or open a socket, proven before the environment
exists (D49). The mode you pass on the command line is the mode the agent gets, and the policy
below is written against what the environment *declares* — which is what the proof found.
"""

from __future__ import annotations

from pathlib import Path

from shadow_hdk.adapters.basic import StdoutSink, SystemClock
from shadow_hdk.adapters.modes import Mode, ModeGovernance

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Ceiling, EffectProfile, Floor, Lease, ScopeSet
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.environment import Mode as EnvironmentMode

EVERYTHING = ScopeSet(everything=True)
WORKSPACE = ScopeSet.of("workspace")

CONFINED = Mode(
    "confined",
    # Writes stay in the root; nothing reaches the network *from a tool*. This is what an
    # environment in `workspace-write` declares, because it is what the OS sandbox makes true.
    #
    # `reaches=True` is deliberate and has to be: holding the conversation open is itself a step,
    # and talking to a provider reaches out — that is what a subscription *is*. What this mode
    # narrows is what the agent's **tools** may do, and the environment's tools declare
    # `reaches=False` in `workspace-write`, which fits inside this.
    ceiling=EffectProfile(
        reads=EVERYTHING,
        writes=WORKSPACE,
        reaches=True,
        reversible=False,
        contained=True,
        costs=True,
    ),
)
"""Files and commands, confined to the root by the operating system."""

OPEN = Mode(
    "open",
    # `full` mode on an ordinary host: a command reaches the machine, and the environment says so
    # (BUG-018). This is uncomfortable to read, which is the point — a policy that permits
    # `full` is permitting the machine, and the honest way to write that is `everything`.
    ceiling=EffectProfile(
        reads=EVERYTHING,
        writes=EVERYTHING,
        reaches=True,
        reversible=False,
        contained=False,
        costs=True,
    ),
)
"""Everything, said out loud. What `--mode full` gets."""

LOOKING = Mode(
    "looking", EffectProfile(reads=EVERYTHING, reaches=True, contained=False, costs=True)
)
"""Nothing may be written or run — what `--mode read-only` gets."""

POLICY_FOR: dict[EnvironmentMode, Mode] = {
    "read-only": LOOKING,
    "workspace-write": CONFINED,
    "full": OPEN,
}
"""The policy that matches each environment mode. A policy narrower than the environment refuses
tools the environment offers; one wider admits what the environment cannot do anyway — so the
pairing is the honest one, and the mode on the command line chooses both."""


async def workshop(root: Path, *, mode: EnvironmentMode = "workspace-write") -> Ports:
    """Everything the agent can reach, and the policy that judges it.

    Raises `CannotEnforce` when this machine has no OS sandbox and a confined mode was asked for —
    the environment refuses to exist rather than quietly widen, and this example lets that reach
    the person, because it is the right thing for them to see.
    """
    environment = await LocalEnvironment.open(
        root, mode=mode, timeout_s=60.0, output_limit=32_000, at="2026-09-11T00:00:00+00:00"
    )
    policy = POLICY_FOR[mode]
    return Ports(
        model=None,  # the reasoning is the provider's; this runtime supplies no model
        components=(environment,),
        governance=ModeGovernance({policy.name: policy}, default=policy.name),
        sink=StdoutSink(),
        clock=SystemClock(),
    )


def a_lease() -> Lease:
    """What the whole conversation may spend. A ceiling on steps, wall-clock and money — the money
    being the subscription's, which is why it is small enough to notice."""
    return Lease(Ceiling(max_steps=400, max_wall_seconds=3600, max_cost_cents=500), Floor(0))


__all__ = ["CONFINED", "LOOKING", "OPEN", "POLICY_FOR", "a_lease", "workshop"]
