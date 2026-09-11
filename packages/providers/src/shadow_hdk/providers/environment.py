"""The environment a provider is launched with, built from its record (D40, D41).

One function, and every provider-specific fact it uses is a **field** rather than a branch. The
reference implementation this is taken from writes the same logic as a chain of `if (agentId ===
'…')` cases, one per provider, and that is exactly the decay this avoids: the second provider must
cost a file.

Three moves, in this order, and the order is the contract:

1. **strip** what must not be inherited,
2. **set** what the record names,
3. **backfill** from the OS only what is still missing.

Stripping first means a record can strip a variable and then set its own value for it. Backfilling
last means it never overwrites a caller who was explicit.

**Nothing here may move a credential.** A provider file is data a team writes, and a `backfill_env`
naming an API key would quietly hand a caller's secret to a child that was never meant to have it.
This package holds no secrets (D41), so it refuses to carry one on a record's say-so.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from shadow_hdk.kernel import Provider

SECRET_LOOKING = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH")
"""Substrings that make a variable name look like a credential.

Deliberately broad and deliberately only applied to **backfill**: a host that means to pass a key to
a provider does so through the base environment it hands in, where it is the host's own decision and
plainly visible. What is refused is a *provider file* reaching into the ambient environment for one.
"""


def _looks_like_a_secret(name: str) -> bool:
    upper = name.upper()
    return any(part in upper for part in SECRET_LOOKING)


def spawn_path(base: str, search: Sequence[str]) -> str:
    """The child's `PATH`: the caller's entries first, then everything resolution searched.

    Symmetry with `resolution.search_dirs` is the point. A binary found in a toolchain directory can
    carry a shebang naming an interpreter in another one; a child whose `PATH` lacks it fails to
    execute a file that certainly exists, and the error names neither cause.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in [*base.split(os.pathsep), *search]:
        if not entry or entry in seen:
            continue
        seen.add(entry)
        ordered.append(entry)
    return os.pathsep.join(ordered)


def environment_for(
    provider: Provider,
    *,
    base: Mapping[str, str],
    search: Sequence[str],
    os_environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """What to launch this provider with."""
    ambient = os_environ if os_environ is not None else os.environ
    made = dict(base)

    # Case-insensitively, because one of the three platforms this runs on treats names that way and
    # a strip that missed `ClaudeCode` there is a bug the other two cannot reproduce.
    strip = {name.upper() for name in provider.strip_env}
    for name in [key for key in made if key.upper() in strip]:
        del made[name]

    for pair in provider.set_env:
        made[pair.name] = pair.value

    for name in provider.backfill_env:
        if name in made or _looks_like_a_secret(name):
            continue
        if (value := ambient.get(name)) is not None:
            made[name] = value

    # The provider's own override — `CLAUDE_BIN`, `CODEX_BIN` — is part of its environment whether
    # or not the record listed it: it is the documented way to name an install off the PATH, and a
    # probe built without it reported the provider absent with the binary right there.
    key = provider.bin_env_key
    if key and key not in made and (named := ambient.get(key)) is not None:
        made[key] = named

    if search:
        made["PATH"] = spawn_path(made.get("PATH", ""), search)
    return made


__all__ = ["environment_for", "spawn_path"]
