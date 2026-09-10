"""Asking a provider about itself — and believing only what it actually said (D41).

Every claim here is run against a **real subprocess**: a small script the test writes and executes.
A double would prove the parsing and none of the things that actually go wrong, and what goes wrong
here is process-shaped — a wrapper whose target was uninstalled, a CLI that exits non-zero because
it dislikes an argument, a status command that answers in prose.

**Authentication has three answers and the third is the one that matters.** Signed in, not signed
in, and *could not tell*. A provider whose wording changed, or which has no status command at all,
must come back `unknown` — reporting *not signed in* because we could not tell sends somebody to
fix what is not broken, and reporting *ready* because nothing matched is worse.

**No credential is ever read, returned or logged.** The probe asks a question and reads an answer.
If the answer contains a secret, it does not survive the probe.
"""

from __future__ import annotations

from pathlib import Path

from shadow_hdk.kernel import Provider
from shadow_hdk.providers.probes import ask_auth, ask_version, newer_or_same

CLAUDE = Provider(
    id="claude-code",
    kind="agent",
    bin="claude",
    version_probe=("--version",),
    auth_probe=("auth", "status"),
    auth_failure_patterns=("not logged in", "run .* login"),
)


def a_cli(where: Path, name: str, body: str) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    made = where / name
    made.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    made.chmod(0o755)
    return made


# ------------------------------------------------------------------ version


async def test_a_version_comes_back(tmp_path: Path) -> None:
    cli = a_cli(tmp_path, "claude", 'echo "2.1.235 (Claude Code)"')

    asked = await ask_version(CLAUDE, cli, env={})

    assert asked.version == "2.1.235", asked
    assert asked.status == "ready"


async def test_a_version_below_the_floor_is_too_old(tmp_path: Path) -> None:
    """A floor exists because somebody measured a break below it, so the answer is `too-old` and
    not a refusal to run — the caller decides what to do about it."""
    cli = a_cli(tmp_path, "claude", 'echo "0.9.1"')
    provider = Provider(
        id="c", kind="agent", bin="claude", version_probe=("--version",), minimum_version="1.0.0"
    )

    asked = await ask_version(provider, cli, env={})

    assert asked.status == "too-old"
    assert asked.version == "0.9.1"


async def test_a_launcher_that_never_reached_its_program_is_not_a_program_that_failed(
    tmp_path: Path,
) -> None:
    """The distinction the reference paid for. A global npm wrapper whose package was uninstalled
    starts, runs node, and only then fails to load the script it names — a plain non-zero exit with
    the launcher's own vocabulary on stderr. Nothing failed to *start*, so it looks exactly like a
    healthy CLI that dislikes `--version`, and the remedies are opposite: abandon this candidate and
    try the next, versus keep it and stop looking."""
    broken = a_cli(tmp_path, "claude", ">&2 echo \"Error: Cannot find module '/x/cli.js'\"; exit 1")

    asked = await ask_version(CLAUDE, broken, env={})

    assert asked.status == "absent", asked
    assert asked.unusable is True, "a broken wrapper must be abandoned for the next candidate"


async def test_a_cli_that_merely_dislikes_the_argument_is_still_the_right_binary(
    tmp_path: Path,
) -> None:
    """The other side. Over-matching here sends a working CLI's user to a different install."""
    fussy = a_cli(tmp_path, "claude", '>&2 echo "unknown option --version"; exit 1')

    asked = await ask_version(CLAUDE, fussy, env={})

    assert asked.unusable is False, "a real answer from the right binary was thrown away"


async def test_a_provider_with_no_version_probe_is_not_guessed_at(tmp_path: Path) -> None:
    cli = a_cli(tmp_path, "x", "exit 0")
    provider = Provider(id="x", kind="agent", bin="x")

    asked = await ask_version(provider, cli, env={})

    assert asked.version is None
    assert asked.status == "ready", "no probe is not a failure; it is nothing asked"


# ------------------------------------------------------------------ authentication


async def test_a_signed_in_provider_is_ready(tmp_path: Path) -> None:
    cli = a_cli(tmp_path, "claude", 'echo "Logged in as someone@example.com"')

    asked = await ask_auth(CLAUDE, cli, env={})

    assert asked.status == "ready"


async def test_a_signed_out_provider_says_so_and_says_how(tmp_path: Path) -> None:
    cli = a_cli(
        tmp_path, "claude", ">&2 echo \"You are not logged in. Run 'claude /login'.\"; exit 1"
    )

    asked = await ask_auth(CLAUDE, cli, env={})

    assert asked.status == "not-signed-in"
    assert "login" in (asked.message or "").lower()


async def test_output_that_matches_nothing_is_unknown_rather_than_either_answer(
    tmp_path: Path,
) -> None:
    """The whole reason the fifth answer exists. A CLI that reworded its message must not read as
    authenticated, and must not read as signed out either."""
    cli = a_cli(tmp_path, "claude", '>&2 echo "auth subsystem unavailable (E_WEIRD)"; exit 3')

    asked = await ask_auth(CLAUDE, cli, env={})

    assert asked.status == "unknown", asked


async def test_a_provider_that_cannot_be_asked_is_unknown(tmp_path: Path) -> None:
    """No `auth_probe` on the record means nobody asked — not that it is fine."""
    cli = a_cli(tmp_path, "x", "exit 0")
    provider = Provider(id="x", kind="agent", bin="x")

    asked = await ask_auth(provider, cli, env={})

    assert asked.status == "unknown"


async def test_the_probe_never_carries_a_credential_back(tmp_path: Path) -> None:
    """D41. A status command that prints a token — and some do — must not put it in a result that
    is about to be logged, rendered in a UI, or written to a diagnostic file."""
    cli = a_cli(tmp_path, "claude", 'echo "Logged in. token=sk-ant-SECRETVALUE123456789"')

    asked = await ask_auth(CLAUDE, cli, env={})

    assert "SECRETVALUE" not in repr(asked), repr(asked)


# ------------------------------------------------------------------ the comparison


def test_version_ordering_is_numeric_not_lexicographic() -> None:
    """`"10" < "9"` as strings, which would report a new CLI as too old."""
    assert newer_or_same("2.1.235", "2.1.9") is True
    assert newer_or_same("0.9.1", "1.0.0") is False
    assert newer_or_same("1.0.0", "1.0.0") is True
    assert newer_or_same("2.1", "2.1.0") is True


def test_a_version_that_cannot_be_compared_does_not_claim_too_old() -> None:
    """A CLI versioned `nightly-abc123` is not old; it is unparseable, and the honest answer is to
    let it through rather than to refuse a working install on a string comparison."""
    assert newer_or_same("nightly-abc123", "1.0.0") is True
