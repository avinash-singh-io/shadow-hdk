"""Providers are files, and a bad file is refused at load naming what is wrong (D40).

D17 made agent architectures TOML a team writes without touching Python; this is the same move for
providers, and the test of it is whether the **second** provider costs a file or a phase.

A loader that shrugs at a typo is worse than no loader: `strip_evn = ["CLAUDECODE"]` would parse,
load, and produce a provider that silently fails to start on the machines where it matters. So an
unknown key is an error, and the error names the file and the key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.providers.library import (
    HERE as LIBRARY,
)
from shadow_hdk.providers.library import (
    MalformedProvider,
    load_provider,
    shipped,
)

CLAUDE = """
id = "claude-code"
name = "Claude Code"
kind = "agent"
bin = "claude"
fallback_bins = ["openclaude"]
version_probe = ["--version"]
auth_probe = ["auth", "status"]
auth_failure_patterns = ["not logged in"]
strip_env = ["CLAUDECODE"]
transport = "acp"
injects_tools = "mcp"
install_hint = "npm i -g @zed-industries/claude-code-acp"

[[set_env]]
name = "SHADOW_HDK_HARNESS"
value = "1"
"""


def a_file(where: Path, text: str, name: str = "p.toml") -> Path:
    made = where / name
    made.write_text(text, encoding="utf-8")
    return made


def test_a_file_becomes_a_provider(tmp_path: Path) -> None:
    provider = load_provider(a_file(tmp_path, CLAUDE))

    assert provider.id == "claude-code"
    assert provider.kind == "agent"
    assert provider.fallback_bins == ("openclaude",)
    assert provider.strip_env == ("CLAUDECODE",)
    assert provider.set_env[0].name == "SHADOW_HDK_HARNESS"
    assert provider.injects_tools == "mcp"


def test_a_missing_required_field_is_refused_naming_it(tmp_path: Path) -> None:
    broken = a_file(tmp_path, 'id = "x"\nkind = "agent"\n')

    with pytest.raises(MalformedProvider, match="bin"):
        load_provider(broken)


def test_an_unknown_key_is_refused_rather_than_ignored(tmp_path: Path) -> None:
    """The typo that would otherwise ship: a provider that looks configured and is not."""
    typo = a_file(tmp_path, 'id = "x"\nkind = "agent"\nbin = "x"\nstrip_evn = ["A"]\n')

    with pytest.raises(MalformedProvider, match="strip_evn"):
        load_provider(typo)


def test_a_refusal_names_the_file(tmp_path: Path) -> None:
    """A library of twenty files and an error naming none of them is not a diagnosis."""
    typo = a_file(tmp_path, 'id = "x"\nkind = "agent"\nbin = "x"\nnope = 1\n', name="codex.toml")

    with pytest.raises(MalformedProvider, match="codex.toml"):
        load_provider(typo)


def test_a_kind_that_is_neither_seam_is_refused(tmp_path: Path) -> None:
    """D39: a provider sells inference or agency. A third value is a design question, not a typo,
    and it must not reach a caller that will branch on it."""
    odd = a_file(tmp_path, 'id = "x"\nkind = "hybrid"\nbin = "x"\n')

    with pytest.raises(MalformedProvider, match="hybrid"):
        load_provider(odd)


def test_broken_toml_is_refused_as_broken_toml(tmp_path: Path) -> None:
    with pytest.raises(MalformedProvider):
        load_provider(a_file(tmp_path, 'id = "x\n'))


# ------------------------------------------------------------------ what ships


def test_every_shipped_provider_parses() -> None:
    """The library is data, so nothing type-checks it. This does."""
    found = shipped()

    assert found, "the shipped library is empty"
    assert all(p.id for p in found.values())


def test_claude_code_ships_and_carries_its_measured_quirk() -> None:
    """Measured 2026-09-11: Claude Code refuses to launch inside another Claude Code session, and
    says which variable to clear. A record that forgot it produces a provider which never starts,
    and an error that names neither cause."""
    claude = shipped()["claude-code"]

    assert claude.kind == "agent"
    assert "CLAUDECODE" in claude.strip_env
    assert claude.auth_probe, "a provider nobody can ask is always `unknown`"
    assert claude.injects_tools == "mcp", "without injection the socket cannot close (D42)"


def test_the_marginal_provider_costs_a_file() -> None:
    """D40's whole claim, stated as a test — and the shape of the answer matters.

    Three providers ship across **two** transports. That ratio is the point: the unit of extension
    is the transport, not the agent. `opencode` cost one file because `acp` already existed;
    `codex` cost one file because `jsonl` already existed, written for Claude Code. The next agent
    costs a file unless it invents a protocol.

    The reference implementation makes the same cut and pays more for it: twenty-eight providers
    over a handful of hand-written stream parsers, with the per-provider parts in TypeScript. Here
    the per-provider parts are fields.
    """
    found = shipped()

    assert {"claude-code", "codex", "opencode"} <= set(found)
    assert {p.transport for p in found.values()} == {"acp", "jsonl"}
    assert found["codex"].transport == found["claude-code"].transport, (
        "codex reuses the transport written for Claude Code — that is what made it a file"
    )


def test_a_record_says_which_of_its_fields_were_measured_and_which_transcribed() -> None:
    """Codex was measured signed in on the owner's login (the hardening round after Phase 24):
    the turn's shapes, the sub-type, the usage, the override spelling. Two things still were not
    seen — a reasoning item and a mid-turn failure — and the header says so, with the source they
    are transcribed from.

    Transcribed and measured are different kinds of claim, and a file that hid the difference would
    invite somebody to trust a field nobody has run. The header says which is which; this makes the
    saying non-optional. (Written first as *nothing here is measured*, then *partly*; the premise
    moved twice, each time by running the thing.)
    """
    text = (LIBRARY / "codex.toml").read_text(encoding="utf-8")

    assert "Measured signed-in" in text
    assert "Still transcribed" in text, "the header must say what has not been run"
    assert "open-design" in text, "a transcribed field must name what it was transcribed from"
    assert "0.154.0" in text, "a measurement names the version it was made against"


def test_opencode_carries_what_was_measured_of_it() -> None:
    """Measured 2026-09-11 against opencode 1.18.21: `acp` is a documented subcommand, so this one
    speaks our transport natively and needs no bridge; `auth list` exits 0 and prints credential
    names rather than values."""
    opencode = shipped()["opencode"]

    assert opencode.launch_args == ("acp",)
    assert opencode.auth_probe == ("auth", "list")
    assert any(pair.name == "OPENCODE_DISABLE_PROJECT_CONFIG" for pair in opencode.set_env)


def test_claude_code_starts_from_a_clean_scope() -> None:
    """ENH-012, measured 2026-09-12 against claude 2.1.235 with a sentinel `CLAUDE.md` in the
    workspace: as launched before, the model quoted the sentinel and said its instructions named a
    memory directory to write to — a person's own `CLAUDE.md`, settings and auto-memory reaching a
    governed run. `--setting-sources ""` dropped the sentinel and kept the claude.ai login;
    `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` dropped the memory; `--bare` would drop both and the login
    with them, so it is not used. A run's instructions are the mode's behaviour and nothing else."""
    claude = shipped()["claude-code"]

    assert "--setting-sources" in claude.launch_args
    at = claude.launch_args.index("--setting-sources")
    assert claude.launch_args[at + 1] == "", "no settings source at all, not a narrower one"
    assert "--bare" not in claude.launch_args, "--bare never reads the keychain: it drops the login"
    assert any(
        pair.name == "CLAUDE_CODE_DISABLE_AUTO_MEMORY" and pair.value == "1"
        for pair in claude.set_env
    )


def test_the_measured_environment_quirks_survive() -> None:
    """Two fields, each one a measurement, each one silently fatal if it goes.

    `USER` — bisected 2026-09-11 against claude 2.1.235: with HOME, PATH and SHELL alone,
    `claude auth status` answers `"loggedIn": false` on a machine that is signed in. Of USER,
    LOGNAME, TMPDIR, XPC_SERVICE_NAME and SSH_AUTH_SOCK, only USER flips it. Without the field this
    library reports a working subscription as unusable and sends somebody to log in again.

    `CLAUDECODE` — measured the same day: Claude Code refuses to start inside another Claude Code
    session and names the variable to clear. Inherited, the child dies before the handshake.

    Neither has a test elsewhere that would notice, because both fail as a *wrong answer* rather
    than an error.
    """
    claude = shipped()["claude-code"]

    assert "USER" in claude.backfill_env
    assert "CLAUDECODE" in claude.strip_env


def test_the_signed_out_pattern_is_a_working_regex() -> None:
    """It was not, once. TOML literal strings need no escaping and the first draft doubled every
    backslash, so `"loggedIn": false` matched nothing and a signed-out install read as `unknown`
    instead of `not-signed-in` — a pattern that is present, plausible and inert."""
    import re

    claude = shipped()["claude-code"]
    said = '{\n  "loggedIn": false,\n  "authMethod": "none"\n}'

    assert any(re.search(p, said, re.IGNORECASE) for p in claude.auth_failure_patterns), (
        f"none of {claude.auth_failure_patterns} matches a real signed-out answer"
    )
