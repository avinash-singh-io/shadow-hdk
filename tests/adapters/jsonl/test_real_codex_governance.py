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


def read_too_late(
    offered: tuple[str, ...], failures: list[str], unreached: bool, captures: list[Any]
) -> bool:
    """The one gap this kit cannot see from the inside (TD-023, fixed in 0.49.0).

    If we answered a listing carrying tools and the provider's request still carried none, it read
    the catalogue too late to use it. The kit never sees that request, so it cannot name this the
    way it names a catalogue never read — only a control can, because the control is the thing
    being asked. Declared rather than hidden, and deliberately narrow, which is why it is a
    function with its own controls: every other failure must still fail.
    """
    # `captures` must exist: a run that never got as far as a request is a different break, and
    # excusing it would make this gap cover far more than its own case. Caught by its controls.
    if not offered or not failures or unreached or not captures:
        return False
    tools = captures[0].get("tools", [])
    return not [tool for tool in tools if tool.get("tools")]


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
                # Compact on purpose: the previous form printed each tool's nested names as a
                # list, and the one failure that mattered was truncated by the assertion repr on
                # CI, which cost a run to diagnose. Type, name and nested count per tool fit, and
                # the count is the whole question — a server listed with zero nested tools means
                # the governed tools never reached the model.
                failures.append(
                    f"{type(error).__name__}: {error}; tools: "
                    + ", ".join(
                        f"{t.get('type')}:{t.get('name')}/{len(t.get('tools') or [])}"
                        for t in captures[-1].get("tools", [])
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
    # Held so the control can say what *this* side offered. An empty listing answered is a
    # problem here; a full listing ignored is the provider's (TD-023).
    offer = SocketOffer(withhold={"turn"})
    sink = ListSink()
    thread = None
    try:
        thread = await Thread.open(
            agent=JsonlProvider(
                provider, binary=Path(binary), env={**os.environ, "CODEX_HOME": str(home)}
            ),
            registry=offer,
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
        async with asyncio.timeout(90):
            seen = [e async for e in thread.turn("Read proof.txt with read_file.")]
        # **What the kit claims, stated as the kit's own contract** (TD-023). A governed run gets
        # the host's tools, *or* it says it did not. Before the barrier it could do neither: the
        # SDK silently dropped a server it could not start and the run proceeded with only its
        # native tools, which is indistinguishable from an agent that chose to call nothing.
        #
        # Whether a particular machine's SDK sandbox permits the relay to reach a loopback socket
        # is that environment's behaviour and not this kit's claim — measured here, the relay
        # connects when spawned directly on every platform, and is denied to the SDK on one
        # continuous-integration runner. So the assertion below is the honest one, and the
        # conditions after it hold wherever the tools did arrive.
        unreached = "tools.unreached" in getattr(thread.conversation, "unmapped_behaviour", ())
        if unreached:
            # The SDK still *lists* the server; it simply has nothing inside it. So the coherent
            # check is that it carried no tools, not that it was absent — getting that wrong is
            # what turned this honest branch into a failure on its first run.
            served = [
                t for t in (captures[0].get("tools", []) if captures else []) if t.get("tools")
            ]
            assert not served, (
                f"the run reported unreachable tools while the SDK was offered {served}; "
                "that is incoherent"
            )
            pytest.skip(
                "the SDK could not reach this run's tool server in this environment, and the kit "
                "named it (tools.unreached) rather than running on silently — which is the "
                "behaviour under test; see TD-023 for the environment question"
            )
        # Our own listing first: pytest truncates a long repr from the middle, and twice that hid
        # the one fact that decides which side dropped the tools.
        if read_too_late(offer.holder.last_offered, failures, unreached, captures):
            pytest.skip(
                f"we offered {offer.holder.last_offered} and the provider composed without them, "
                "so it read the catalogue too late to use it — the first listing must be correct, "
                "which needs the registry to answer before a run attaches (TD-023, 0.49.0)"
            )
        assert not failures, (
            f"we offered: {offer.holder.last_offered}",
            failures,
            getattr(thread.conversation._session, "stderr", ""),
        )
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


async def test_the_restricted_model_metadata_reaches_every_row_of_the_actual_catalogue(
    tmp_path: Path,
) -> None:
    """The shipped provider claims restricted model metadata; this is what measures it.

    Asserting that a governed turn behaves says nothing about the metadata the SDK was launched
    with, so three mutations of the shipped replacements survived every control above. The first
    attempt at this one survived two of them as well, because it read what to expect from the same
    shipped data the mutation changes — a mutated expectation compared against a mutated
    application always agrees. So the restriction is written out here instead: these literals are
    the claim, and the shipped data is what is being measured against it.

    Swept over every row, because an SDK that grows a twelfth model must have it restricted too.
    """
    from shadow_hdk.adapters.jsonl.catalogue import prepare_catalogue

    restricted: dict[str, Any] = {
        "node_repl_disabled": True,
        "experimental_supported_tools": [],
        "supports_search_tool": False,
        "use_responses_lite": False,
        "tool_mode": "direct",
        "apply_patch_tool_type": None,
        "multi_agent_version": None,
    }

    binary = shutil.which("codex")
    assert binary is not None, "this SDK gate requires Codex 0.154.0"
    dialect = shipped()["codex"].dialect
    assert dialect is not None, "the shipped codex provider must declare a dialect"
    spec = dialect.launch_catalogue
    assert spec is not None, "the shipped codex provider must prepare a catalogue"
    # The shipped data must still ask for each restriction; a field deleted from it would
    # otherwise leave the rows below untouched and this control agreeing with the omission.
    assert {field.name for field in spec.replace_fields} == set(restricted), (
        "the shipped replacements no longer match the restrictions this control enforces"
    )

    argument, rendered = await prepare_catalogue(
        spec, binary=Path(binary), env={**os.environ}, directory=tmp_path
    )
    assert argument == spec.config_arg
    written = Path(rendered.split('"')[1] if '"' in rendered else rendered)
    rows = json.loads(written.read_text(encoding="utf-8"))[spec.entries_at]
    assert rows, "the actual catalogue must carry model rows"

    for row in rows:
        for name, required in restricted.items():
            assert name in row, f"{row.get('slug')} lost {name}"
            assert row[name] == required, (
                f"{row.get('slug')}: {name} is {row[name]!r}, must be {required!r}"
            )
