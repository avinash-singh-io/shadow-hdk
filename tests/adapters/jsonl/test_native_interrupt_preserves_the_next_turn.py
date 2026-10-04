"""H7: native interrupt preserves the process without leaking the interrupted reply."""

import asyncio
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

import shadow_hdk.adapters.jsonl.session as session_module
import shadow_hdk.providers.library as provider_library
from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import Dialect

pytestmark = pytest.mark.anyio

CONTROL = (
    '{"type":"control_request","request_id":"shadow-interrupt","request":{"subtype":"interrupt"}}'
)


class ObservedSession(JsonlSession):
    started: asyncio.Event

    async def _a_line_from(self, process: asyncio.subprocess.Process) -> bytes:
        line = await super()._a_line_from(process)
        if b'"ready"' in line:
            self.started.set()
        return line


@pytest.mark.parametrize("explicit_line", [False, True])
@pytest.mark.parametrize("finish_during_drain", [False, True])
async def test_interrupt_keeps_the_process_and_discards_the_old_result(
    tmp_path: Path, explicit_line: bool, finish_during_drain: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = tmp_path / "fake-cli"
    cli.write_text(
        """#!/usr/bin/env python3
import sys, json
interrupted = False
for raw in sys.stdin:
    event = json.loads(raw)
    if event.get('type') == 'control_request':
        interrupted = (event.get('request') == {'subtype': 'interrupt'}
                       and bool(event.get('request_id')))
        reply = {'type':'control_response','response':{'request_id':event.get('request_id')}}
        print(json.dumps(reply), flush=True)
        thinking = {'type':'thinking','thinking':'OLD THOUGHT'}
        print(json.dumps({'type':'assistant','message':{'content':[thinking]}}), flush=True)
        delta = {'type':'thinking_delta','thinking':'OLD DELTA'}
        print(json.dumps({'type':'stream_event','event':{'delta':delta}}), flush=True)
        print(json.dumps({'type':'result','result':'OLD RESULT','is_error':False}), flush=True)
    elif event['message']['content'][0]['text'] == 'first':
        print(json.dumps({'type':'ready'}), flush=True)
    else:
        text = 'NEXT RESULT' if interrupted else 'MISSED INTERRUPT'
        print(json.dumps({'type':'result','result':text,'is_error':False}), flush=True)
"""
    )
    cli.chmod(0o755)
    record = provider_library.load_provider(
        Path(provider_library.__file__).parent / "library" / "claude-code.toml"
    )
    if explicit_line:
        record = replace(
            record, dialect=replace(record.dialect or Dialect(), interrupt_line=CONTROL)
        )
    session = ObservedSession(record, binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path)
    session.started = asyncio.Event()
    recorded: list[str] = []

    async def reasoning(text: str) -> None:
        recorded.append(text)

    async def activity(kind: str, text: str) -> None:
        recorded.append(text)

    monkeypatch.setattr(
        session_module,
        "current_run",
        lambda: SimpleNamespace(reasoning=reasoning, activity=activity),
    )
    active = asyncio.create_task(session.turn("first"))
    try:
        await session.started.wait()
        process = cast(asyncio.subprocess.Process, session._process)
        stdin = cast(asyncio.StreamWriter, process.stdin)
        original_drain = stdin.drain
        if finish_during_drain:

            async def drain() -> None:
                await active

            monkeypatch.setattr(stdin, "drain", drain)
        told = await session.interrupt()
        if finish_during_drain:
            assert session._interrupted is False
            monkeypatch.setattr(stdin, "drain", original_drain)
            recorded.clear()
        active.cancel()
        with suppress(asyncio.CancelledError):
            await active
        following = await session.turn("second")
        assert (told, following.text, session._process is process, recorded) == (
            True,
            "NEXT RESULT",
            True,
            [],
        )
    finally:
        active.cancel()
        with suppress(asyncio.CancelledError):
            await active
        await session.close()
