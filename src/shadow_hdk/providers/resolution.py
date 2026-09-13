"""Finding a provider's binary — every candidate, and further than `PATH`.

Three rules, each one a failure that is invisible on the machine you develop on.

**Return every candidate, in order.** A directory earlier on the path can hold a wrapper left by a
half-finished install: it exists, it is executable, and running it fails. Nothing here can tell it
from a working CLI — only spawning can — so the caller gets the list and walks it until one runs.
Returning "the winner" makes that impossible and reports a broken install as the provider.

**`PATH` is not the search path.** A process started by a launcher rather than a shell inherits a
minimal `PATH`, and the user's tools are in Homebrew, `~/.local/bin`, `~/.bun/bin`, a version
manager's directory. Searching only `PATH` reports a CLI absent on the machine it is installed on.

**What resolution searched, spawning must search too.** A binary can resolve here and still fail to
execute, because its shebang names an interpreter living in one of those extra directories and the
child's `PATH` did not carry it. `search_dirs` is therefore exported for the environment to reuse
rather than recomputed there — asymmetry between the two is a bug that only appears elsewhere.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from shadow_hdk.kernel import Provider

USER_TOOLCHAIN = (
    ".local/bin",
    ".bun/bin",
    ".cargo/bin",
    ".deno/bin",
    ".npm-global/bin",
    ".volta/bin",
    ".yarn/bin",
)
"""Where user-level installers put executables, relative to home."""

SYSTEM_TOOLCHAIN = ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin")
"""Package managers that a launcher's minimal `PATH` routinely omits."""


def search_dirs(path: Sequence[str] | None = None, home: Path | None = None) -> list[str]:
    """Every directory a provider's binary might be in, in the order to look.

    `PATH` comes first because what the user's shell would find is what this should find; the
    toolchain directories are the fallback for a process that did not inherit a shell's environment.
    """
    entries = list(path if path is not None else os.environ.get("PATH", "").split(os.pathsep))
    where = home if home is not None else Path.home()
    entries += [str(where / part) for part in USER_TOOLCHAIN]
    entries += list(SYSTEM_TOOLCHAIN)
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in entries:
        if not entry or entry in seen:
            continue
        seen.add(entry)
        ordered.append(entry)
    return ordered


def _runnable(where: Path) -> bool:
    return where.is_file() and os.access(where, os.X_OK)


def candidates(
    provider: Provider,
    *,
    path: Sequence[str] | None = None,
    extra_dirs: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> list[Path]:
    """Every executable that might be this provider, best first.

    `bin` outranks `fallback_bins` whatever the directory order says: a fork is a substitute for the
    real thing, never a preference over it.

    An override in the environment wins outright — and an override naming nothing **falls through**
    rather than failing, because a stale line in a shell profile must not make a working install
    unreachable.
    """
    environment = env if env is not None else os.environ
    if (
        provider.bin_env_key
        and (named := environment.get(provider.bin_env_key))
        and _runnable(Path(named))
    ):
        return [Path(named)]

    dirs = list(path if path is not None else os.environ.get("PATH", "").split(os.pathsep))
    dirs += list(extra_dirs) if extra_dirs is not None else search_dirs(path=[], home=home)
    ordered_dirs = list(dict.fromkeys(d for d in dirs if d))  # first occurrence wins, order kept

    found: list[Path] = []
    seen: set[Path] = set()
    for name in (provider.bin, *provider.fallback_bins):
        for directory in ordered_dirs:
            here = Path(directory) / name
            if here in seen or not _runnable(here):
                continue
            seen.add(here)
            found.append(here)
    return found


__all__ = ["candidates", "search_dirs"]
