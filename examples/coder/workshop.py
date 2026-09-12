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
from typing import Any

from shadow_hdk.adapters.agent import SkillComponents, SkillRegistry, shipped_skills
from shadow_hdk.adapters.basic import StdoutSink, SystemClock
from shadow_hdk.adapters.modes import (
    Mode,
    ModeRegistry,
    governance_for,
    shipped_modes,
)

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Ceiling, Floor, Lease
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.runtime.person import person_components

# The three policies the harness ships, one per environment mode (D64) — the definitions live in
# the modes adapter now, not here. Kept as names for the example and its tests; a product builds
# its own registry the same way.
MODES = ModeRegistry(shipped_modes())
_POLICY = {spec.id: spec.policy for spec in MODES.listing()}
LOOKING: Mode = _POLICY["read-only"]
CONFINED: Mode = _POLICY["workspace-write"]
OPEN: Mode = _POLICY["full"]
POLICY_FOR: dict[EnvironmentMode, Mode] = {
    "read-only": LOOKING,
    "workspace-write": CONFINED,
    "full": OPEN,
}


async def workshop(
    root: Path, *, mode: EnvironmentMode = "workspace-write", rules: Any = None
) -> Ports:
    """Everything the agent can reach, and the policy that judges it.

    Raises `CannotEnforce` when this machine has no OS sandbox and a confined mode was asked for —
    the environment refuses to exist rather than quietly widen, and this example lets that reach
    the person, because it is the right thing for them to see.
    """
    environment = await LocalEnvironment.open(
        root, mode=mode, timeout_s=60.0, output_limit=32_000, at="2026-09-11T00:00:00+00:00"
    )
    # The shipped skills, offered as a component (D55): the provider chooses one through the same
    # socket its file tools go through, and the choice is a step on the record. Choosing is pure,
    # so every mode offers it; minting writes the record, so `read-only` hides it — by effect.
    skills = SkillComponents(
        SkillRegistry((shipped_skills(),)), minting=True, at="2026-09-11T00:00:00+00:00"
    )
    return Ports(
        model=None,  # the reasoning is the provider's; this runtime supplies no model
        # The agent's own question to the person is a component like any other (D65): no
        # effects, so every mode offers it.
        components=(environment, skills, person_components()),
        # Every shipped mode is judged from; the environment's mode is the one selected by default,
        # and `Thread.set_mode` flips between them live (D64). The host's act rules — "approve and
        # don't ask again" — are read after a mode says *ask* (D65).
        governance=governance_for(MODES, default=mode, rules=rules),
        sink=StdoutSink(),
        clock=SystemClock(),
    )


def a_lease() -> Lease:
    """What the whole conversation may spend. A ceiling on steps, wall-clock and money — the money
    being the subscription's, which is why it is small enough to notice."""
    return Lease(Ceiling(max_steps=400, max_wall_seconds=3600, max_cost_cents=500), Floor(0))


__all__ = ["CONFINED", "LOOKING", "MODES", "OPEN", "POLICY_FOR", "a_lease", "workshop"]
