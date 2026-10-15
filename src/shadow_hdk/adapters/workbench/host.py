"""The person's command/file door is direct host access, with no model or agent authority."""

import re
from collections.abc import Sequence
from ipaddress import ip_address
from typing import Any

from pydantic import JsonValue

from shadow_hdk.adapters.workbench.listeners import ProcessListeners
from shadow_hdk.adapters.workbench.reports import junit_results
from shadow_hdk.kernel import Completed, Observation
from shadow_hdk.runtime.environment import Environment


def browsable(addresses: Sequence[Any]) -> str | None:
    """The url of a job's own server, where there is one a browser could open (ENH-053).

    **Verified only, and loopback only.** A url scraped from a process's output is a guess at where
    it listens; a listener was looked up, and the pane must not open a page nobody confirmed is
    there. And the seam must not widen the origin boundary: a job bound to a routable interface is
    somebody else's reach into this run, so it is not offered at all rather than offered and
    refused. Loopback needs no origin naming by hand, because the policy already allows it — which
    is what makes this a join of two halves rather than a new permission.
    """
    for address in addresses:
        if not isinstance(address, dict) or not address.get("verified"):
            continue
        if address.get("protocol") != "tcp":
            continue
        host, port = address.get("host"), address.get("port")
        if not isinstance(port, int) or not isinstance(host, str):
            continue
        try:
            if not ip_address(host).is_loopback:
                continue
        except ValueError:
            if host != "localhost":
                continue
        return f"http://{host}:{port}"
    return None


class HostDoor:
    """The host supplies its own environment and authentication; this does not grant rights.

    Use the same working-copy roots as the agent, with the person's own enforced environment
    policy. Closing this door does not close a shared environment; its owner closes it.
    """

    def __init__(
        self, environment: Environment, *, listeners: ProcessListeners | None = None
    ) -> None:
        self.environment, self._listeners = environment, listeners

    async def read(self, path: str) -> Observation:
        return await self.environment.invoke("read_file", {"path": path})

    async def run(self, command: str) -> Observation:
        return await self.environment.invoke("run_shell", {"command": command})

    async def background(self, command: str) -> Observation:
        return await self.environment.invoke("run_background", {"command": command})

    async def stop(self, job: str) -> Observation:
        return await self.environment.invoke("kill_job", {"job": job})

    async def output(self, job: str, *, cursor: int = 0, limit: int = 64000) -> Observation:
        return self.environment.observe_process(job, cursor=cursor, limit=limit)

    async def jobs(self) -> Observation:
        jobs: list[JsonValue] = []
        for info in self.environment.observe_processes():
            addresses: list[JsonValue] = []
            output = self.environment.observe_process(str(info["job"]))
            if isinstance(output, Completed) and isinstance(output.output, dict):
                text = str(output.output["output"])
                addresses.extend(
                    {"url": url, "source": "output", "verified": False}
                    for url in sorted(set(re.findall(r"https?://[^\s<>\"']+", text)))
                )
            inspection: str | None = None
            if self._listeners is not None and info["running"] and isinstance(info["pid"], int):
                try:
                    addresses.extend(await self._listeners.inspect(info["pid"]))
                except Exception as error:
                    inspection = f"listener inspection unavailable: {type(error).__name__}: {error}"
            jobs.append({**info, "addresses": addresses, "inspection_error": inspection})
        return Completed({"jobs": jobs})

    async def results(self, path: str) -> Observation:
        report = await self.read(path)
        if not isinstance(report, Completed):
            return report
        return junit_results(report.output)
