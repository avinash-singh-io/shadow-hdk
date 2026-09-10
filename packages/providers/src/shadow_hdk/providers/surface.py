"""What this machine can reach, and how to open it without importing an adapter.

**Detection reports; it never installs (D41).** An absent provider comes back absent with the
command a person would run. Running it is somebody else's decision on somebody else's machine.

**A transport is discovered, not imported.** This module hands back a `ModelPort` from one adapter
or an `AgentPort` from another, and a module that imported both would fail rule 4 of the
stands-alone invariant — an AST walk over every import node, which a deferred import does not evade
and should not. So an adapter *declares* itself in its own distribution metadata:

    [project.entry-points."shadow_hdk.transports"]
    acp = "shadow_hdk.adapters.acp:open_agent"

and this looks the declaration up. No adapter's name appears in this file, the arrow points from
detail to abstraction, and a third party can ship a transport nobody here has heard of. That is the
dependency inversion, and it is enforced rather than promised: rule 5 of the same invariant fails
the build if this package ever imports an adapter.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from shadow_hdk.kernel import Provider, ProviderStatus
from shadow_hdk.providers.probes import ask_auth, ask_version
from shadow_hdk.providers.resolution import candidates

TRANSPORT_GROUP = "shadow_hdk.transports"
"""The entry-point group an adapter declares itself in."""

_REGISTERED: dict[str, Callable[..., Any]] = {}


class NoSuchTransport(LookupError):
    """A provider names a transport nothing installed here serves."""


@dataclass(frozen=True)
class Available:
    """One provider, as this machine actually found it. Every field is measured or `None`."""

    provider: Provider
    status: ProviderStatus
    binary: Path | None = None
    version: str | None = None
    message: str | None = None

    @property
    def install_hint(self) -> str:
        return self.provider.install_hint

    @property
    def usable(self) -> bool:
        """Worth trying — which includes `unknown`.

        `unknown` means nobody could ask, not that the answer was no (D41). Treating it as
        unusable would make every provider without a status command permanently unavailable, which
        is the two-state mistake the fifth answer exists to avoid.
        """
        return self.status in ("ready", "unknown")


def register_transport(name: str, opener: Callable[..., Any]) -> None:
    """Wire a transport by hand — the same mechanism with the discovery step skipped."""
    _REGISTERED[name] = opener


def transports() -> dict[str, Callable[..., Any]]:
    """Every transport this machine can serve: declared by installed distributions, plus any
    registered by hand. Nothing is imported to find them — only to *use* one."""
    found: dict[str, Callable[..., Any]] = {}
    for entry in entry_points(group=TRANSPORT_GROUP):
        found[entry.name] = entry.load
    found.update(_REGISTERED)
    return found


async def detect(
    providers: Sequence[Provider],
    *,
    path: Sequence[str] | None = None,
    extra_dirs: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> list[Available]:
    """Ask each provider whether it is here, current, and signed in.

    A candidate that turns out to be a wrapper whose target is gone is **abandoned for the next
    one** rather than reported as the provider — which is the whole reason resolution hands over a
    list instead of a winner.
    """
    environment = dict(env or {})
    found: list[Available] = []
    for provider in providers:
        found.append(await _detect_one(provider, path, extra_dirs, environment))
    return found


async def _detect_one(
    provider: Provider,
    path: Sequence[str] | None,
    extra_dirs: Sequence[str] | None,
    env: Mapping[str, str],
) -> Available:
    last: str | None = None
    for binary in candidates(provider, path=path, extra_dirs=extra_dirs, env=env):
        version = await ask_version(provider, binary, env=env)
        if version.unusable:
            last = version.message
            continue
        if version.status == "too-old":
            return Available(provider, "too-old", binary, version.version, version.message)
        auth = await ask_auth(provider, binary, env=env)
        return Available(provider, auth.status, binary, version.version, auth.message)
    return Available(provider, "absent", None, None, last)


async def open_with(
    provider: Provider, *, binary: Path, env: Mapping[str, str], **extra: Any
) -> Any:
    """Open this provider over the transport its record names.

    The opener is loaded by name at call time. A provider naming a transport nothing serves is a
    typo or a missing package, and the error says which string could not be honoured — never a
    silent fallback to some other transport, which would drive the wrong CLI the wrong way.
    """
    if not provider.transport:
        raise NoSuchTransport(
            f"{provider.called} names no transport, so there is no way to talk to it"
        )
    serving = transports()
    if provider.transport not in serving:
        raise NoSuchTransport(
            f"{provider.called} speaks {provider.transport!r} and nothing installed here serves it"
            + (f" — {provider.install_hint}" if provider.install_hint else "")
        )
    opener = serving[provider.transport]()
    return await opener(provider, binary=binary, env=env, **extra)


__all__ = [
    "TRANSPORT_GROUP",
    "Available",
    "NoSuchTransport",
    "detect",
    "open_with",
    "register_transport",
    "transports",
]
