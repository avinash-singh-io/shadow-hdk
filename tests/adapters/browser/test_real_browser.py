"""Real local application controls, using disposable profiles and local HTTP/TLS servers."""

from __future__ import annotations

import asyncio
import base64
import datetime
import os
import ssl
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.browser import (
    AgentBrowserEngine,
    BrowserComponents,
    OriginPolicy,
    PlaywrightEngine,
)
from shadow_hdk.kernel import Completed, Failed, Image, ModelResponse, Refused

pytestmark = [pytest.mark.anyio, pytest.mark.browser, pytest.mark.timeout(180)]


@pytest.fixture(
    autouse=True, params=(PlaywrightEngine, AgentBrowserEngine), ids=("playwright", "agent-browser")
)
def interaction_engine(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "PlaywrightEngine", request.param)


class AppServer(ThreadingHTTPServer):
    def __init__(self, handler: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(("127.0.0.1", 0), handler)
        self.hits: list[str] = []
        self.accepted = 0
        self.denied_url = ""
        self.redirect_url = ""
        self.next_redirect = ""
        self.scheme = "http"
        self.stun_port = 0

    @property
    def origin(self) -> str:
        return f"{self.scheme}://127.0.0.1:{self.server_port}"

    def get_request(self) -> Any:
        connection = super().get_request()
        self.accepted += 1
        return connection


class App(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        server = cast(AppServer, self.server)
        server.hits.append(self.path)
        if self.path.startswith("/chain"):
            self.send_response(302)
            self.send_header("Location", server.next_redirect)
            self.end_headers()
            return
        if self.path == "/bad":
            self.send_response(503)
            self.end_headers()
            return
        if self.headers.get("Upgrade") == "websocket":
            import hashlib

            accept = base64.b64encode(
                hashlib.sha1(
                    (
                        self.headers["Sec-WebSocket-Key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                    ).encode()
                ).digest()
            ).decode()
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/javascript" if self.path == "/worker.js" else "text/html"
        )
        if self.path == "/cookie/set":
            self.send_header("Set-Cookie", "private=owner-a; SameSite=Lax")
        self.end_headers()
        if self.path == "/worker.js":
            self.wfile.write(f"fetch('{server.denied_url}/worker-fetch').catch(()=>0);".encode())
            return
        if self.path.startswith("/cookie"):
            self.wfile.write(f"<h1>{self.headers.get('Cookie', 'anonymous')}</h1>".encode())
            return
        if self.path == "/next":
            self.wfile.write(b"<h1>Next page</h1>")
            return
        if self.path == "/rtc":
            self.wfile.write(
                f"""<p id="done">Gathering</p><script>
            (async()=>{{const peer=new RTCPeerConnection({{iceServers:[
                {{urls:'stun:127.0.0.1:{server.stun_port}'}}]}});
                peer.createDataChannel('probe');
                await peer.setLocalDescription(await peer.createOffer());
                await new Promise(resolve=>setTimeout(resolve,1800));
                peer.close();document.querySelector('#done').textContent='Finished';
            }})();</script>""".encode()
            )
            return
        if self.path == "/network-boundary":
            self.wfile.write(
                f"""<p id="done">Waiting</p><script>
            fetch('{server.denied_url}/boundary').finally(()=>
                document.querySelector('#done').textContent='Finished');</script>""".encode()
            )
            return
        socket_url = server.origin.replace("http", "ws", 1)
        denied_socket = server.denied_url.replace("http", "ws", 1)
        self.wfile.write(
            f"""<!doctype html><title>Workbench app</title>
          <h1 id="heading">Untitled</h1><label>Title<input id="title"></label>
          <button onclick="document.querySelector('#heading').textContent=
           document.querySelector('#title').value">Save</button>
          <select aria-label="Language"
           onchange="document.querySelector('#status').textContent=this.value">
           <option value="js">JavaScript</option><option value="py">Python</option></select>
          <p id="status" role="status">js</p><a href="/next">Next</a>
          <div style="height:1800px"></div><p>Bottom of the application</p>
          <script>console.log('workbench ready');fetch('/bad');
           new WebSocket('{socket_url}/socket').onopen=()=>console.log('socket ready');
           fetch('{server.denied_url}/fetch').catch(()=>0);
           new WebSocket('{denied_socket}/socket');new Worker('/worker.js');
          </script><img src="{server.denied_url}/pixel">""".encode()
        )


@pytest.fixture
def apps(tmp_path: Path) -> Iterator[tuple[AppServer, AppServer, AppServer, AppServer, Path]]:
    if os.environ.get("SHADOW_HDK_BROWSER_TESTS") != "1":
        pytest.skip("opt in to real browser controls with SHADOW_HDK_BROWSER_TESTS=1")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    ca, private = tmp_path / "ca.pem", tmp_path / "key.pem"
    ca.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    servers = [AppServer(App) for _ in range(4)]
    first, second, denied_http, denied_tls = servers
    for server in (second, denied_tls):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(ca, private)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.scheme = "https"
    first.denied_url = denied_http.origin
    second.denied_url = denied_tls.origin
    first.next_redirect = second.origin + "/chain"
    second.next_redirect = denied_tls.origin + "/exfil"
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield first, second, denied_http, denied_tls, ca
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


def engine_for(apps: Any) -> PlaywrightEngine:
    first, second, _, denied_tls, ca = apps
    # Approve HTTP on the denied TLS authority to prove the gateway enforces scheme too.
    policy = OriginPolicy(
        (first.origin, second.origin, denied_tls.origin.replace("https:", "http:")),
        allow_localhost=False,
    )
    return PlaywrightEngine(
        policy=policy,
        install_browser=False,
        upstream_ca=ca,
        gateway_python=os.environ.get("SHADOW_HDK_BROWSER_GATEWAY_PYTHON"),
    )


async def completed(
    engine: PlaywrightEngine, action: str, inputs: Any, scope: str = "app"
) -> Completed:
    result = await engine.execute(action, inputs, scope)
    assert isinstance(result, Completed), result
    return result


async def test_edit_navigate_debug_and_take_real_images(apps: Any) -> None:
    first, *_ = apps
    engine = engine_for(apps)
    try:
        opened = await completed(engine, "open", {"url": first.origin})
        assert cast(dict[str, Any], opened.output).get("status") == 200
        tab = cast(dict[str, Any], opened.output)["tab"]
        await completed(engine, "type", {"role": "textbox", "name": "Title", "value": "Scoped app"})
        await completed(engine, "press", {"role": "button", "name": "Save", "key": "Enter"})
        await completed(
            engine, "select", {"role": "combobox", "name": "Language", "values": ["py"]}
        )
        await completed(engine, "wait", {"role": "heading", "name": "Scoped app"})
        snapshot = await completed(engine, "snapshot", {})
        assert "Scoped app" in str(snapshot.output) and "py" in str(snapshot.output)
        found = await completed(engine, "find", {"role": "button", "name": "Save"})
        assert cast(dict[str, Any], found.output)["count"] == 1
        before = await completed(engine, "screenshot", {})
        assert base64.b64decode(before.images[0].data).startswith(b"\x89PNG\r\n\x1a\n")
        await completed(engine, "scroll", {"y": 1600})
        after = await completed(engine, "screenshot", {})
        assert after.images != before.images, "scroll must change the rendered viewport"
        await completed(engine, "click", {"role": "link", "name": "Next"})
        assert "Next page" in str((await completed(engine, "snapshot", {})).output)
        await completed(engine, "back", {})
        assert "Save" in str((await completed(engine, "snapshot", {})).output)
        await completed(engine, "forward", {})
        assert "Next page" in str((await completed(engine, "snapshot", {})).output)
        await completed(engine, "new_tab", {"url": first.origin})
        tabs = await completed(engine, "tabs", {})
        assert len(cast(dict[str, Any], tabs.output)["tabs"]) == 2
        selected = await completed(engine, "console", {"tab": tab})
        assert all(
            entry["tab"] == tab for entry in cast(dict[str, Any], selected.output)["entries"]
        )
        closing = engine._profiles["app"].tabs[cast(dict[str, Any], tabs.output)["active"]]
        await completed(engine, "close_tab", {})
        assert closing.is_closed(), "close_tab must close the underlying page"
        assert (
            cast(dict[str, Any], await_out := (await completed(engine, "tabs", {})).output)[
                "active"
            ]
            == tab
        ), await_out
        assert len(cast(dict[str, Any], await_out)["tabs"]) == 1
        console = await completed(engine, "console", {})
        errors = await completed(engine, "requests", {})
        assert "workbench ready" in str(console.output) and "socket ready" in str(console.output)
        assert "/bad" in str(errors.output) and "503" in str(errors.output)
        profile = engine._profiles["app"]
        directory = Path(profile.directory.name)
        browser, gateway = profile.browser, profile.gateway
    finally:
        await engine.release_run("app")
    assert gateway is not None
    try:
        assert (directory.exists(), browser.is_connected(), gateway.process.returncode is None) == (
            False,
            False,
            False,
        )
    finally:
        # Also settle a deliberately broken lifecycle during mutation verification.
        await profile.close()
    assert isinstance(await engine.execute("open", {"url": first.origin}, "app"), Refused)


async def test_navigation_reports_http_failures_and_preserves_upstream_tls_verification(
    apps: Any,
) -> None:
    first, second, *_ = apps
    engine = PlaywrightEngine(
        policy=OriginPolicy((first.origin, second.origin), allow_localhost=False),
        install_browser=False,
    )
    try:
        bad = await completed(engine, "open", {"url": first.origin + "/bad"})
        assert cast(dict[str, Any], bad.output).get("status") == 503
        tls = await completed(engine, "open", {"url": second.origin})
        assert cast(dict[str, Any], tls.output).get("status") == 502
        assert second.hits == [], "an untrusted upstream certificate must not be accepted"
        assert "502" in str((await completed(engine, "requests", {})).output)
    finally:
        await engine.release_run("app")


async def test_page_webrtc_does_not_contact_an_unapproved_udp_server(apps: Any) -> None:
    from playwright.async_api import async_playwright

    first, *_ = apps
    packets: list[bytes] = []

    class Stun(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, address: Any) -> None:
            packets.append(data)

    transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
        Stun, local_addr=("127.0.0.1", 0)
    )
    first.stun_port = transport.get_extra_info("sockname")[1]
    engine = engine_for(apps)
    try:
        # An unconstrained Chromium really sends UDP to this probe. An empty capture alone
        # would otherwise prove neither the fixture nor the engine's network boundary.
        async with async_playwright() as driver:
            control = await driver.chromium.launch(headless=True)
            try:
                page = await control.new_page()
                await page.goto(first.origin + "/rtc")
                await page.get_by_text("Finished", exact=True).wait_for()
                assert packets, "the positive STUN control must contact the probe"
            finally:
                await control.close()
        packets.clear()
        await completed(engine, "open", {"url": first.origin + "/rtc"})
        await completed(engine, "wait", {"selector": "#done:text-is('Finished')"})
        assert packets == [], "a page must not bypass the host's origin gateway using WebRTC"
    finally:
        await engine.release_run("app")
        transport.close()


async def test_http_subresource_denial_precedes_a_connection(apps: Any) -> None:
    first, _, denied, *_ = apps
    engine = engine_for(apps)
    try:
        await completed(engine, "open", {"url": first.origin + "/network-boundary"})
        await completed(engine, "wait", {"selector": "#done:text-is('Finished')"})
        assert (denied.hits, denied.accepted) == ([], 0)
    finally:
        await engine.release_run("app")


async def test_first_use_installs_a_missing_binary_and_reports_progress(
    apps: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.environ.get("SHADOW_HDK_BROWSER_INSTALL_TESTS") != "1":
        pytest.skip("opt in to a real first-use download with SHADOW_HDK_BROWSER_INSTALL_TESTS=1")
    from shadow_hdk.adapters.browser import engine as implementation

    first, *_ = apps
    activities: list[tuple[str, str]] = []

    class Context:
        async def activity(self, kind: str, text: str) -> None:
            activities.append((kind, text))

    monkeypatch.setattr(implementation, "current_run", Context)
    binaries = tmp_path / "first-use-binaries"
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(binaries))
    engine = PlaywrightEngine(policy=OriginPolicy((first.origin,), allow_localhost=False))
    try:
        assert not binaries.exists(), "construction must not install a binary"
        await completed(engine, "open", {"url": first.origin})
        assert ("install", "Installing Chromium for the optional browser component.") in activities
        assert list(binaries.glob("chromium-*")), (
            "the first operation must install its missing engine"
        )
        assert "Untitled" in str((await completed(engine, "snapshot", {})).output)
    finally:
        await engine.release_run("app")


async def test_redirects_subresources_workers_and_websockets_cannot_reach_denied_origins(
    apps: Any,
) -> None:
    first, second, denied_http, denied_tls, _ = apps
    engine = engine_for(apps)
    try:
        await completed(engine, "open", {"url": first.origin})
        await completed(engine, "wait", {"selector": "h1"})
        await completed(engine, "open", {"url": second.origin})
        await completed(engine, "wait", {"selector": "h1"})
        chain = await engine.execute("open", {"url": first.origin + "/chain"}, "app")
        assert isinstance(chain, Failed) and "blocked" in chain.error, chain
        # Image/script requests are asynchronous; a second allowed navigation is a load barrier.
        await completed(engine, "open", {"url": second.origin + "/next"})
        assert (denied_http.hits, denied_tls.hits, denied_http.accepted, denied_tls.accepted) == (
            [],
            [],
            0,
            0,
        )
        assert "/socket" in first.hits, "an allowed socket must work, not just denied ones"
        assert "/worker.js" in first.hits and "/worker.js" in second.hits
    finally:
        await engine.release_run("app")


async def test_overlapping_runs_have_isolated_cookies_and_close_independently(apps: Any) -> None:
    first, *_ = apps
    engine = engine_for(apps)
    try:
        await completed(engine, "open", {"url": first.origin + "/cookie/set"}, "a")
        await completed(engine, "open", {"url": first.origin + "/cookie"}, "b")
        assert "anonymous" in str((await completed(engine, "snapshot", {}, "b")).output)
        await completed(engine, "open", {"url": first.origin + "/cookie"}, "a")
        assert "private=owner-a" in str((await completed(engine, "snapshot", {}, "a")).output)
        await engine.release_run("a")
        assert "anonymous" in str((await completed(engine, "snapshot", {}, "b")).output)
    finally:
        await engine.release_run("a")
        await engine.release_run("b")


async def test_a_real_screenshot_reaches_the_model_and_closes_with_its_thread(
    apps: Any, tmp_path: Path
) -> None:
    from shadow_hdk.adapters.agent import ModelAgent, single
    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.kernel.ports import ToolCall
    from shadow_hdk.runtime import InMemoryEffectJournal, Ports
    from shadow_hdk.runtime.testing import (
        AllowAuthorizer,
        FixedAuthority,
        FixedClock,
        ListSink,
        ScriptedModel,
    )
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread
    from tests.runtime.test_a_conversation_without_a_record import _lease

    first, *_ = apps
    engine = engine_for(apps)
    model = ScriptedModel(
        [
            ModelResponse(tool_calls=(ToolCall("open", "browser_open", {"url": first.origin}),)),
            ModelResponse(tool_calls=(ToolCall("image", "browser_screenshot", {}),)),
            ModelResponse(
                tool_calls=(ToolCall("done", "done", {"summary": "Rendered app checked"}),)
            ),
            ModelResponse(tool_calls=(ToolCall("second-image", "browser_screenshot", {}),)),
            ModelResponse(tool_calls=(ToolCall("done-again", "done", {"summary": "Same tab"}),)),
        ]
    )
    thread = await Thread.open(
        agent=ModelAgent(model=model, pattern=single),
        ports=Ports(
            model=model,
            components=(BrowserComponents(engine=engine),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
            authority=FixedAuthority(),
            authorizer=AllowAuthorizer(),
            effect_journal=InMemoryEffectJournal(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
    )
    try:
        [e async for e in thread.turn("Check the rendered app")]
        images = [image for message in model.requests[-1].messages for image in message.images]
        assert len(images) == 1 and isinstance(images[0], Image)
        assert len(base64.b64decode(images[0].data)) > 1000
        assert images[0].data not in "".join(m.content for m in model.requests[-1].messages)
        assert thread.id in engine._profiles, "the profile belongs to the conversation"
        [e async for e in thread.turn("Check the same tab again")]
        images_again = [
            image for message in model.requests[-1].messages for image in message.images
        ]
        assert len(images_again) == 2 and len(engine._profiles[thread.id].tabs) == 1
    finally:
        await thread.close()
    assert engine._profiles == {}
