"""Deterministic Playwright operations over isolated profiles and an owned origin gateway."""

from __future__ import annotations

import asyncio
import base64
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import JsonValue

from shadow_hdk.adapters.browser.arguments import Inputs, parse
from shadow_hdk.adapters.browser.gateway import Gateway, stop_process
from shadow_hdk.adapters.browser.policy import OriginPolicy
from shadow_hdk.kernel import Completed, Failed, Image, Observation, Refused
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.processes import start_held


@dataclass
class _Profile:
    directory: tempfile.TemporaryDirectory[str]
    agent: Any = None
    driver: Any = None
    gateway: Gateway | None = None
    browser: Any = None
    context: Any = None
    tabs: dict[str, Any] = field(default_factory=dict)
    active: str = ""
    next_tab: int = 0
    console: list[JsonValue] = field(default_factory=list)
    requests: list[JsonValue] = field(default_factory=list)

    def record(self, destination: list[JsonValue], item: JsonValue) -> None:
        destination.append(item)
        del destination[:-256]

    def add_page(self, page: Any) -> str:
        for identity, existing in self.tabs.items():
            if existing is page:
                return identity
        self.next_tab += 1
        identity = f"tab-{self.next_tab}"
        self.tabs[identity] = page
        self.active = identity
        page.on(
            "console",
            lambda message: self.record(
                self.console,
                {
                    "tab": identity,
                    "type": message.type,
                    "text": message.text[:8000],
                },
            ),
        )
        page.on(
            "pageerror",
            lambda error: self.record(
                self.console,
                {
                    "tab": identity,
                    "type": "pageerror",
                    "text": str(error)[:8000],
                },
            ),
        )
        page.on(
            "requestfailed",
            lambda request: self.record(
                self.requests,
                {
                    "tab": identity,
                    "url": request.url,
                    "method": request.method,
                    "failure": request.failure,
                },
            ),
        )
        page.on(
            "response",
            lambda response: (
                self.record(
                    self.requests,
                    {
                        "tab": identity,
                        "url": response.url,
                        "status": response.status,
                    },
                )
                if response.status >= 400
                else None
            ),
        )
        return identity

    async def close(self) -> None:
        failures: list[str] = []
        try:
            for resource, method in (
                (self.agent, "close"),
                (self.context, "close"),
                (self.browser, "close"),
                (self.driver, "stop"),
                (self.gateway, "close"),
            ):
                if resource is not None:
                    try:
                        await getattr(resource, method)()
                    except (Exception, asyncio.CancelledError) as error:
                        failures.append(f"{type(error).__name__}: {error}")
        finally:
            self.directory.cleanup()
        if failures:
            raise RuntimeError("; ".join(failures))


class PlaywrightEngine:
    licence = "Apache-2.0 (Playwright); MIT (mitmproxy); MIT/Apache-2.0 (uv)"

    def __init__(
        self,
        *,
        policy: OriginPolicy | None = None,
        headless: bool = True,
        install_browser: bool = True,
        gateway_python: str | None = None,
        upstream_ca: Path | None = None,
    ) -> None:
        self._policy = policy or OriginPolicy()
        self._headless, self._install_browser = headless, install_browser
        self._gateway_python, self._upstream_ca = gateway_python, upstream_ca
        self._profiles: dict[str, _Profile] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._closed: set[str] = set()
        self._installing = asyncio.Lock()

    @property
    def policy(self) -> OriginPolicy:
        return self._policy

    async def _install(self) -> None:
        context = current_run()
        if context is not None:
            await context.activity(
                "install", "Installing Chromium for the optional browser component."
            )
        process = await start_held(
            sys.executable,
            "-I",
            "-m",
            "playwright",
            "install",
            "chromium",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), 300)
            if process.returncode:
                raise RuntimeError("Chromium installation failed: " + output.decode()[-8000:])
        finally:
            await stop_process(process)

    async def _create(self) -> _Profile:
        from playwright.async_api import async_playwright

        profile = _Profile(tempfile.TemporaryDirectory(prefix="shadow-hdk-browser-"))
        try:
            profile.driver = await async_playwright().start()
            binary = Path(profile.driver.chromium.executable_path)
            if not binary.exists():
                if not self._install_browser:
                    raise RuntimeError(
                        "Chromium is missing; run python -m playwright install chromium."
                    )
                async with self._installing:
                    if not binary.exists():
                        await self._install()
            profile.gateway = await Gateway.start(
                Path(profile.directory.name),
                self.policy,
                sdk_python=self._gateway_python,
                upstream_ca=self._upstream_ca,
            )
            profile.browser = await profile.driver.chromium.launch(
                headless=self._headless,
                proxy={"server": f"http://127.0.0.1:{profile.gateway.port}"},
                args=[
                    "--proxy-bypass-list=<-loopback>",
                    f"--ignore-certificate-errors-spki-list={profile.gateway.spki}",
                    "--disable-quic",
                    "--dns-prefetch-disable",
                    "--disable-background-networking",
                    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                ],
            )
            profile.context = await profile.browser.new_context(
                service_workers="block",
                accept_downloads=False,
                viewport={"width": 1280, "height": 720},
            )
            profile.context.on("page", profile.add_page)
            return profile
        except BaseException:
            await profile.close()
            raise

    async def execute(self, action: str, inputs: JsonValue, resource_scope: str) -> Observation:
        try:
            params = parse(action, inputs)
        except ValueError as error:
            return Refused(f"invalid browser inputs: {error}")
        async with self._locks.setdefault(resource_scope, asyncio.Lock()):
            if resource_scope in self._closed:
                return Refused("this browser resource scope is closed")
            if action in ("open", "new_tab") and (
                params.url is None or not self.policy.allows(params.url)
            ):
                return Refused("browser origin denied by the host")
            try:
                profile = self._profiles.get(resource_scope)
                if profile is None:
                    if action not in ("open", "new_tab"):
                        return Refused("no browser is open in this scope")
                    profile = await self._create()
                    self._profiles[resource_scope] = profile
                return await self._action(profile, action, params)
            except ImportError:
                return Failed("Install shadow-hdk[browser] to use the optional browser component.")
            except Exception as error:
                return Failed(f"browser {action} failed: {error}"[-8000:])

    async def _locator(self, page: Any, params: Inputs, *, many: bool = False) -> Any:
        if bool(params.selector) == bool(params.role):
            raise ValueError("supply either selector or role")
        locator = (
            page.locator(params.selector)
            if params.selector
            else page.get_by_role(
                params.role,
                **({"name": params.name, "exact": True} if params.name is not None else {}),
            )
        )
        if many:
            return locator
        if params.nth is not None:
            return locator.nth(params.nth)
        count = await locator.count()
        if count > 1:
            raise ValueError(f"selector matched {count} elements; choose an explicit nth index")
        return locator

    async def _action(self, profile: _Profile, action: str, params: Inputs) -> Observation:
        if action == "tabs":
            tabs: list[JsonValue] = [
                {"id": identity, "url": page.url, "title": await page.title()}
                for identity, page in list(profile.tabs.items())
                if not page.is_closed()
            ]
            return Completed({"tabs": tabs, "active": profile.active})
        if action in ("console", "requests"):
            if params.tab is not None and params.tab not in profile.tabs:
                return Refused("unknown browser tab")
            entries = [
                entry
                for entry in getattr(profile, action)
                if params.tab is None
                or (isinstance(entry, dict) and entry.get("tab") == params.tab)
            ]
            return Completed({"entries": entries})
        identity = params.tab or profile.active
        page = profile.tabs.get(identity)
        if action == "new_tab" or (action == "open" and page is None and params.tab is None):
            page = await profile.context.new_page()
            identity = profile.add_page(page)
        if page is None or page.is_closed():
            return Refused("unknown or closed browser tab")
        page.set_default_timeout(params.timeout_ms)
        page.set_default_navigation_timeout(params.timeout_ms)
        response = None
        if action in ("open", "new_tab"):
            response = await page.goto(params.url, wait_until="domcontentloaded")
        elif action in ("back", "forward"):
            response = await getattr(page, f"go_{action}")(wait_until="domcontentloaded")
        elif action == "close_tab":
            await page.close()
            del profile.tabs[identity]
            profile.active = next(iter(profile.tabs), "")
            return Completed({"closed": identity})
        elif action == "snapshot":
            text = await page.locator("body").aria_snapshot()
            return Completed(
                {
                    "tab": identity,
                    "url": page.url,
                    "snapshot": text[:200000],
                    "truncated": len(text) > 200000,
                }
            )
        elif action == "find":
            locator = await self._locator(page, params, many=True)
            count = await locator.count()
            matches: list[JsonValue] = [
                {"nth": index, "snapshot": (await locator.nth(index).aria_snapshot())[:10000]}
                for index in range(min(count, 20))
            ]
            return Completed(
                {"tab": identity, "count": count, "matches": matches, "truncated": count > 20}
            )
        elif action == "screenshot":
            if params.full_page:
                size = await page.evaluate(
                    "({width:document.documentElement.scrollWidth,"
                    "height:document.documentElement.scrollHeight})"
                )
                if size["width"] * size["height"] > 20_000_000:
                    return Refused("full-page image is too large; take a viewport screenshot")
            png = await page.screenshot(type="png", full_page=params.full_page)
            if len(png) > 10_000_000:
                return Refused("image is too large for a model observation")
            return Completed(
                {"tab": identity, "url": page.url, "bytes": len(png)},
                images=(Image("image/png", base64.b64encode(png).decode()),),
            )
        elif action == "scroll":
            await page.mouse.wheel(params.x, params.y)
        elif action == "wait":
            if params.selector or params.role:
                await (await self._locator(page, params)).wait_for(state="visible")
            else:
                await page.wait_for_load_state("domcontentloaded")
        elif action in ("click", "type", "select", "press"):
            locator = await self._locator(page, params)
            if action == "click":
                await locator.click()
            elif action == "type":
                if params.value is None:
                    return Refused("type requires value")
                await locator.fill(params.value)
            elif action == "select":
                if params.values is None:
                    return Refused("select requires values")
                await locator.select_option(params.values)
            else:
                if params.key is None:
                    return Refused("press requires key")
                await locator.press(params.key)
        else:
            return Refused(f"unknown browser action: {action}")
        if page.url != "about:blank" and not self.policy.allows(page.url):
            return Failed("navigation was blocked at an origin denied by the host")
        profile.active = identity
        output: dict[str, JsonValue] = {"tab": identity, "url": page.url}
        if action in ("open", "new_tab", "back", "forward"):
            output["status"] = response.status if response is not None else None
        return Completed(output)

    async def release_run(self, resource_scope: str) -> None:
        self._closed.add(resource_scope)
        async with self._locks.setdefault(resource_scope, asyncio.Lock()):
            profile = self._profiles.pop(resource_scope, None)
            if profile is not None:
                await profile.close()
