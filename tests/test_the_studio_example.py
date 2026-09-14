"""The studio is a page `shadow-hdk serve --http --page` serves, talking the wire and nothing
local (Phase 26 group 6, D69): `thread/start` once at load — `thread/resume` when a `?thread=` is
given — `turn/start` per message, `approvals/answer`, `thread/set_mode`, `modes/list`, `store/*`
for the admin panel, and `files/list` + `files/read` under the thread's root for the environment.

Driven here with a scripted provider over the real HTTP/SSE transport, so nothing costs a turn;
the page's JavaScript is exercised by a person, and every method it calls is exercised here.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import anyio
import httpx
import pytest

from shadow_hdk.kernel import ActRule, Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from shadow_hdk.serve import ServeHost
from shadow_hdk.serve.config import Settings
from shadow_hdk.wire import connect_to, protocol, served_over_http
from tests.serve.test_serve_answers_a_host_in_any_language import ENFORCEABLE

pytestmark = pytest.mark.anyio

PAGE = Path(__file__).resolve().parents[1] / "examples" / "studio" / "page.html"


class WritingProvider:
    """A provider that writes one file through the thread's own registry and answers — what a
    real CLI does through the offered socket."""

    def __init__(self) -> None:
        self.reach: Any = None
        self.opened = 0
        self.closed = 0

    async def open(self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None) -> Any:
        self.opened += 1
        provider = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                target = prompt if prompt.endswith(".txt") else "hello.txt"
                await provider.reach("write_file", {"path": target, "content": "hello"})
                return Turn(text="done: " + prompt)

            async def close(self) -> None:
                provider.closed += 1

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


class StudioHost(ServeHost):
    """`ServeHost` with the scripted provider reaching the thread's registry as the socket would."""

    def __init__(self, root: Path) -> None:
        self.writer = WritingProvider()
        super().__init__(Settings(root=root, mode=ENFORCEABLE), agent=cast(Any, self.writer))
        # Where the machine can only open `full`, that mode asks before a write (D65) and nobody
        # here answers — measured as a hang on CI. The person's rule pre-approves the one write.
        self.rules.add(ActRule(component="write_file"))

    async def open(self, **kw: Any) -> Any:
        thread = await super().open(**kw)
        self.writer.reach = thread.registry.call
        return thread

    async def resume(self, thread_id: str, **kw: Any) -> Any:
        thread = await super().resume(thread_id, **kw)
        self.writer.reach = thread.registry.call
        return thread


def _ports() -> Ports:
    from shadow_hdk.adapters.basic import AllowAll

    return Ports(
        model=ScriptedModel([]),
        components=(),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_the_page_is_served_by_serve_itself(tmp_path: Path) -> None:
    host = StudioHost(tmp_path)
    with anyio.fail_after(60):
        async with served_over_http(threads=host, page=PAGE) as address:
            async with httpx.AsyncClient() as web:
                page = await web.get(address + "/")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"]
    assert "thread/start" in page.text and "turn/start" in page.text


def test_the_page_speaks_only_what_the_wire_serves() -> None:
    """Every method the page calls is a name `protocol.py` publishes: the page's vocabulary is the
    wire's, so a client in another language could be this page."""
    text = PAGE.read_text(encoding="utf-8")
    called = set(re.findall(r"""call\(\s*['"]([a-z_]+/[a-z_]+)['"]""", text))
    heard = set(re.findall(r"""hear\(\s*['"]([a-z_]+)['"]""", text))
    published = {v for k, v in vars(protocol).items() if k.isupper() and isinstance(v, str)}
    assert called, "the page calls the wire by method"
    assert called <= published, sorted(called - published)
    assert heard <= published, sorted(heard - published)
    assert {
        "thread/start",
        "thread/resume",
        "turn/start",
        "approvals/answer",
        "thread/set_mode",
        "modes/list",
        "store/put",
        "rules/list",
        "files/list",
        "files/read",
        "tools/list",
        "skills/list",
    } <= called
    assert {
        "event",
        "item",
        "activity",
        "approval_request",
        "input_request",
        "request_withdrawn",
    } <= heard
    assert "fetch('/say" not in text and "EventSource('/stream" not in text, "nothing local"


async def test_a_turn_over_the_wire_writes_a_file_the_environment_pane_reads(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    host = StudioHost(root)
    (root / ".hidden").write_text("no", encoding="utf-8")
    # A file that exists, one level up: what a traversal would reach if it were allowed to.
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    items: list[dict[str, Any]] = []
    with anyio.fail_after(60):
        async with served_over_http(threads=host, page=PAGE) as address:
            async with connect_to(address, _ports()) as client:
                await client.initialize()

                async def keep(params: dict[str, Any]) -> None:
                    items.append(params["item"])

                client.peer.hears("item", keep)
                started = await client.peer.call(
                    "thread/start", {"root": str(root), "mode": ENFORCEABLE}
                )
                tid = started["thread_id"]
                assert started["root"] == str(root), "the page shows the root it was given"
                before = await client.peer.call("files/list", {"thread_id": tid})
                assert before["files"] == [], "dotfiles are not the workspace"
                done = await client.peer.call("turn/start", {"thread_id": tid, "text": "hello"})
                listed = await client.peer.call("files/list", {"thread_id": tid})
                read = await client.peer.call("files/read", {"thread_id": tid, "path": "hello.txt"})
                for outside in ("../outside.txt", str(tmp_path / "outside.txt")):
                    with pytest.raises(Exception, match="not in the workspace"):
                        await client.peer.call("files/read", {"thread_id": tid, "path": outside})
                with pytest.raises(Exception, match="not in the workspace"):
                    await client.peer.call("files/read", {"thread_id": tid, "path": ".hidden"})
    assert done["turn"]["text"] == "done: hello" and done["turn"]["outcome"] == "completed"
    assert [f["path"] for f in listed["files"]] == ["hello.txt"]
    assert listed["files"][0]["bytes"] == 5 and listed["files"][0]["mtime"] > 0
    assert read["content"] == "hello"
    assert any(i.get("component") == "write_file" for i in items), "the tool call is an item"


async def test_a_reload_resumes_the_thread_and_reads_its_turns(tmp_path: Path) -> None:
    """The page keeps `?thread=<id>`; a reload is a new session that resumes the same thread."""
    host = StudioHost(tmp_path)
    with anyio.fail_after(60):
        async with served_over_http(threads=host, page=PAGE) as address:
            async with connect_to(address, _ports()) as first:
                await first.initialize()
                started = await first.peer.call(
                    "thread/start", {"root": str(tmp_path), "mode": ENFORCEABLE}
                )
                tid = started["thread_id"]
                await first.peer.call("turn/start", {"thread_id": tid, "text": "one"})
            # The first session's stream is gone, and the session keeps its thread for a grace
            # (D94) — a page on a train reattaches. A reload is a new session: resuming the
            # thread takes it over, and the old session's provider is closed then.
            assert host.writer.closed == 0
            async with connect_to(address, _ports()) as second:
                await second.initialize()
                resumed = await second.peer.call("thread/resume", {"thread_id": tid})
                assert host.writer.closed == 1, "taken over: the old session's provider closed"
                assert [t["prompt"] for t in resumed["turns"]] == ["one"]
                assert resumed["root"] == str(tmp_path)
                done = await second.peer.call("turn/start", {"thread_id": tid, "text": "two"})
    assert done["turn"]["text"] == "done: two"
    assert host.writer.opened == 2


def test_the_studio_runs_serve_with_its_page() -> None:
    """`python -m examples.studio ws --mode=read-only --store=x.sqlite --port=1` is
    `shadow-hdk serve --http` with the page and the flags — nothing of its own."""
    from examples.studio.__main__ import serve_arguments

    assert serve_arguments(["ws", "--mode=read-only", "--store=x.sqlite", "--port=1"]) == [
        "serve",
        "--http",
        "--port=1",
        f"--page={PAGE}",
        "--root=ws",
        "--mode=read-only",
        "--store=x.sqlite",
    ]
    assert serve_arguments([])[:4] == ["serve", "--http", "--port=8765", f"--page={PAGE}"]
    assert "--root=./studio-workspace" in serve_arguments([])


def test_serve_takes_the_settings_from_flags_as_well_as_a_toml(tmp_path: Path) -> None:
    from shadow_hdk.serve.__main__ import settings_from

    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "work"\nmode = "read-only"\n', encoding="utf-8"
    )
    from_toml = settings_from([str(tmp_path / "harness.toml"), "--http"])
    assert from_toml.root == (tmp_path / "work").resolve() and from_toml.mode == "read-only"
    overridden = settings_from(
        [
            str(tmp_path / "harness.toml"),
            "--mode=full",
            f"--store={tmp_path / 's.sqlite'}",
            "--provider=codex",
            f"--root={tmp_path / 'other'}",
        ]
    )
    assert overridden.mode == "full" and overridden.want == "codex"
    assert overridden.store == f"sqlite:///{tmp_path / 's.sqlite'}"
    assert overridden.root == (tmp_path / "other").resolve()
    bare = settings_from(["--http", f"--root={tmp_path}"])
    assert bare.root == tmp_path.resolve() and bare.mode == "workspace-write"
    # `--flag value` is the form every CLI takes as well as `--flag=value`; the README uses it.
    spaced = settings_from(["--http", "--root", str(tmp_path), "--mode", "full", "--port", "1"])
    assert spaced.root == tmp_path.resolve() and spaced.mode == "full"
