"""Actual CLI and MCP relay, deterministic local Responses server; no account or remote model."""

import asyncio
import json
import os
import shutil
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.adapters.jsonl.transport import JsonlProvider
from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.adapters.recording import SocketOffer
from shadow_hdk.kernel import Ceiling, Ended, Floor, Lease
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.providers import shipped
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.skipif(
    os.environ.get("SHADOW_HDK_TEST_CODEX") != "1",
    reason="opt-in local SDK proof: SHADOW_HDK_TEST_CODEX=1 (no account is used)",
)


@pytest.mark.parametrize("model", ["gpt-5.4", "gpt-6-astra", "gpt-6-sol"])
async def test_native_tools_and_repository_discovery_are_absent_and_read_uses_the_kit(
    tmp_path: Path,
    model: str,
) -> None:
    binary = shutil.which("codex")
    assert binary is not None, "this SDK gate requires Codex 0.154.0"
    captures: list[dict[str, Any]] = []
    failures: list[str] = []

    class Model(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            try:
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                captures.append(payload)
                number = len(captures)
                if number == 1:
                    flat = next(
                        (t for t in payload["tools"] if t.get("name", "").endswith("__read_file")),
                        None,
                    )
                    namespace = (
                        None
                        if flat
                        else next(
                            t
                            for t in payload["tools"]
                            if t["type"] == "namespace"
                            and any(f.get("name") == "read_file" for f in t["tools"])
                        )
                    )
                    name = (
                        flat["name"]
                        if flat
                        else next(
                            t["name"]
                            for t in (namespace or {})["tools"]
                            if t["name"] == "read_file"
                        )
                    )
                    item = {
                        "type": "function_call",
                        "id": "fc_1",
                        "call_id": "call_1",
                        "name": name,
                        **({"namespace": namespace["name"]} if namespace else {}),
                        "arguments": '{"path":"proof.txt"}',
                        "status": "completed",
                    }
                else:
                    item = {
                        "type": "message",
                        "id": "msg_1",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Read through the kit.",
                                "annotations": [],
                            }
                        ],
                    }
                response = {
                    "id": f"resp_{number}",
                    "object": "response",
                    "status": "completed",
                    "output": [item],
                    "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                }
                events: list[dict[str, Any]] = [
                    {
                        "type": "response.created",
                        "response": {**response, "status": "in_progress", "output": []},
                    },
                    {"type": "response.output_item.added", "output_index": 0, "item": item},
                    {"type": "response.output_item.done", "output_index": 0, "item": item},
                    {"type": "response.completed", "response": response},
                ]
                body = "".join(
                    f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as error:
                failures.append(
                    f"{type(error).__name__}: {error}; tools: "
                    + str(
                        [
                            (
                                t.get("type"),
                                t.get("name"),
                                [f.get("name") for f in t.get("tools", [])],
                            )
                            for t in captures[-1].get("tools", [])
                        ]
                    )
                )
                self.send_error(500)

    server = HTTPServer(("127.0.0.1", 0), Model)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    root = tmp_path / "repository"
    root.mkdir()
    (root / "proof.txt").write_text("HDK_AUDITED_FILE_TOKEN")
    (root / "AGENTS.md").write_text("HDK_UNAUDITED_DOCUMENT_SENTINEL")
    skill = root / ".agents/skills/unjudged"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: unjudged\ndescription: HDK_UNAUDITED_SKILL_SENTINEL\n---\nHidden procedure.\n"
    )
    home = tmp_path / "sdk-home"
    home.mkdir()
    codex = shipped()["codex"]
    config = [
        'model_provider="local_proof"',
        'model_providers.local_proof.name="HDK local proof"',
        f'model_providers.local_proof.base_url="http://127.0.0.1:{server.server_port}/v1"',
        'model_providers.local_proof.wire_api="responses"',
        "model_providers.local_proof.requires_openai_auth=false",
    ]
    provider = replace(
        codex, launch_args=(*codex.launch_args, *(arg for c in config for arg in ("-c", c)))
    )
    environment = await LocalEnvironment.open(root, mode="full")
    sink = ListSink()
    thread = None
    try:
        thread = await Thread.open(
            agent=JsonlProvider(
                provider, binary=Path(binary), env={**os.environ, "CODEX_HOME": str(home)}
            ),
            registry=SocketOffer(withhold={"turn"}),
            ports=Ports(
                components=(environment,), governance=AllowAll(), sink=sink, clock=FixedClock()
            ),
            store=InMemoryThreads(),
            root=root,
            lease=Lease(Ceiling(40, 90, None), Floor(0)),
            modes=ModeRegistry(
                (
                    ModeSpec.of(
                        "read", behaviour=Behaviour(model=model, tools_offered=("read_file",))
                    ),
                )
            ),
            mode="read",
        )
        async with asyncio.timeout(45):
            seen = [e async for e in thread.turn("Read proof.txt with read_file.")]
        assert not failures, (failures, getattr(thread.conversation._session, "stderr", ""))
        assert len(captures) == 2, thread.record.turns[-1].text
        names = {t["name"] for t in captures[0]["tools"]}
        assert names == {
            "mcp__shadow_hdk",
            "list_mcp_resources",
            "list_mcp_resource_templates",
            "read_mcp_resource",
            "request_user_input",
            "get_goal",
            "create_goal",
            "update_goal",
        }, names
        namespace = next(t for t in captures[0]["tools"] if t["type"] == "namespace")
        assert [t["name"] for t in namespace["tools"]] == ["read_file"]
        prompt = json.dumps(captures[0]["input"])
        assert (
            "HDK_UNAUDITED_DOCUMENT_SENTINEL" not in prompt
            and "HDK_UNAUDITED_SKILL_SENTINEL" not in prompt
        )
        assert "HDK_AUDITED_FILE_TOKEN" in json.dumps(captures[1]["input"])
        assert [(e.component, e.inputs) for e in seen if e.kind == "invoked"] == [
            ("turn", {"prompt": "Read proof.txt with read_file."}),
            ("read_file", {"path": "proof.txt"}),
        ]
        assert thread.record.turns[-1].outcome == "completed"
        async with asyncio.timeout(45):
            again = [e async for e in thread.turn("Keep using only the kit's tools.")]
        assert len(captures) == 3 and thread.record.turns[-1].outcome == "completed", (
            thread.record.turns[-1],
            getattr(thread.conversation._session, "stderr", ""),
        )
        assert {t["name"] for t in captures[2]["tools"]} == names
        assert isinstance(again[-1], Ended) and again[-1].reason == "completed"
    finally:
        if thread is not None:
            await thread.close()
        await environment.close()
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        worker.join(timeout=5)
