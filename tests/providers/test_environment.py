"""The environment a provider is launched with — from the record, never from a branch (D40).

The reference implementation keeps its provider record as data and then writes the spawn environment
as a hand-written `if (agentId === '...')` chain, one branch per provider. That is the shape this
package exists to avoid: every time provider knowledge leaks into a code path, the next provider
costs a phase instead of a file. So `set`, `strip` and `backfill` are fields, and this module is the
one piece of code that reads them.

**Stripping is the field that matters most**, and the measurement proving it real: Claude Code
refuses to start inside another Claude Code session, detecting it through an inherited variable. A
provider launched from within one never starts, and the failure arrives as a JSON-RPC internal error
with the real cause on a stderr nobody was reading.

**The spawn path carries what resolution searched.** Not a nicety — a binary found in a toolchain
directory can have a shebang naming an interpreter in another one, and a child whose `PATH` lacks it
fails to execute a file that certainly exists.
"""

from __future__ import annotations

from shadow_hdk.kernel import EnvVar, Provider
from shadow_hdk.providers.environment import environment_for

CLAUDE = Provider(
    id="claude-code",
    kind="agent",
    bin="claude",
    strip_env=("CLAUDECODE",),
    set_env=(EnvVar(name="SHADOW_HDK_RUN", value="1"),),
)


def test_what_the_record_sets_is_set() -> None:
    made = environment_for(CLAUDE, base={"HOME": "/home/x"}, search=[])

    assert made["SHADOW_HDK_RUN"] == "1"
    assert made["HOME"] == "/home/x"


def test_what_the_record_strips_is_gone() -> None:
    """Measured 2026-09-11: `CLAUDECODE=1` in the parent makes the child refuse to start."""
    made = environment_for(CLAUDE, base={"CLAUDECODE": "1", "HOME": "/home/x"}, search=[])

    assert "CLAUDECODE" not in made
    assert made["HOME"] == "/home/x", "stripping took something it was not asked for"


def test_stripping_does_not_care_about_case() -> None:
    """Environment variables are case-insensitive on one of the three platforms this runs on, and a
    strip that missed `ClaudeCode` there would be a bug nobody could reproduce on the other two."""
    made = environment_for(CLAUDE, base={"ClaudeCode": "1"}, search=[])

    assert not [key for key in made if key.upper() == "CLAUDECODE"]


def test_a_missing_variable_is_backfilled_from_the_os() -> None:
    """A child spawned with a stripped environment otherwise fails for want of something nobody
    thought to forward — a CLI that resolves its config home up front and exits when `HOME` is
    unset looks, from outside, exactly like a CLI that is not installed."""
    provider = Provider(id="x", kind="agent", bin="x", backfill_env=("HOME",))

    made = environment_for(provider, base={}, search=[], os_environ={"HOME": "/home/real"})

    assert made["HOME"] == "/home/real"


def test_a_backfill_never_overwrites_what_was_given() -> None:
    provider = Provider(id="x", kind="agent", bin="x", backfill_env=("HOME",))

    made = environment_for(
        provider, base={"HOME": "/home/given"}, search=[], os_environ={"HOME": "/home/real"}
    )

    assert made["HOME"] == "/home/given"


def test_the_spawn_path_carries_what_resolution_searched() -> None:
    """The asymmetry bug: resolved here, cannot execute there."""
    made = environment_for(
        CLAUDE, base={"PATH": "/usr/bin"}, search=["/opt/homebrew/bin", "/home/x/.local/bin"]
    )

    assert "/usr/bin" in made["PATH"]
    assert "/opt/homebrew/bin" in made["PATH"]
    assert "/home/x/.local/bin" in made["PATH"]


def test_the_spawn_path_keeps_the_callers_entries_first() -> None:
    """What the user's own environment points at wins over what we guessed."""
    made = environment_for(CLAUDE, base={"PATH": "/usr/bin"}, search=["/opt/homebrew/bin"])

    assert made["PATH"].split(":")[0] == "/usr/bin"


def test_no_directory_appears_twice_in_the_spawn_path() -> None:
    made = environment_for(CLAUDE, base={"PATH": "/usr/bin"}, search=["/usr/bin", "/usr/bin"])

    assert made["PATH"].split(":").count("/usr/bin") == 1


def test_the_record_cannot_smuggle_a_credential_out_of_the_environment() -> None:
    """D41: this package holds no secret, so nothing it builds may name one. A provider file is
    data a team writes, and `backfill_env = ["ANTHROPIC_API_KEY"]` in one would quietly move a
    caller's credential into a child that was never meant to have it."""
    provider = Provider(id="x", kind="agent", bin="x", backfill_env=("ANTHROPIC_API_KEY",))

    made = environment_for(
        provider, base={}, search=[], os_environ={"ANTHROPIC_API_KEY": "sk-secret"}
    )

    assert "ANTHROPIC_API_KEY" not in made
