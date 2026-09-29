"""The relay the child launches, on a path with a space in it — every transport (BUG-226, BUG-227).

Lane P found this in an installed macOS app: the kit sits in
`/Applications/Intent Studio.app/…/shadow-hdk-registry`, and the CLI was launched with
`{"command": "/Applications/Intent", "args": ["Studio.app/…/shadow-hdk-registry"]}`. The relay
never started (`posix_spawn 'stdio'`, ENOENT) — and because a governed CLI runs with its own
built-ins off (`--tools ""`, BUG-031), it had **no tools at all**. A turn that can read and write
nothing looks exactly like a model that chose not to: the most expensive possible way to fail.

The rule these tests pin: **an address is a command, never a command line.** Nothing splits it, so
no path can be split by accident — and the one thing the kit itself puts there is the whole path to
its own console script.

The second defect is in the same family and was found while proving the first: the ACP transport
built its MCP server entry with `env=[]`, so the relay learned neither the port nor the token and
answered `SHADOW_HDK_REGISTRY_PORT is not set to a port; nothing to relay to`. Same outcome — a
governed OpenCode with no tools — for a different reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.acp.agent import mcp_servers_from
from shadow_hdk.adapters.jsonl.transport import argv_for, mcp_config_for, mcp_overrides_for
from shadow_hdk.adapters.recording.offer import RELAY, relay_source
from shadow_hdk.kernel import Dialect, Provider, ToolSource

SPACED = "/Applications/Intent Studio.app/Contents/Resources/service/bin/shadow-hdk-registry"
"""Where macOS installs it. No developer tree ever has this path, which is why it was not caught."""

OURS = ToolSource(
    kind="mcp",
    address=SPACED,
    env=(("SHADOW_HDK_REGISTRY_PORT", "4242"), ("SHADOW_HDK_REGISTRY_TOKEN", "t0k")),
)


# ----------------------------------------------------- Claude Code: the JSON `--mcp-config`


def test_the_json_config_names_the_whole_path_as_the_command() -> None:
    server = json.loads(mcp_config_for((OURS,)))["mcpServers"]["shadow-hdk"]

    assert server["command"] == SPACED
    assert server["args"] == []
    assert server["env"] == {
        "SHADOW_HDK_REGISTRY_PORT": "4242",
        "SHADOW_HDK_REGISTRY_TOKEN": "t0k",
    }


def test_the_launch_argv_carries_that_config_whole() -> None:
    """End of the seam: what `open()` actually hands the CLI."""
    provider = Provider(
        id="claude-code",
        kind="agent",
        bin="claude",
        transport="jsonl",
        launch_args=("-p",),
        dialect=Dialect(mcp_config_arg="--mcp-config"),
    )

    argv = argv_for(provider, (OURS,))

    payload = json.loads(argv[argv.index("--mcp-config") + 1])
    assert payload["mcpServers"]["shadow-hdk"]["command"] == SPACED


# ----------------------------------------------------------------- Codex: the `-c` overrides


def test_the_codex_overrides_name_the_whole_path_as_the_command() -> None:
    flags = mcp_overrides_for("-c", (OURS,))

    assert flags[1] == f'mcp_servers.shadow-hdk.command="{SPACED}"'
    assert flags[3] == "mcp_servers.shadow-hdk.args=[]"


# ------------------------------------------------------------- OpenCode: ACP's `session/new`


def test_the_acp_server_entry_names_the_whole_path_as_the_command() -> None:
    (server,) = mcp_servers_from((OURS,))

    assert server.command == SPACED
    assert server.args == []


def test_the_acp_server_entry_carries_the_port_and_the_token() -> None:
    """BUG-227. Without these the relay starts and has nothing to relay to — the env only ever
    travels on the `ToolSource`; the ACP process inherits an environment that never had it."""
    (server,) = mcp_servers_from((OURS,))

    assert [(v.name, v.value) for v in server.env] == [
        ("SHADOW_HDK_REGISTRY_PORT", "4242"),
        ("SHADOW_HDK_REGISTRY_TOKEN", "t0k"),
    ]


# ------------------------------------------------------- where the kit finds its own relay


def test_the_relay_is_found_beside_the_running_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kit's console script is installed beside the interpreter running it. A `PATH` lookup
    answers for whatever environment the *service* was started with, which in a bundled app is a
    different one; the interpreter is the kit's own installation by construction."""
    bundle = tmp_path / "Intent Studio.app" / "bin"
    bundle.mkdir(parents=True)
    (bundle / RELAY).write_text("#!/bin/sh\n")
    monkeypatch.setattr("sys.executable", str(bundle / "python3.12"))

    source = relay_source(4242, "t0k")

    assert source.address == str(bundle / RELAY)
    assert " " in source.address, "the path this test is about"


def test_the_relay_falls_back_to_the_path_when_it_is_not_beside_the_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A kit imported from a source tree, or an interpreter that is not the one it was installed
    for: the old lookup, unchanged."""
    empty = tmp_path / "nowhere"
    empty.mkdir()
    monkeypatch.setattr("sys.executable", str(empty / "python3.12"))
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/local/bin/shadow-hdk-registry")

    assert relay_source(1, "t").address == "/usr/local/bin/shadow-hdk-registry"


def test_an_unfindable_relay_is_still_named_rather_than_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "nowhere"
    empty.mkdir()
    monkeypatch.setattr("sys.executable", str(empty / "python3.12"))
    monkeypatch.setattr("shutil.which", lambda _name: None)

    assert relay_source(1, "t").address == RELAY


# ------------------------------------------------------------------------ what stays true


def test_a_source_of_a_kind_nothing_serves_is_still_refused_by_name() -> None:
    with pytest.raises(ValueError, match="carrier-pigeon"):
        mcp_servers_from((ToolSource(kind="carrier-pigeon", address="x"),))


def test_an_http_source_still_becomes_an_http_server() -> None:
    (server,) = mcp_servers_from(
        (ToolSource(kind="mcp-http", address="http://127.0.0.1:8931/mcp"),)
    )

    assert getattr(server, "url", None) == "http://127.0.0.1:8931/mcp"


def test_a_second_source_is_still_named_apart() -> None:
    second: Any = ToolSource(kind="mcp", address="/tmp/other relay")
    servers = json.loads(mcp_config_for((OURS, second)))["mcpServers"]

    assert sorted(servers) == ["shadow-hdk", "shadow-hdk-1"]
    assert servers["shadow-hdk-1"]["command"] == "/tmp/other relay"
