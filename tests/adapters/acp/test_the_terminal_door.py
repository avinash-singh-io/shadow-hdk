"""The child can run code, and every command it runs is on our leash (D42).

This door refused outright for five phases — *"this bridge grants no terminals yet"* — which left an
agent asked to run something either unable to, or running it in its own process where nothing here
sees it. Both answers break the socket: **every effect routes through the run, whoever asked**.

The grant is judged once, at creation, on the effects of *opening a terminal at all* — reading and
writing the workspace, reaching the network unless containment says otherwise, irreversible. The
follow-ups are not re-judged, because asking again for every read of a terminal already allowed is
noise rather than safety.

What the terminal is, is a `HeldProcess` from the runtime: its own process group, a cap on output,
a timeout that runs whether or not anybody is waiting, and a kill that takes the group. The bridge
does not implement any of that — it borrows it, which is why granting a terminal here does not make
this adapter import the sandbox adapter.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from acp.exceptions import RequestError

from shadow_hdk.adapters.acp import BridgeClient
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.kernel import EffectProfile, ScopeSet
from tests.adapters.acp.conftest import EVERYTHING, inside_a_run

WORKSPACE = ScopeSet.of("workspace")

RUNNING = Mode(
    "running",
    # **Everything, and deliberately so** (BUG-018). This said `writes=WORKSPACE` and passed,
    # because the profile for `execute` claimed the workspace while a plain subprocess can `cd ..`.
    # Now that the profile is honest, permitting a terminal at all means permitting what a terminal
    # on an ordinary host can really do — and a host has to write that down rather than be told a
    # comfortable thing. Narrowing it back is what `contained=True` is for.
    EffectProfile(
        reads=EVERYTHING,
        writes=EVERYTHING,
        reaches=True,
        reversible=False,
        contained=False,
        costs=True,
    ),
)
LOOKING = Mode("looking", EffectProfile(reads=EVERYTHING, contained=False, costs=True))


def mode(one: Mode) -> ModeGovernance:
    return ModeGovernance({one.name: one}, default=one.name)


async def a_terminal(client: BridgeClient, command: str, *args: str) -> str:
    made = await inside_a_run(
        lambda: client.create_terminal("s", command, list(args)), governance=mode(RUNNING)
    )
    return str(made.terminal_id)


# ---------------------------------------------------------------- the grant


async def test_a_terminal_is_granted_when_the_mode_permits_running(tmp_path: Path) -> None:
    """The bug, at the size a reader met it: this raised *no terminals yet* whatever was asked."""
    client = BridgeClient(workspace=tmp_path)

    terminal = await a_terminal(client, "/bin/echo", "hello")

    assert terminal


async def test_a_terminal_is_refused_when_the_mode_does_not(tmp_path: Path) -> None:
    """Judged on effects, not on the word *terminal*: a looking mode permits no writes, and opening
    a terminal writes."""
    client = BridgeClient(workspace=tmp_path)

    with pytest.raises(RequestError) as refused:
        await inside_a_run(
            lambda: client.create_terminal("s", "/bin/echo", ["hi"]), governance=mode(LOOKING)
        )

    assert "looking" in str(refused.value)


async def test_a_refused_terminal_starts_no_process(tmp_path: Path) -> None:
    """A refusal that had already run the command would be a report, not a refusal."""
    client = BridgeClient(workspace=tmp_path)
    target = tmp_path / "written-by-a-refused-command"

    with pytest.raises(RequestError):
        await inside_a_run(
            lambda: client.create_terminal("s", "/bin/sh", ["-c", f"touch {target}"]),
            governance=mode(LOOKING),
        )

    assert not target.exists(), "the command ran and then the answer was no"


# ---------------------------------------------------------------- the follow-ups


async def test_what_the_command_printed_comes_back(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path)
    terminal = await a_terminal(client, "/bin/echo", "the lathe weighs 12kg")

    await client.wait_for_terminal_exit("s", terminal)
    said = await client.terminal_output("s", terminal)

    assert "the lathe weighs 12kg" in said.output
    assert said.truncated is False


async def test_waiting_gives_the_exit_code(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path)
    terminal = await a_terminal(client, "/bin/sh", "-c", "exit 7")

    ended = await client.wait_for_terminal_exit("s", terminal)

    assert ended.exit_code == 7


async def test_a_terminal_can_be_killed(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path)
    terminal = await a_terminal(client, "/bin/sh", "-c", "sleep 60")

    await client.kill_terminal("s", terminal)
    ended = await client.wait_for_terminal_exit("s", terminal)

    assert ended.exit_code != 0 or ended.signal is not None


async def test_releasing_a_terminal_ends_what_was_still_running(tmp_path: Path) -> None:
    """D35: a step owns the process tree it starts. A released terminal whose program outlived the
    run is exactly the orphan that rule forbids."""
    client = BridgeClient(workspace=tmp_path)
    terminal = await a_terminal(client, "/bin/sh", "-c", "sleep 60")

    await client.release_terminal("s", terminal)

    with pytest.raises(RequestError):
        await client.terminal_output("s", terminal)


async def test_a_terminal_nobody_created_is_refused(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path)

    with pytest.raises(RequestError, match="no terminal"):
        await client.terminal_output("s", "made-up")


async def test_a_command_runs_in_the_workspace_and_not_wherever_we_are(tmp_path: Path) -> None:
    """The confinement the workspace already promises, extended to what the child runs."""
    client = BridgeClient(workspace=tmp_path)
    terminal = await a_terminal(client, "/bin/sh", "-c", "pwd")

    await client.wait_for_terminal_exit("s", terminal)
    said = await client.terminal_output("s", terminal)

    assert str(tmp_path.resolve()) in said.output


async def test_a_bridge_with_no_workspace_grants_no_terminal() -> None:
    """Nowhere to run it is not somewhere to run it. A terminal defaulting to this process's own
    directory would put a model-written command in the operator's checkout."""
    client = BridgeClient()

    with pytest.raises(RequestError, match="workspace"):
        await inside_a_run(
            lambda: client.create_terminal("s", "/bin/echo", ["hi"]), governance=mode(RUNNING)
        )
