"""A command in an environment runs on the runtime's leash — the sandbox adapter's claims, kept.

Timeout, output cap, stderr, exit codes, the working directory, and the operator's secrets withheld
from a script the model wrote. All were true of `sandbox_subprocess` and tested there; all carry
over, because the environment runs commands through the same `run_leashed`. `full` mode, so they
hold on any machine.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Completed
from shadow_hdk.kernel.observations import Observation


async def full(tmp_path: Path, **kw: Any) -> tuple[LocalEnvironment, Path]:
    root = tmp_path / "ws"
    root.mkdir()
    return await LocalEnvironment.open(root, mode="full", **kw), root


def output(observation: Observation) -> dict[str, Any]:
    assert isinstance(observation, Completed) and isinstance(observation.output, dict), observation
    return observation.output


async def test_python_runs_and_its_output_comes_back(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    done = output(await env.invoke("run_python", {"source": "print(6 * 7)"}))

    assert done["stdout"].strip() == "42" and done["exit_code"] == 0


async def test_a_shell_command_runs_inside_the_root(tmp_path: Path) -> None:
    env, root = await full(tmp_path)

    done = output(await env.invoke("run_shell", {"command": "pwd"}))

    assert Path(done["stdout"].strip()).resolve() == root.resolve()


async def test_a_script_that_fails_still_ran(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    done = output(await env.invoke("run_python", {"source": "raise SystemExit(3)"}))

    assert done["exit_code"] == 3


async def test_stderr_comes_back_too(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    done = output(
        await env.invoke("run_python", {"source": "import sys; print('warn', file=sys.stderr)"})
    )

    assert "warn" in done["stderr"]


async def test_a_runaway_script_is_stopped_by_the_clock(tmp_path: Path) -> None:
    env, _ = await full(tmp_path, timeout_s=0.5)

    done = await env.invoke("run_python", {"source": "import time; time.sleep(30)"})

    assert "timed out" in str(done)


async def test_output_beyond_the_cap_is_truncated_and_says_so(tmp_path: Path) -> None:
    env, _ = await full(tmp_path, output_limit=100)

    done = output(await env.invoke("run_python", {"source": "print('x' * 10_000)"}))

    assert len(done["stdout"]) <= 100
    assert done.get("truncated") is True


async def test_a_script_the_model_wrote_does_not_inherit_the_operators_secrets(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """The leash's environment, not the operator's (BUG-009). A model-written script must not be
    able to print the key that paid for it."""
    monkeypatch.setenv("SOME_API_KEY", "sk-should-not-leak")
    env, _ = await full(tmp_path)

    done = output(
        await env.invoke(
            "run_python", {"source": "import os; print(os.environ.get('SOME_API_KEY', 'ABSENT'))"}
        )
    )

    assert done["stdout"].strip() == "ABSENT"


async def test_what_a_script_does_need_still_reaches_it(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    done = output(
        await env.invoke("run_python", {"source": "import os; print(bool(os.environ.get('PATH')))"})
    )

    assert done["stdout"].strip() == "True"


async def test_running_code_is_never_reversible(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)
    effects = {r.id: r.component.effects for r in await env.registrations()}

    assert effects["run_shell"].reversible is False
    assert effects["run_python"].reversible is False


async def test_the_interpreter_is_the_one_on_the_path_not_this_process(tmp_path: Path) -> None:
    """`python3`, not `sys.executable`: inside a box the host's interpreter does not exist, and the
    same argv has to mean the same thing locally and in a sandbox."""
    env, _ = await full(tmp_path)

    done = output(
        await env.invoke("run_python", {"source": "import sys; print(sys.version_info.major)"})
    )

    assert done["stdout"].strip() == "3", (sys.executable, done)
