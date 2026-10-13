"""Agent-browser interactions and refs in a host-owned Playwright browser context.

The SDK supplies accessibility observations, reference identity and native interactions.
HDK owns the managed profile, origin gateway, per-tab audit metadata and teardown.
It attaches only to the local browser HDK just created, never a discovered browser.
"""

from __future__ import annotations

import asyncio
import base64
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue

from shadow_hdk.adapters.browser.agent_client import AgentClient
from shadow_hdk.adapters.browser.arguments import Inputs
from shadow_hdk.adapters.browser.engine import PlaywrightEngine, _Profile
from shadow_hdk.adapters.browser.gateway import Gateway
from shadow_hdk.kernel import Completed, Failed, Image, Observation, Refused


@dataclass
class _ManagedProfile(_Profile):
    targets: dict[str, str] = field(default_factory=dict)
    statuses: dict[str, int] = field(default_factory=dict)

    def add_page(self, page: Any) -> str:
        identity = super().add_page(page)

        def record(response: Any) -> None:
            if response.request.is_navigation_request() and response.frame == page.main_frame:
                self.statuses[identity] = response.status

        page.on("response", record)
        return identity


class AgentBrowserEngine(PlaywrightEngine):
    """Pinned local interaction SDK; no cloud provider, user config, plugins or WebMCP."""

    licence = "Apache-2.0 (agent-browser/Playwright); MIT (mitmproxy); MIT/Apache-2.0 (uv)"

    async def _create(self) -> _ManagedProfile:
        from playwright.async_api import async_playwright

        profile = _ManagedProfile(tempfile.TemporaryDirectory(prefix="hdk-browser-", dir="/tmp"))
        try:
            profile.driver = await async_playwright().start()
            binary = Path(profile.driver.chromium.executable_path)
            if not binary.exists():
                if not self._install_browser:
                    raise RuntimeError("Chromium is missing; install the optional browser binary.")
                async with self._installing:
                    if not binary.exists():
                        await self._install()
            directory = Path(profile.directory.name)
            profile.gateway = await Gateway.start(
                directory,
                self.policy,
                sdk_python=self._gateway_python,
                upstream_ca=self._upstream_ca,
            )
            profile.context = await profile.driver.chromium.launch_persistent_context(
                directory / "chrome",
                executable_path=str(binary),
                headless=self._headless,
                proxy={"server": f"http://127.0.0.1:{profile.gateway.port}"},
                args=[
                    "--remote-debugging-port=0",
                    "--remote-debugging-address=127.0.0.1",
                    "--proxy-bypass-list=<-loopback>",
                    f"--ignore-certificate-errors-spki-list={profile.gateway.spki}",
                    "--disable-quic",
                    "--dns-prefetch-disable",
                    "--disable-background-networking",
                    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                ],
                service_workers="block",
                accept_downloads=False,
                viewport={"width": 1280, "height": 720},
            )
            profile.browser = profile.context.browser
            profile.context.on("page", profile.add_page)
            for page in profile.context.pages:
                profile.add_page(page)
            port, _ = (directory / "chrome/DevToolsActivePort").read_text().splitlines()
            profile.agent = await AgentClient.start(directory, f"http://127.0.0.1:{int(port)}")
            return profile
        except BaseException:
            await profile.close()
            raise

    async def _target(self, client: AgentClient, params: Inputs) -> str:
        if params.ref:
            snapshot = await client.call("snapshot")
            if params.ref.removeprefix("@") not in snapshot.get("refs", {}):
                raise ValueError("element reference is stale; take a fresh snapshot")
            return params.ref
        if params.role:
            snapshot = await client.call("snapshot")
            matches = [
                "@" + ref
                for ref, node in snapshot.get("refs", {}).items()
                if node.get("role") == params.role
                and (params.name is None or node.get("name") == params.name)
            ]
            if params.nth is not None:
                if params.nth >= len(matches):
                    raise ValueError("no element at the requested index")
                return str(matches[params.nth])
            if len(matches) != 1:
                raise ValueError(
                    f"query matched {len(matches)} elements; choose an explicit nth index"
                )
            return str(matches[0])
        assert params.selector is not None
        count = (await client.call("count", selector=params.selector))["count"]
        if count > 1:
            raise ValueError(f"selector matched {count} elements; choose an explicit nth index")
        return params.selector

    async def _action(self, profile: _Profile, action: str, params: Inputs) -> Observation:
        assert isinstance(profile, _ManagedProfile) and profile.agent is not None
        client: AgentClient = profile.agent
        client.timeout_ms = params.timeout_ms
        if action in ("tabs", "console", "requests", "close_tab"):
            # Ownership metadata and tab-correlated logs stay with HDK: the SDK's logs
            # currently omit tab ids. This also keeps every tab in the managed context.
            return await super()._action(profile, action, params)
        identity = params.tab or profile.active
        page = profile.tabs.get(identity)
        if action == "new_tab":
            page = await profile.context.new_page()
            identity = profile.add_page(page)
        if page is None or page.is_closed():
            return Refused("unknown or closed browser tab")
        if identity not in profile.targets:
            session = await profile.context.new_cdp_session(page)
            try:
                profile.targets[identity] = (await session.send("Target.getTargetInfo"))[
                    "targetInfo"
                ]["targetId"]
            finally:
                await session.detach()
        await client.call("tab_switch", tabId=profile.targets[identity])
        profile.active = identity
        if action in ("open", "new_tab"):
            profile.statuses.pop(identity, None)
            await client.call("navigate", url=params.url, waitUntil="domcontentloaded")
        elif action in ("back", "forward"):
            profile.statuses.pop(identity, None)
            await client.call(action)
        elif action == "snapshot":
            result = await client.call("snapshot")
            text = str(result["snapshot"])
            refs = {"@" + ref: node for ref, node in result.get("refs", {}).items()}
            return Completed(
                {
                    "tab": identity,
                    "url": page.url,
                    "snapshot": text[:200000],
                    "refs": dict(list(refs.items())[:5000]),
                    "truncated": len(text) > 200000 or len(refs) > 5000,
                }
            )
        elif action == "find":
            if params.role:
                snapshot = await client.call("snapshot")
                nodes = [
                    {"ref": "@" + ref, "snapshot": str(node)}
                    for ref, node in snapshot.get("refs", {}).items()
                    if node.get("role") == params.role
                    and (params.name is None or node.get("name") == params.name)
                ]
            else:
                result = await client.call("find", selector=params.selector)
                nodes = [
                    {"nth": index, "snapshot": str(node.get("text", ""))[:10000]}
                    for index, node in enumerate(result["elements"])
                ]
            return Completed(
                {
                    "tab": identity,
                    "count": len(nodes),
                    "matches": cast(JsonValue, nodes[:20]),
                    "truncated": len(nodes) > 20,
                }
            )
        elif action == "screenshot":
            if params.full_page:
                size = await page.evaluate(
                    "({width:document.documentElement.scrollWidth,"
                    "height:document.documentElement.scrollHeight})"
                )
                if size["width"] * size["height"] > 20_000_000:
                    return Refused("full-page image is too large; take a viewport screenshot")
            path = Path(profile.directory.name) / "screenshot.png"
            try:
                await client.call("screenshot", path=str(path), fullPage=params.full_page)
                if path.stat().st_size > 10_000_000:
                    return Refused("image is too large for a model observation")
                png = path.read_bytes()
            finally:
                path.unlink(missing_ok=True)
            if not png.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("browser SDK returned an invalid PNG")
            return Completed(
                {"tab": identity, "url": page.url, "bytes": len(png)},
                images=(Image("image/png", base64.b64encode(png).decode()),),
            )
        elif params.selector and params.nth is not None:
            # SDK nth supports only click/fill/check/hover/text and mutates DOM during
            # lookup. Preserve the existing indexed-selector contract through the
            # managed context; refs and role queries use the SDK's own identity map.
            return await super()._action(profile, action, params)
        elif action == "scroll":
            await client.call("scroll", x=params.x, y=params.y)
        elif action == "wait":
            if params.selector or params.role or params.ref:
                async with asyncio.timeout(params.timeout_ms / 1000):
                    while True:
                        try:
                            target = await self._target(client, params)
                            if (await client.call("isvisible", selector=target)).get("visible"):
                                break
                        except ValueError:
                            pass
                        await asyncio.sleep(0.02)
            else:
                await client.call("waitforloadstate", state="domcontentloaded")
        else:
            target = await self._target(client, params)
            if action == "click":
                await client.call("click", selector=target)
            elif action == "type":
                await client.call("fill", selector=target, value=params.value)
            elif action == "select":
                await client.call("select", selector=target, values=params.values)
            elif action == "press":
                await client.call("focus", selector=target)
                await client.call("press", key=params.key)
            else:
                return Refused(f"unknown browser action: {action}")
        if page.url != "about:blank" and not self.policy.allows(page.url):
            return Failed("navigation was blocked at an origin denied by the host")
        output: dict[str, JsonValue] = {"tab": identity, "url": page.url}
        if action in ("open", "new_tab", "back", "forward"):
            output["status"] = profile.statuses.get(identity)
        return Completed(output)
