"""A governed Codex run does not pick up the person's own MCP servers (H23, ENH-005, phase 66).

**The registry's direction is ours → the CLI** (D42): the kit offers a run's tools to Codex through
the socket, judged and recorded. A server the person configured in their own
`$CODEX_HOME/config.toml` is the opposite — a tool path into the run that no mode judged and no
record carries. For a *governed* run that is the whole problem: the mode said what this agent may
do, and something else was answering too.

Claude Code has `--strict-mcp-config` and the kit has used it since Phase 31. ENH-005, measured
2026-09-12 on `codex-cli 0.154.0`, concluded Codex had no equivalent and needed one **upstream**,
and the shipped record said so in prose.

**It has one.** `codex exec --help` on that same version lists:

    --ignore-user-config
            Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`

Two properties make it the right flag rather than a blunt one: our own servers go in as `-c`
command-line overrides, not config, so they survive it; and **auth still uses `CODEX_HOME`**, so a
subscription login survives it too. Verified by parsing on the installed CLI, with an invented flag
as the control — `codex exec --no-such-flag-at-all --help` is rejected, so acceptance means
something.

What it does **not** fix, and what this therefore does not claim: Codex has no flag to refuse its
*own* tools. Its native reads stay its own, confined by `--sandbox read-only` but outside the
registry. So `tool_path` stays `uncontrolled` — the honest reason has simply changed, and the record
now says which part is controlled and which is not.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from shadow_hdk.kernel import Provider, ToolSource
from shadow_hdk.providers.library import shipped

STRICT = "--ignore-user-config"


def codex_record() -> Provider:
    found = shipped().get("codex")
    assert found is not None, "the shipped library has no codex record"
    return found


# ------------------------------------------------------------------ the record carries the flag


def test_the_codex_record_names_a_strict_flag() -> None:
    """The field existed and was empty, which is why the leak survived three phases."""
    record = codex_record()
    dialect = record.dialect
    assert dialect is not None

    assert dialect.mcp_strict_args == (STRICT,), dialect.mcp_strict_args


def test_a_governed_launch_carries_it() -> None:
    """Through `argv_for`, which is what actually reaches the process."""
    from shadow_hdk.adapters.jsonl.transport import argv_for

    argv = argv_for(
        codex_record(),
        (ToolSource(kind="mcp", address="/path/to/relay"),),
    )

    assert STRICT in argv, argv


def test_our_own_server_still_goes_in_beside_it() -> None:
    """The flag drops *config* servers. Ours arrive as `-c` overrides on the command line, so they
    must survive it — if they did not, a governed run would have no tools at all, which is the
    BUG-226 outcome by another route."""
    from shadow_hdk.adapters.jsonl.transport import argv_for

    argv = argv_for(
        codex_record(),
        (ToolSource(kind="mcp", address="/path/to/relay"),),
    )

    joined = " ".join(argv)
    assert STRICT in argv
    assert "mcp_servers.shadow-hdk" in joined, joined
    assert "/path/to/relay" in joined, "our relay must still be named"


def test_a_run_with_no_tools_does_not_carry_it() -> None:
    """The flag belongs to the governed path. A launch injecting nothing is not governing anything,
    and dropping a person's configuration there would be taking something away for no reason."""
    from shadow_hdk.adapters.jsonl.transport import argv_for

    argv = argv_for(codex_record(), ())

    assert STRICT not in argv, argv


# ------------------------------------------------------------------ and the CLI really takes it


@pytest.mark.live
def test_the_installed_codex_accepts_the_flag() -> None:
    """Measured, not transcribed. ENH-005 said this flag did not exist; the only way that claim gets
    corrected honestly is by asking the binary.

    Paired with an invented flag, because `--help` short-circuits in some CLIs and acceptance would
    then prove nothing.
    """
    binary = shutil.which("codex")
    if binary is None:
        pytest.skip("codex is not installed on this machine")

    good = subprocess.run(
        [binary, "exec", STRICT, "--json", "--skip-git-repo-check", "--help"],
        capture_output=True,
        timeout=60,
    )
    bad = subprocess.run(
        [binary, "exec", "--no-such-flag-at-all", "--help"], capture_output=True, timeout=60
    )

    assert good.returncode == 0, good.stderr.decode()[:400]
    assert bad.returncode != 0, "the control was accepted, so acceptance proves nothing here"


def test_the_records_evidence_no_longer_claims_the_servers_cannot_be_excluded() -> None:
    """The prose was the claim, and it is the thing that was false. `tool_path` stays
    `uncontrolled` — Codex's own reads are still its own — but for the right reason now."""
    record = codex_record()
    capabilities = record.capabilities
    said = " ".join(e.source for e in capabilities.evidence if e.axis == "tool_path").lower()

    assert capabilities.tool_path == "uncontrolled", capabilities.tool_path
    assert "cannot be disabled" not in said, said
    assert "native" in said, f"the reason must now be the native reads: {said!r}"
