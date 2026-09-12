"""What a mode forbids, a child is not even offered — and is refused if it asks anyway.

The coder example's second demonstration, and it needs **no model at all**: the claim is about the
registry a child is handed, which is decided before anybody reasons about anything.

Two layers, and both matter:

**It is not offered.** `RecordingServer` builds its tool list from `RunContext.visible()`, which is
governed. Under a policy narrower than the environment, the operations that exceed it are absent
from the list the child receives — so a well-behaved agent never tries.

**It is refused if called anyway.** A list is a courtesy; the judgement is the control. A child that
guessed a tool name gets a refusal naming the **mode**, because the policy judged a set of effects
and has never heard of `run_shell`.

**Rewritten in Phase 22 from a corrected premise.** The old version showed a `confined` mode that
did not offer the shell, because running code was an unconfined subprocess and the only honest way
to confine was to forbid it. Now `workspace-write` **does** offer the shell, confined by the
operating system — the stronger claim, proven in `tests/adapters/environment`. What this file
holds is the mechanism: a policy narrower than the environment filters what the child sees, on
effects, in every mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from examples.coder.workshop import LOOKING, OPEN, a_lease
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.adapters.recording import RecordingServer

from shadow_hdk.adapters.environment import LocalEnvironment, local_sandbox
from shadow_hdk.kernel import (
    Allow,
    Completed,
    Composition,
    EffectProfile,
    Invoke,
    Observation,
)
from shadow_hdk.runtime import Approvals, Ports, RunOptions, current_run, run
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)

WATCHING = make_registration(
    "watching",
    effects=EffectProfile(),
    description="Look at the registry a child would be handed, and nothing else.",
)
"""A driver that does nothing, on purpose.

The example's real driver holds a conversation, so it declares writes and reaching out — and a mode
that forbids those refuses **it** before the registry is consulted. That is correct enforcement,
and it made the first version of this file test the driver's profile rather than the registry's
contents. A driver with no effects is permitted by every mode here, which leaves each test's
subject the thing it is named after.
"""


async def offered_and_asked(
    root: Path,
    policy: Mode,
    environment_mode: EnvironmentMode = "full",
    *,
    approvals: Approvals | None = None,
) -> dict[str, Any]:
    """What a child would be handed under `policy` over an environment in `environment_mode`, and
    what happens if it calls the shell anyway. `approvals` is who answers when the policy asks
    (D58); nobody, by default."""
    found: dict[str, Any] = {}

    async def drive(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        server = RecordingServer(context, withhold={"watching"})
        found["offered"] = sorted(tool.name for tool in await server.tools())
        found["wrote"] = await server.call_tool("write_file", {"path": "a.txt", "content": "hi"})
        found["ran"] = await server.call_tool("run_shell", {"command": "ls"})
        return Completed(None)

    environment = await LocalEnvironment.open(root, mode=environment_mode)
    ports = Ports(
        model=None,
        components=(environment, InMemoryComponents([(WATCHING, drive)])),
        governance=ModeGovernance({policy.name: policy}, default=policy.name),
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition((Invoke("watching", "watching"),))
    async for _ in run(plan, ports, options=RunOptions(lease=a_lease(), approvals=approvals)):
        pass
    return found


class SaysYes(Approvals):
    """A person who allows everything the moment it is asked — the test's stand-in for `y`."""

    async def ask(self, pending: Any) -> Any:
        return Allow()


async def test_a_policy_narrower_than_the_environment_does_not_offer_what_exceeds_it(
    tmp_path: Path,
) -> None:
    """`full` declares everything; a policy that permits no writes excludes every operation that
    writes — files and commands alike — from the list the child is handed."""
    seen = await offered_and_asked(tmp_path, LOOKING, "full")

    assert "read_file" in seen["offered"]
    assert "write_file" not in seen["offered"], seen["offered"]
    assert "run_shell" not in seen["offered"], seen["offered"]


async def test_it_is_refused_even_if_the_child_asks_anyway(tmp_path: Path) -> None:
    """The list is a courtesy; the judgement is the control."""
    seen = await offered_and_asked(tmp_path, LOOKING, "full")

    assert seen["wrote"].is_error is True
    assert seen["ran"].is_error is True
    assert "looking" in str(seen["ran"].content), seen["ran"].content


async def test_the_refusal_names_the_mode_and_not_the_tool(tmp_path: Path) -> None:
    """The policy judged a set of effects. It has never heard of `run_shell`, which is why it would
    refuse a tool nobody has written yet on exactly the same grounds."""
    seen = await offered_and_asked(tmp_path, LOOKING, "full")

    said = str(seen["ran"].content)
    assert "run_shell" not in said, f"the refusal is about the effects, not the name: {said}"


async def test_the_open_policy_does_offer_it_and_asks_before_a_write(tmp_path: Path) -> None:
    """The anti-vacuity half: a registry that offered nothing under every policy would pass the
    tests above and mean nothing. `open` asks before a write (its ask line); with a person who
    says yes, the write goes through. (Written first with no ask line; the premise moved.)"""
    seen = await offered_and_asked(tmp_path, OPEN, "full", approvals=SaysYes())

    assert "run_shell" in seen["offered"]
    assert seen["ran"].is_error is False
    assert seen["wrote"].is_error is False


async def test_with_nobody_to_ask_the_open_policys_write_is_refused_and_says_so(
    tmp_path: Path,
) -> None:
    seen = await offered_and_asked(tmp_path, OPEN, "full")

    assert seen["wrote"].is_error is True
    assert "nobody" in seen["wrote"].content[0].text
    # An unconfined shell writes anywhere too — `full` declares it so — and is asked the same way.
    assert seen["ran"].is_error is True
    assert "nobody" in seen["ran"].content[0].text


@pytest.mark.skipif(
    local_sandbox() is None, reason="read-only needs an OS sandbox to be enforceable"
)
async def test_read_only_does_not_offer_a_write_and_the_environment_itself_refuses_one(
    tmp_path: Path,
) -> None:
    """The third rung, one layer down: in `read-only` the *environment* does not register a write at
    all, before any policy is consulted — and a command may run, because it cannot write."""
    seen = await offered_and_asked(tmp_path, LOOKING, "read-only")

    assert "read_file" in seen["offered"]
    assert "write_file" not in seen["offered"], seen["offered"]
    assert seen["wrote"].is_error is True
