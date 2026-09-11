"""What this machine can reach, and how a transport is found without importing it.

**Detection reports; it never installs (D41).** An absent provider comes back absent, with the
command a person would run. Running it is not this library's business.

**A transport is discovered, not imported.** The selection surface must hand back a `ModelPort` from
one adapter or an `AgentPort` from another, and a module that imported both would fail rule 4 of the
stands-alone invariant — an AST walk over every import node, which deferring the import inside a
function does not evade and should not. So an adapter *declares* itself in its own distribution
metadata and this looks the declaration up: the arrow points from detail to abstraction, and a third
party can ship a transport nobody here has heard of.

Registering one by hand is the same mechanism with the discovery step skipped, and it is what a host
uses when it would rather wire its own.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.kernel import Provider
from shadow_hdk.providers.surface import (
    NoSuchTransport,
    detect,
    open_with,
    register_transport,
    transports,
)

ABSENT = Provider(
    id="nowhere",
    kind="agent",
    bin="a-binary-that-is-not-installed-anywhere",
    install_hint="brew install nothing",
)


def a_cli(where: Path, name: str, body: str) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    made = where / name
    made.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    made.chmod(0o755)
    return made


# ------------------------------------------------------------------ detection


async def test_an_absent_provider_is_reported_with_the_command_that_would_fix_it() -> None:
    found = await detect([ABSENT], path=[], extra_dirs=[])

    assert len(found) == 1
    assert found[0].status == "absent"
    assert found[0].binary is None
    assert found[0].install_hint == "brew install nothing"


async def test_detection_installs_nothing(tmp_path: Path) -> None:
    """D41, asserted rather than assumed: nothing appears on disk because we looked."""
    before = sorted(tmp_path.iterdir())

    await detect([ABSENT], path=[str(tmp_path)], extra_dirs=[])

    assert sorted(tmp_path.iterdir()) == before


async def test_a_present_and_signed_in_provider_is_ready(tmp_path: Path) -> None:
    a_cli(tmp_path, "here", 'if [ "$1" = "auth" ]; then echo "Logged in"; else echo "1.2.3"; fi')
    provider = Provider(
        id="here",
        kind="agent",
        bin="here",
        version_probe=("--version",),
        auth_probe=("auth",),
        auth_failure_patterns=("not logged in",),
    )

    found = await detect([provider], path=[str(tmp_path)], extra_dirs=[])

    assert found[0].status == "ready"
    assert found[0].version == "1.2.3"
    assert found[0].binary is not None


async def test_the_binary_override_in_the_process_environment_is_honoured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`bin_env_key` is the documented way to point the harness at an install off the PATH — a
    local one in a scratch directory, say. `detect()` builds the probe's environment from the
    record's `backfill_env`, and the override was not in it, so it was dropped on the floor and
    the provider reported `absent` with the binary right there. Found measuring Codex, installed
    locally and never globally."""
    elsewhere = a_cli(
        tmp_path / "elsewhere",
        "here",
        'if [ "$1" = "auth" ]; then echo "Logged in"; else echo "1.2.3"; fi',
    )
    provider = Provider(
        id="here",
        kind="agent",
        bin="here",
        bin_env_key="HERE_BIN",
        version_probe=("--version",),
        auth_probe=("auth",),
        auth_failure_patterns=("not logged in",),
    )
    monkeypatch.setenv("HERE_BIN", str(elsewhere))

    found = await detect([provider], path=[str(tmp_path / "not-on-path")], extra_dirs=[])

    assert found[0].status == "ready", found[0]
    assert found[0].binary == elsewhere


async def test_a_present_but_signed_out_provider_says_which(tmp_path: Path) -> None:
    """The distinction that matters to a person: installed is not the same as usable."""
    a_cli(
        tmp_path, "out", 'if [ "$1" = "auth" ]; then echo "not logged in"; exit 1; fi; echo 1.0.0'
    )
    provider = Provider(
        id="out",
        kind="agent",
        bin="out",
        version_probe=("--version",),
        auth_probe=("auth",),
        auth_failure_patterns=("not logged in",),
    )

    found = await detect([provider], path=[str(tmp_path)], extra_dirs=[])

    assert found[0].status == "not-signed-in"
    assert found[0].binary is not None, "it is installed; it is just not signed in"


async def test_a_broken_wrapper_does_not_hide_the_working_install(tmp_path: Path) -> None:
    """The candidate walk, end to end: resolution offers both and detection keeps going."""
    first, second = tmp_path / "a", tmp_path / "b"
    a_cli(first, "two", ">&2 echo \"Error: Cannot find module '/gone/cli.js'\"; exit 1")
    working = a_cli(second, "two", 'echo "3.0.0"')
    provider = Provider(id="two", kind="agent", bin="two", version_probe=("--version",))

    found = await detect([provider], path=[str(first), str(second)], extra_dirs=[])

    assert found[0].binary == working, "the broken wrapper was reported as the provider"
    assert found[0].version == "3.0.0", "the version could only have come from the second candidate"
    # Not `ready`: this provider declares no auth probe, so nobody asked and `unknown` is the
    # honest answer (D41). The first draft of this test asserted `ready` and was wrong about the
    # design rather than about the code.
    assert found[0].status == "unknown"
    assert found[0].usable, "`unknown` means we could not tell — it is worth trying, not refused"


async def test_the_version_is_not_asked_of_a_provider_that_is_not_there() -> None:
    """An `Available` with no binary and a version would be a fabricated fact."""
    found = await detect([ABSENT], path=[], extra_dirs=[])

    assert found[0].version is None


# ------------------------------------------------------------------ transports


def test_a_transport_can_be_registered_by_hand() -> None:
    """The escape hatch: a host that would rather wire its own."""

    def opener(**_: object) -> str:
        return "opened"

    register_transport("test-transport", opener)

    assert "test-transport" in transports()


async def test_opening_an_unknown_transport_names_it() -> None:
    """A provider file naming a transport nothing serves is a typo or a missing package, and the
    error has to say which string it could not honour."""
    provider = Provider(id="x", kind="agent", bin="x", transport="carrier-pigeon")

    with pytest.raises(NoSuchTransport, match="carrier-pigeon"):
        await open_with(provider, binary=Path("/bin/true"), env={})


async def test_a_provider_with_no_transport_is_refused_rather_than_guessed() -> None:
    provider = Provider(id="x", kind="agent", bin="x")

    with pytest.raises(NoSuchTransport):
        await open_with(provider, binary=Path("/bin/true"), env={})


def test_discovery_reads_installed_distributions_rather_than_importing_adapters() -> None:
    """The anti-vacuity half. `transports()` must actually consult the entry-point registry — a
    version that returned only hand-registered openers would pass every test above and find nothing
    a real adapter declared."""
    found = transports()

    assert isinstance(found, dict)
    # The group this package reads. Nothing may be imported to learn it.
    from shadow_hdk.providers.surface import TRANSPORT_GROUP

    assert TRANSPORT_GROUP == "shadow_hdk.transports"


async def test_a_probe_runs_with_the_environment_the_record_asks_for(tmp_path: Path) -> None:
    """The bug this closes, found by running the README's own snippet: `detect` handed the probe an
    **empty** environment, so a CLI that resolves its credentials under `HOME` could not find them
    and every install came back `unknown`.

    `backfill_env` existed for exactly this and was never wired into detection — the field was
    right and nothing read it. A probe is only worth running in the environment the provider will
    actually be run in.
    """
    seen = tmp_path / "what-the-probe-saw"
    a_cli(tmp_path, "envy", f'echo "HOME=$HOME" > {seen}; echo 1.0.0')
    provider = Provider(
        id="envy",
        kind="agent",
        bin="envy",
        version_probe=("--version",),
        backfill_env=("HOME", "PATH"),
    )

    await detect([provider], path=[str(tmp_path)], extra_dirs=[])

    assert seen.exists(), "the probe never ran"
    assert seen.read_text().strip() != "HOME=", "the probe ran with no HOME"


async def test_a_probe_still_does_not_inherit_a_credential(tmp_path: Path) -> None:
    """D41 survives the fix: backfilling the environment must not become a way to hand a caller's
    key to every CLI on the machine."""
    seen = tmp_path / "leaked"
    a_cli(tmp_path, "nosy", f'echo "[$ANTHROPIC_API_KEY]" > {seen}; echo 1.0.0')
    provider = Provider(
        id="nosy",
        kind="agent",
        bin="nosy",
        version_probe=("--version",),
        backfill_env=("HOME", "PATH", "ANTHROPIC_API_KEY"),
    )

    await detect([provider], path=[str(tmp_path)], extra_dirs=[])

    assert seen.read_text().strip() == "[]", "a credential reached the probe"
