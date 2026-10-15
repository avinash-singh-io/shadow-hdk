"""A governed SDK boots beside, rather than inside, the repository it may inspect."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import Dialect, Provider, ToolSource
from shadow_hdk.providers import shipped


async def test_private_bootstrap_survives_turns_then_closes_even_after_process_exit(
    tmp_path: Path,
) -> None:
    dialect = replace(
        Dialect(
            done_on=("done",), done_at="text", session_id_at="session", resume_args=("resume",)
        ),
        private_working_directory=True,
    )
    cli = tmp_path / "cli"
    cli.write_text(
        "#!/usr/bin/env python3\nimport sys, pathlib, json\nsys.stdin.read()\n"
        "root=pathlib.Path.cwd()\n"
        "print(json.dumps({'type':'done','session':'remembered', 'text':json.dumps("
        "{'cwd':str(root),'files':sorted(p.name for p in root.iterdir()),"
        "'args':sys.argv[1:]})}),flush=True)\n"
    )
    cli.chmod(0o755)
    (tmp_path / "AGENTS.md").write_text("private repository instructions")
    provider = Provider(id="fake", kind="agent", bin="cli", transport="jsonl", dialect=dialect)
    session = JsonlSession(
        provider,
        binary=cli,
        env={"PATH": "/usr/bin:/bin"},
        workspace=tmp_path,
        tools=(ToolSource(kind="mcp", address="/host/registry"),),
    )
    bootstrap = None
    try:
        first = json.loads((await session.turn("go")).text)
        bootstrap = Path(first["cwd"])
        assert bootstrap != tmp_path and first["files"] == [".git"]
        second = json.loads((await session.turn("again")).text)
        assert (second["cwd"], second["args"], session.session_id) == (
            str(bootstrap),
            ["resume", "remembered"],
            "remembered",
        )
        assert bootstrap.exists() and (tmp_path / "AGENTS.md").exists()
    finally:
        await session.close()
    assert bootstrap is not None and not bootstrap.exists()
    await session.close()


async def test_an_uninjected_cli_keeps_its_working_directory(tmp_path: Path) -> None:
    from tests.adapters.jsonl.test_a_turn import a_provider

    cli = tmp_path / "cli"
    cli.write_text(
        "#!/usr/bin/env python3\nimport sys,pathlib,json\nsys.stdin.readline()\n"
        "print(json.dumps({'type':'result','result':str(pathlib.Path.cwd())}),flush=True)\n"
    )
    cli.chmod(0o755)
    session = JsonlSession(
        replace(
            a_provider(),
            dialect=replace(
                Dialect(resident=True, done_on=("result",), done_at="result"),
                private_working_directory=True,
            ),
        ),
        binary=cli,
        env={"PATH": "/usr/bin:/bin"},
        workspace=tmp_path,
    )
    try:
        turn = await session.turn("go")
        assert Path(turn.text) == tmp_path
    finally:
        await session.close()


def test_the_codex_record_disables_native_world_tools_only_when_tools_are_injected() -> None:
    from shadow_hdk.adapters.jsonl.transport import argv_for

    codex = shipped()["codex"]
    assert codex.dialect is not None and codex.dialect.private_working_directory
    dialect = TypeAdapter(Dialect).validate_json(TypeAdapter(Dialect).dump_json(codex.dialect))
    assert dialect.private_working_directory
    argv = argv_for(codex, (ToolSource(kind="mcp", address="/host/registry"),))
    for feature in (
        "shell_tool",
        "unified_exec",
        "view_image",
        "browser_use",
        "computer_use",
        "apps",
        "plugins",
        "multi_agent",
        "memories",
        "workspace_dependencies",
        "hooks",
    ):
        assert any(a == "--disable" and b == feature for a, b in zip(argv, argv[1:], strict=False))
    assert "--ignore-rules" in argv and "project_doc_max_bytes=0" in argv
    assert argv_for(codex, ()) == list(codex.launch_args)


async def test_cancelled_close_settles_before_removing_the_private_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.adapters.jsonl.test_a_turn import a_fake_cli, a_provider

    provider = replace(
        a_provider(),
        dialect=Dialect(
            done_on=("result",),
            done_at="result",
            private_working_directory=True,
        ),
    )
    session = JsonlSession(
        provider,
        binary=a_fake_cli(tmp_path, [{"type": "result", "result": "done"}]),
        env={"PATH": "/usr/bin:/bin"},
        workspace=tmp_path,
        tools=(ToolSource(kind="mcp", address="/host/registry"),),
    )
    await session.turn("go")
    assert session._private_workspace is not None
    directory = Path(session._private_workspace.name)
    entered, finish = asyncio.Event(), asyncio.Event()
    original = session._close_process

    async def slow() -> None:
        entered.set()
        await finish.wait()
        await original()

    monkeypatch.setattr(session, "_close_process", slow)
    task = asyncio.create_task(session.close())
    try:
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and directory.exists()
    finally:
        finish.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await session.close()
    assert not directory.exists()


async def test_launch_catalogue_is_restricted_once_retained_for_resume_and_removed(
    tmp_path: Path,
) -> None:
    import os

    from shadow_hdk.providers.library import provider_from_data

    cli = tmp_path / "cli"
    cli.write_text(
        "#!/usr/bin/env python3\nimport sys,pathlib,json,os\n"
        "if sys.argv[1:] == ['metadata']:\n"
        " pathlib.Path("
        + repr(str(tmp_path / "probes"))
        + ").open('a').write(os.environ['SDK_HOME']+'\\n')\n"
        " print(json.dumps({'models':[{'native':True,'patch':'freeform',"
        "'context':777,'role':'unchanged'}]}))\n"
        "else:\n"
        " sys.stdin.read()\n"
        " file=pathlib.Path(sys.argv[sys.argv.index('--catalogue')+1])\n"
        " print(json.dumps({'type':'done','session':'kept','text':json.dumps("
        "{'path':str(file),'data':json.loads(file.read_text()),"
        "'home':os.environ['SDK_HOME']})}))\n"
    )
    cli.chmod(0o755)
    provider = provider_from_data(
        {
            "id": "catalogue-cli",
            "kind": "agent",
            "bin": "cli",
            "transport": "jsonl",
            "dialect": {
                "done_on": ["done"],
                "done_at": "text",
                "session_id_at": "session",
                "resume_args": ["resume"],
                "launch_catalogue": {
                    "probe_args": ["metadata"],
                    "entries_at": "models",
                    "replace_fields": [{"name": "native", "value": False}, {"name": "patch"}],
                    "config_arg": "--catalogue",
                    "config_template": "{path}",
                    "isolated_env_keys": ["SDK_HOME"],
                },
            },
        },
        where="fixture",
    )
    session = JsonlSession(
        provider,
        binary=cli,
        env={**os.environ, "SDK_HOME": "original-auth-home"},
        workspace=tmp_path,
        tools=(ToolSource(kind="mcp", address="/host/registry"),),
    )
    path = None
    try:
        first = json.loads((await session.turn("go")).text)
        path = Path(first["path"])
        assert first["data"] == {
            "models": [{"native": False, "patch": None, "context": 777, "role": "unchanged"}]
        }
        assert first["home"] == "original-auth-home" and path.is_file()
        again = json.loads((await session.turn("again")).text)
        assert again["path"] == str(path) and again["data"] == first["data"]
        probes = (tmp_path / "probes").read_text().splitlines()
        assert len(probes) == 1 and probes[0] != "original-auth-home"
        assert provider.dialect is not None
        assert (
            TypeAdapter(Dialect).validate_json(TypeAdapter(Dialect).dump_json(provider.dialect))
            == provider.dialect
        )
    finally:
        await session.close()
    assert path is not None and not path.exists()


@pytest.mark.parametrize("payload", ["not json", '{"models":[]}', '{"models":[{"native":true}]}'])
async def test_a_bad_launch_catalogue_is_refused_before_sdk_turn(
    tmp_path: Path, payload: str
) -> None:
    import os

    from shadow_hdk.providers.library import provider_from_data

    cli = tmp_path / "cli"
    marker = tmp_path / "launched"
    cli.write_text(
        '#!/usr/bin/env python3\nimport sys,pathlib\nif sys.argv[1:]==["metadata"]: print('
        + repr(payload)
        + ")\nelse: pathlib.Path("
        + repr(str(marker))
        + ").touch()\n"
    )
    cli.chmod(0o755)
    provider = provider_from_data(
        {
            "id": "fake",
            "kind": "agent",
            "bin": "cli",
            "transport": "jsonl",
            "dialect": {
                "launch_catalogue": {
                    "probe_args": ["metadata"],
                    "entries_at": "models",
                    "replace_fields": [{"name": "native", "value": False}, {"name": "patch"}],
                    "config_arg": "--catalogue",
                    "config_template": "{path}",
                }
            },
        },
        where="fixture",
    )
    session = JsonlSession(
        provider,
        binary=cli,
        env=os.environ,
        tools=(ToolSource(kind="mcp", address="/host/registry"),),
    )
    try:
        with pytest.raises(RuntimeError, match="catalogue"):
            await session.turn("go")
        assert not marker.exists()
    finally:
        await session.close()
