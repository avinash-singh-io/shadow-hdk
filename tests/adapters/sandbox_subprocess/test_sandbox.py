"""A subprocess sandbox that says what it is.

Two things are being tested. That it *runs* code with a leash — a timeout that fires, an output cap
that bites, a non-zero exit that is data rather than a failure. And, more importantly, that it
**declares itself honestly**: an uncontained host cannot stop a subprocess opening a socket, so a
profile claiming otherwise would be the exact lie this design exists to prevent.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from shadow_hdk.adapters.sandbox_subprocess import SubprocessSandbox
from pydantic import JsonValue

from shadow_hdk.kernel import Completed, EffectProfile, Failed, ScopeSet
from shadow_hdk.kernel.ports import ComponentPort
from tests.adapters.contract import ComponentPortContract


def sandbox(
    root: Path,
    *,
    contained: bool = False,
    timeout_s: float = 30.0,
    output_limit: int = 64_000,
    network: bool = False,
) -> SubprocessSandbox:
    return SubprocessSandbox(
        root,
        contained=contained,
        timeout_s=timeout_s,
        output_limit=output_limit,
        network=network,
        at="2026-09-10T00:00:00+00:00",
    )


async def profiles(root: Path, **kw: Any) -> dict[str, EffectProfile]:
    return {r.id: r.component.effects for r in await sandbox(root, **kw).registrations()}


def _output(observation: object) -> dict[str, JsonValue]:
    assert isinstance(observation, Completed), f"expected Completed, got {observation!r}"
    assert isinstance(observation.output, dict)
    return observation.output


class TestSubprocessSandboxIsAComponentPort(ComponentPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        with TemporaryDirectory() as tmp:
            yield sandbox(Path(tmp))

    def valid_call(self) -> tuple[str, JsonValue]:
        return "run_python", {"source": "print('hello')"}


# ---------------------------------------------------------------- it runs things


async def test_python_runs_and_its_output_comes_back(tmp_path: Path) -> None:
    result = _output(await sandbox(tmp_path).invoke("run_python", {"source": "print(6 * 7)"}))
    assert result["exit_code"] == 0
    assert "42" in str(result["stdout"])


async def test_a_shell_command_runs(tmp_path: Path) -> None:
    result = _output(await sandbox(tmp_path).invoke("run_shell", {"command": "echo lathe"}))
    assert result["exit_code"] == 0
    assert "lathe" in str(result["stdout"])


async def test_it_runs_inside_the_workspace(tmp_path: Path) -> None:
    (tmp_path / "here.txt").write_text("x")
    result = _output(await sandbox(tmp_path).invoke("run_shell", {"command": "ls"}))
    assert "here.txt" in str(result["stdout"])


async def test_a_script_that_fails_still_ran(tmp_path: Path) -> None:
    """A non-zero exit is `Completed`, not `Failed`. The script ran perfectly well and told us it
    failed — which is a result the agent can read, not an error the runtime should dress up."""
    result = _output(
        await sandbox(tmp_path).invoke("run_python", {"source": "import sys; sys.exit(3)"})
    )
    assert result["exit_code"] == 3


async def test_what_a_script_writes_to_stderr_comes_back_too(tmp_path: Path) -> None:
    result = _output(
        await sandbox(tmp_path).invoke(
            "run_python", {"source": "import sys; print('bad', file=sys.stderr)"}
        )
    )
    assert "bad" in str(result["stderr"])


# ---------------------------------------------------------------- the leash


async def test_a_runaway_script_is_stopped_by_the_clock(tmp_path: Path) -> None:
    """Measured, not asserted: a test that only checked for `Failed` would pass even if the
    timeout never fired and something else went wrong."""
    started = time.perf_counter()
    observation = await sandbox(tmp_path, timeout_s=1.0).invoke(
        "run_python", {"source": "import time; time.sleep(60)"}
    )
    elapsed = time.perf_counter() - started
    assert isinstance(observation, Failed)
    assert "timed out" in observation.error
    assert elapsed < 10.0, f"the timeout did not stop it: {elapsed:.1f}s"


async def test_output_beyond_the_cap_is_truncated_and_says_so(tmp_path: Path) -> None:
    """Silently truncating would let an agent reason from half an answer believing it was whole."""
    result = _output(
        await sandbox(tmp_path, output_limit=200).invoke(
            "run_python", {"source": "print('x' * 5000)"}
        )
    )
    assert result["truncated"] is True
    assert len(str(result["stdout"])) <= 200


async def test_output_within_the_cap_is_not_marked_truncated(tmp_path: Path) -> None:
    result = _output(await sandbox(tmp_path).invoke("run_python", {"source": "print('small')"}))
    assert result["truncated"] is False


# ---------------------------------------------------------------- what it declares


async def test_running_code_is_never_reversible(tmp_path: Path) -> None:
    assert (await profiles(tmp_path))["run_python"].reversible is False


async def test_contained_is_carried_verbatim_from_the_deployment(tmp_path: Path) -> None:
    assert (await profiles(tmp_path, contained=False))["run_python"].contained is False
    assert (await profiles(tmp_path, contained=True))["run_python"].contained is True


async def test_an_uncontained_host_admits_it_cannot_stop_the_network(tmp_path: Path) -> None:
    """The honesty that matters most here.

    A plain subprocess on a normal host can open a socket whatever we pass it, so `reaches=False`
    with `contained=False` would be a claim we cannot keep — and a governance system fed a lie is
    worse than one fed nothing. `reaches` is therefore `network or not contained`: only a deployment
    that asserts real isolation gets to say a run does not reach outside.
    """
    uncontained = await profiles(tmp_path, contained=False, network=False)
    assert uncontained["run_python"].reaches is True

    contained = await profiles(tmp_path, contained=True, network=False)
    assert contained["run_python"].reaches is False

    contained_but_online = await profiles(tmp_path, contained=True, network=True)
    assert contained_but_online["run_shell"].reaches is True


async def test_it_says_it_touches_everything_unless_it_is_contained(tmp_path: Path) -> None:
    """This test used to assert `{workspace}` for both, and was wrong (BUG-018).

    It encoded the adapter's claim rather than the adapter's behaviour, and the claim was false: a
    plain subprocess honours `cwd` and nothing else, so `cd ..` and absolute paths reach the whole
    machine. Rewritten from the corrected premise — **containment is what makes the narrow claim
    true**, and without it the honest answer is *everything*.

    `test_it_declares_what_it_can_really_do.py` next door proves the behaviour by doing it.
    """
    loose = (await profiles(tmp_path))["run_shell"]
    assert loose.writes == ScopeSet(everything=True)
    assert loose.reads == ScopeSet(everything=True)

    proven = (await profiles(tmp_path, contained=True))["run_shell"]
    assert proven.writes == ScopeSet.of("workspace")
    assert proven.reads == ScopeSet.of("workspace")


async def test_a_script_the_model_wrote_does_not_inherit_the_operators_secrets(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """The environment is where credentials live, and a child inherits it by default.

    A script an agent wrote is untrusted code; handing it `ANTHROPIC_API_KEY` because it happened
    to be in the parent process is how a tool that reads a file also exfiltrates a token. Only a
    named few variables pass. Added after a mutation replaced the filter with `dict(os.environ)`
    and nothing failed.
    """
    monkeypatch.setenv("SPIKE_FAKE_TOKEN", "sk-not-a-real-secret")
    monkeypatch.setenv("PATH", os.environ.get("PATH", "/usr/bin:/bin"))

    result = _output(
        await sandbox(tmp_path).invoke(
            "run_python",
            {"source": "import os; print(os.environ.get('SPIKE_FAKE_TOKEN', 'ABSENT'))"},
        )
    )
    assert "ABSENT" in str(result["stdout"])
    assert "sk-not-a-real-secret" not in str(result["stdout"])


async def test_what_a_script_does_need_still_reaches_it(tmp_path: Path) -> None:
    """A filter that dropped everything would pass the test above and break every script."""
    result = _output(
        await sandbox(tmp_path).invoke(
            "run_python", {"source": "import os; print('PATH' in os.environ)"}
        )
    )
    assert "True" in str(result["stdout"])


async def test_a_timed_out_program_is_dead_not_merely_abandoned(tmp_path: Path) -> None:
    """The mutation that found this gap deleted the kill, and every test stayed green.

    The earlier timeout test asserts the error text and the elapsed time, and both are identical
    whether the child was killed or simply left running: `wait_for` returns on the deadline either
    way, and the orphan carries on in the background. That is the vacuous-test shape recorded in
    Phase 4 — *nothing checked a timed-out child was actually dead* — and here it was, again.

    So this asks the child to leave a mark if it survives. It sleeps past the timeout and then
    touches a file; if the leash really killed it, the file never appears.
    """
    import anyio

    marker = tmp_path / "SURVIVED"
    with anyio.fail_after(10):
        observation = await sandbox(tmp_path, timeout_s=0.3).invoke(
            "run_shell", {"command": f"sleep 1.5; touch {marker.name}"}
        )
        assert observation.kind == "failed" and "timed out" in observation.error
        # Give an abandoned child more than enough time to reach its `touch`.
        await anyio.sleep(2.0)
    assert not marker.exists(), "the timed-out program was abandoned, not killed — it kept running"
