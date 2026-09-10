"""Finding a provider's binary, and why the obvious way is wrong.

Three claims, each a lesson the reference implementation paid for and each one a thing that fails
silently if you skip it:

**Every candidate, in order — not the winner.** A directory earlier on the path can hold a wrapper
left behind by a half-finished install. Resolution cannot tell it from a working CLI; only spawning
can. So the caller is given the whole list and walks it until one runs.

**`PATH` is not the search path.** A process started by a launcher rather than a shell inherits a
minimal `PATH`, and the user's tools are in Homebrew, `~/.local/bin`, a version manager's directory.
Searching only `PATH` reports a CLI absent on the machine it is installed on.

**Resolution and spawning must search the same directories.** A binary can resolve here and still
fail to execute, because its shebang names an interpreter that lives in one of those extra
directories and the child's `PATH` did not carry it. Symmetry is the fix, and asymmetry is a bug
that only appears on other people's machines.
"""

from __future__ import annotations

import os
from pathlib import Path

from shadow_hdk.kernel import Provider
from shadow_hdk.providers.resolution import candidates, search_dirs

CLAUDE = Provider(id="claude-code", kind="agent", bin="claude", fallback_bins=("openclaude",))


def an_executable(where: Path, name: str) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    made = where / name
    made.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    made.chmod(0o755)
    return made


def test_every_candidate_comes_back_in_order(tmp_path: Path) -> None:
    """The claim: a broken wrapper first on the path must not hide a working CLI behind it."""
    first, second = tmp_path / "a", tmp_path / "b"
    broken = an_executable(first, "claude")
    working = an_executable(second, "claude")

    found = candidates(CLAUDE, path=[str(first), str(second)], extra_dirs=[])

    assert found == [broken, working], "resolution returned a winner instead of the list"


def test_a_fallback_binary_is_tried_after_the_real_name(tmp_path: Path) -> None:
    """A single-binary install of an argv-compatible fork is still this provider."""
    here = tmp_path / "bin"
    fork = an_executable(here, "openclaude")

    found = candidates(CLAUDE, path=[str(here)], extra_dirs=[])

    assert found == [fork]


def test_the_real_name_outranks_a_fork(tmp_path: Path) -> None:
    """Order matters: `bin` before `fallback_bins`, whatever the directory order says."""
    here = tmp_path / "bin"
    fork = an_executable(here, "openclaude")
    real = an_executable(here, "claude")

    found = candidates(CLAUDE, path=[str(here)], extra_dirs=[])

    assert found == [real, fork]


def test_a_directory_is_searched_once(tmp_path: Path) -> None:
    """A duplicated `PATH` entry must not produce the same binary twice — a caller walking
    candidates would spawn a known-broken wrapper a second time."""
    here = tmp_path / "bin"
    only = an_executable(here, "claude")

    found = candidates(CLAUDE, path=[str(here), str(here)], extra_dirs=[])

    assert found == [only]


def test_an_environment_override_wins_outright(tmp_path: Path) -> None:
    """The escape hatch: a machine whose layout nothing here can be expected to guess."""
    on_path = an_executable(tmp_path / "bin", "claude")
    elsewhere = an_executable(tmp_path / "somewhere", "claude")
    provider = Provider(id="c", kind="agent", bin="claude", bin_env_key="CLAUDE_BIN")

    found = candidates(
        provider,
        path=[str(on_path.parent)],
        extra_dirs=[],
        env={"CLAUDE_BIN": str(elsewhere)},
    )

    assert found == [elsewhere], "the override did not win"


def test_an_override_naming_nothing_falls_back_rather_than_failing(tmp_path: Path) -> None:
    """A stale override left in a shell profile must not make a working install unreachable."""
    on_path = an_executable(tmp_path / "bin", "claude")
    provider = Provider(id="c", kind="agent", bin="claude", bin_env_key="CLAUDE_BIN")

    found = candidates(
        provider,
        path=[str(on_path.parent)],
        extra_dirs=[],
        env={"CLAUDE_BIN": str(tmp_path / "gone")},
    )

    assert found == [on_path]


def test_a_file_that_is_not_executable_is_not_a_candidate(tmp_path: Path) -> None:
    """A stray file of the right name is not a CLI, and spawning it wastes a candidate."""
    here = tmp_path / "bin"
    here.mkdir()
    (here / "claude").write_text("notes about claude\n", encoding="utf-8")

    assert candidates(CLAUDE, path=[str(here)], extra_dirs=[]) == []


# ------------------------------------------------------------------ the search path


def test_the_search_path_reaches_past_PATH() -> None:
    """The bug this prevents: a CLI reported absent on the machine it is installed on, because the
    process was started by a launcher with a minimal `PATH`."""
    dirs = search_dirs(path=["/usr/bin"], home=Path("/home/someone"))

    assert "/usr/bin" in dirs
    assert any(d.endswith("/.local/bin") for d in dirs), dirs
    assert len(dirs) > 1


def test_the_search_path_is_ordered_and_deduplicated() -> None:
    """`PATH` first — what the user's shell would find is what we should find — and a directory
    named twice is searched once."""
    dirs = search_dirs(path=["/usr/bin", "/usr/bin"], home=Path("/home/someone"))

    assert dirs[0] == "/usr/bin"
    assert dirs.count("/usr/bin") == 1


def test_the_real_search_path_uses_this_machine() -> None:
    """The anti-vacuity half: a default that read nothing would make every test above synthetic."""
    dirs = search_dirs()

    assert dirs, "the search path is empty on a machine that has one"
    assert any(part in dirs for part in os.environ.get("PATH", "").split(os.pathsep) if part)
